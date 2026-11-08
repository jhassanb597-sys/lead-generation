import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from io import BytesIO
import re, urllib.parse, json, uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import List

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from sectors import SECTORS, choose_sources, list_sectors, get_sector_examples
from schema import Lead
from scoring import score_lead, HIGH_TICKET_SECTORS
from utils import safe_request, redact_url, dedupe_against_history, mark_as_seen
from enrich import fetch_signals_cached, research_summary
from outreach import render_pitch

# ---- Country / City data ----
COUNTRIES_AND_CITIES = {
    "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "San Francisco"],
    "United Kingdom": ["London", "Manchester", "Birmingham", "Glasgow"],
    "Pakistan": ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad"],
    "India": ["Mumbai", "Delhi", "Bangalore", "Hyderabad"],
    "UAE": ["Dubai", "Abu Dhabi", "Sharjah"],
    "Saudi Arabia": ["Riyadh", "Jeddah", "Dammam"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
    "France": ["Paris", "Lyon", "Marseille", "Toulouse"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth"],
}

CITY_COORDS = {
    "New York": (40.71, -74.01), "Los Angeles": (34.05, -118.24),
    "Chicago": (41.88, -87.63), "Houston": (29.76, -95.38),
    "Miami": (25.76, -80.19), "San Francisco": (37.77, -122.41),
    "London": (51.51, -0.13), "Manchester": (53.48, -2.24),
    "Karachi": (24.86, 67.01), "Lahore": (31.55, 74.34),
    "Islamabad": (33.68, 73.04), "Rawalpindi": (33.59, 73.05), "Faisalabad": (31.41, 73.07),
    "Mumbai": (19.08, 72.88), "Delhi": (28.61, 77.21), "Bangalore": (12.97, 77.59),
    "Dubai": (25.20, 55.27), "Abu Dhabi": (24.47, 54.37), "Sharjah": (25.35, 55.39),
    "Toronto": (43.65, -79.38), "Vancouver": (49.28, -123.12),
    "Sydney": (-33.87, 151.21), "Melbourne": (-37.81, 144.96),
    "Berlin": (52.52, 13.40), "Munich": (48.14, 11.58),
    "Paris": (48.86, 2.35), "Riyadh": (24.71, 46.67), "Jeddah": (21.54, 39.17)
}

def _get_city_coords(city: str):
    return CITY_COORDS.get(city, (40.71, -74.01))

# ---- Config & Persistence ----
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
LEADS_FILE = os.path.join(DATA_DIR, "leads.json")
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")

st.set_page_config(page_title="Lead Empire", layout="wide")

# ---- Branding CSS ----
st.markdown("""
<style>
:root { --primary: #FF4B4B; --bg: #0E1117; --card-bg: #262730; --text: #FAFAFA; --muted: #888; }
.block-container { padding-top: 1.5rem; }
h1, h2, h3, .stMarkdown { color: var(--text) !important; }
.stApp { background-color: var(--bg); }
header[data-testid="stHeader"] { background-color: var(--bg); }
.sidebar .sidebar-content { background-color: var(--card-bg); }

.empire-header { background: linear-gradient(90deg, var(--primary) 0%, #ff1a1a 100%); padding: 0.75rem 1.5rem; margin: -1rem -1rem 1.5rem -1rem; display: flex; align-items: center; gap: 1rem; border-bottom: 2px solid #ff6666; }
.empire-header h1 { margin: 0; font-size: 1.4rem; color: white !important; font-weight: 700; }
.empire-badge { background: rgba(255,255,255,0.15); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }

.chip { display: inline-flex; align-items: center; gap: 0.35rem; background: var(--card-bg); border: 1px solid #333; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.8rem; margin: 0.2rem 0.2rem 0.2rem 0; }
.chip-wa { color: #25D366; } .chip-ig { color: #E1306C; } .chip-fb { color: #1877F2; } .chip-em { color: #D44638; } .chip-web { color: #4285F4; }

.streamlit-expanderHeader { background: var(--card-bg) !important; border-radius: 8px !important; }
</style>
<div class="empire-header"><h1>🔥 Lead Empire</h1><span class="empire-badge">One-Click Lead Engine</span></div>
""", unsafe_allow_html=True)

# ---- Session State ----
if "leads" not in st.session_state:
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, "r", encoding="utf-8") as f: st.session_state.leads = [Lead(**d) for d in json.load(f)]
        except: st.session_state.leads = []
    else: st.session_state.leads = []

if "audits" not in st.session_state: st.session_state.audits = []
if "contacted" not in st.session_state: st.session_state.contacted = set()
if "selected_lead_ids" not in st.session_state: st.session_state.selected_lead_ids = set()

def persist_leads():
    with open(LEADS_FILE, "w", encoding="utf-8") as f: json.dump([asdict(l) for l in st.session_state.leads], f, indent=2)

def clean_url(dirty: str) -> str:
    if not dirty or dirty == "N/A": return "N/A"
    if "/url?q=" in dirty:
        try:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(dirty).query).get('q')
            if q: dirty = urllib.parse.unquote(q[0])
        except: pass
    parts = [urllib.parse.unquote(dirty)]
    for delim in ["&sa=U", "&ved=", "&usg=", "?utm_", "&opi"]:
        if not parts[-1]: break
        parts.append(parts[-1].split(delim)[0])
    return parts[-1] if parts else dirty

def enrich_contacts(website: str) -> dict:
    empty = {"website": website if website != "N/A" else "N/A", "whatsapp": "N/A", "fb": "N/A", "insta": "N/A", "linkedin": "N/A", "email": "N/A"}
    if website == "N/A" or not website: return empty
    clean = clean_url(website)
    if not clean.startswith("http"): clean = "https://" + clean
    try:
        r = safe_request(clean, timeout=8)
        if r.status_code != 200: return empty
        soup = BeautifulSoup(r.text, 'html.parser')
        html = r.text
        wa = "N/A"
        for a in soup.find_all('a', href=True):
            h = a['href']
            if 'wa.me' in h or 'api.whatsapp' in h or 'whatsapp.com' in h:
                wa = clean_url(h); break
        fb = next((clean_url(a['href']) for a in soup.find_all('a', href=True) if 'facebook.com' in a['href'] and 'sharer' not in a['href']), "N/A")
        insta = next((clean_url(a['href']) for a in soup.find_all('a', href=True) if 'instagram.com' in a['href']), "N/A")
        linkedin = next((clean_url(a['href']) for a in soup.find_all('a', href=True) if 'linkedin.com' in a['href']), "N/A")
        email_m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}', html)
        email = email_m.group(0) if email_m and 'example' not in email_m.group(0) else "N/A"
        return {"website": clean, "whatsapp": wa, "fb": fb, "insta": insta, "linkedin": linkedin, "email": email}
    except: return empty

def check_rebuild_needed(website: str):
    if website == "N/A": return "🔥 NO WEBSITE - Build New $500", 10
    try:
        r = safe_request(website, timeout=6)
        if r.status_code != 200: return "⚠️ Site Error - Rebuild Opportunity", 7
        text = r.text.lower()
        issues = []
        m = re.search(r"(©|copyright)\s*(20\d{2})", text, re.I)
        if m and int(m.group(2)) < 2024: issues.append("Outdated Copyright")
        m = re.search(r"wordpress[\\/s]*([3-5])\.", text, re.I)
        if m and int(m.group(1)) < 6: issues.append("Legacy WordPress")
        if "not mobile friendly" in text or not re.search(r'<meta[^>]+name=["\']viewport["\']', text, re.I): issues.append("Not Mobile Friendly")
        if issues: return f"⚠️ Rebuild Needed: {', '.join(issues)}", 8
        return "OK Site - Try Upsell", 4
    except: return "⚠️ Site Error - Rebuild Opportunity", 7

# ---- Source Adapters ----
def scrape_google_maps(sector, sub_sector, city, country, limit) -> List[Lead]:
    leads = []
    if DEMO_MODE: return []
    query = urllib.parse.quote_plus(f"{sub_sector} in {city}, {country}")
    lat, lng = _get_city_coords(city)
    url = f"https://www.google.com/maps/search/{query}/@{lat},{lng},12z"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=60000)
            try: page.locator('button:has-text("Accept all")').first.click(timeout=3000)
            except: pass
            page.wait_for_timeout(3000)
            for _ in range(4):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(1000)
            cards = page.locator('div[role="article"]').all()
            if not cards: cards = page.locator('a[href*="/maps/place/"]').all()
            for i in range(min(limit, len(cards))):
                try:
                    cards[i].click()
                    page.wait_for_timeout(2000)
                    name_loc = page.locator('h1.DUwDvf')
                    if name_loc.count() == 0: continue
                    name = name_loc.first.inner_text()
                    phone = page.locator('button[data-item-id*="phone"]').first.inner_text() if page.locator('button[data-item-id*="phone"]').count() > 0 else "N/A"
                    web = clean_url(page.locator('a[data-item-id="authority"]').first.get_attribute("href")) if page.locator('a[data-item-id="authority"]').count() > 0 else "N/A"
                    enriched = enrich_contacts(web)
                    final_wa = enriched['whatsapp'] if enriched['whatsapp'] != "N/A" else (f"{phone} (WA Check)" if phone != "N/A" else "N/A")
                    leads.append(Lead(lead_id=str(uuid.uuid4())[:8], name=name, sector=sector, sub_sector=sub_sector, city=city, country=country, phone=phone, whatsapp=final_wa, email=enriched['email'], website=enriched['website'], instagram=enriched['insta'], facebook=enriched['fb'], linkedin=enriched['linkedin'], source="google_maps", source_url=url, scraped_at=datetime.now(timezone.utc).isoformat()))
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                except: continue
            browser.close()
    except Exception as e: print(f"Maps error: {e}")
    return leads

def scrape_google_search_dorking(sector, sub_sector, city, country, limit) -> List[Lead]:
    leads = []
    if DEMO_MODE: return []
    if sector == "INFLUENCERS": query = f'site:instagram.com "{city}" "{sub_sector}"'
    elif sector == "TECH_COMPANIES": query = f'site:linkedin.com/in/ "{city}" "{sub_sector}"'
    else: query = f'site:linkedin.com/company/ "{city}" "{sub_sector}"'
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num={limit}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(2000)
            results = page.locator('div.g').all()
            for res in results[:limit]:
                try:
                    title_el = res.locator('h3')
                    link_el = res.locator('a')
                    if title_el.count() > 0 and link_el.count() > 0:
                        name, link = title_el.first.inner_text(), link_el.first.get_attribute("href")
                        if "instagram.com" in link: leads.append(Lead(lead_id=str(uuid.uuid4())[:8], name=name, sector=sector, sub_sector=sub_sector, city=city, country=country, instagram=link, source="Google (IG)", source_url=link))
                        elif "linkedin.com" in link: leads.append(Lead(lead_id=str(uuid.uuid4())[:8], name=name, sector=sector, sub_sector=sub_sector, city=city, country=country, linkedin=link, source="Google (LI)", source_url=link))
                except: continue
            browser.close()
    except Exception as e: print(f"Dorking error: {e}")
    return leads

ADAPTER_MAP = {"google_maps": scrape_google_maps, "google_search_dorking": scrape_google_search_dorking}

# ---- TABS ----
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Lead Finder", "🔍 Bulk Audit", "📊 Triage & Pitch", "🏢 Single Audit", "📤 Export"])

with tab1:
    st.subheader("Lead Finder")
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1])
    sectors = list_sectors()
    sector = col1.selectbox("Sector", sectors, key="t1_sector")
    sub_sector = col2.selectbox("Sub-Sector", get_sector_examples(sector), key="t1_sub")
    selected_country = col3.selectbox("Country", list(COUNTRIES_AND_CITIES.keys()), key="t1_country")
    city = col4.selectbox("City", COUNTRIES_AND_CITIES.get(selected_country, []), key="t1_city")
    limit = col5.slider("Limit", 5, 50, 10, key="t1_limit")
    
    if st.button("🚀 Find Leads", type="primary", use_container_width=True):
        sources = choose_sources(sector)
        all_leads = []
        with st.spinner("Scraping the web for your target clients..."):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {executor.submit(ADAPTER_MAP[s], sector, sub_sector, city, selected_country, limit): s for s in sources if s in ADAPTER_MAP}
                for f in as_completed(futures):
                    try: all_leads.extend(f.result())
                    except Exception as e: st.warning(f"Source failed: {e}")
            
            seen, deduped = set(), []
            for l in all_leads:
                k = (l.name.lower(), l.phone)
                if k not in seen: seen.add(k); deduped.append(l)
            
            if deduped:
                websites = [l.website for l in deduped if l.website != "N/A"]
                signals_map = {}
                if websites:
                    with ThreadPoolExecutor(max_workers=6) as ex:
                        futures = {ex.submit(fetch_signals_cached, url): url for url in websites}
                        for f in as_completed(futures): signals_map[futures[f]] = f.result()
                
                scored = [score_lead(l, signals_map.get(l.website)) for l in deduped]
                scored.sort(key=lambda x: x.opportunity_score, reverse=True)
                st.session_state.leads = scored
                persist_leads()
                st.success(f"Successfully found {len(scored)} leads!")
            else: st.error("No leads found. Google may have blocked the scraper.")

    if st.session_state.leads:
        df = pd.DataFrame([{"Select": l.lead_id in st.session_state.selected_lead_ids, "Business": l.name, "Phone": l.phone, "WhatsApp": l.whatsapp, "Email": l.email, "Website": l.website, "Instagram": l.instagram, "Score": l.opportunity_score, "Source": l.source, "lead_id": l.lead_id} for l in st.session_state.leads])
        edited = st.data_editor(df, use_container_width=True, hide_index=True, column_config={"Select": st.column_config.CheckboxColumn("☑️"), "lead_id": None}, key="t1_editor")
        st.session_state.selected_lead_ids = set(edited.loc[edited["Select"] == True, "lead_id"].tolist())
        
        c1, c2 = st.columns(2)
        if c1.button("Select All"):
            st.session_state.selected_lead_ids = set(l.lead_id for l in st.session_state.leads)
            st.rerun()
        if c2.button("Clear Selection"):
            st.session_state.selected_lead_ids = set()
            st.rerun()
            
        selected = df[df["lead_id"].isin(st.session_state.selected_lead_ids)].drop(columns=["lead_id", "Select"])
        if not selected.empty:
            st.download_button("📥 Download Selected CSV", selected.to_csv(index=False).encode('utf-8'), "leads.csv")

with tab2:
    st.subheader("Bulk Website Auditor")
    urls_text = st.text_area("URLs (one per line)", height=150)
    if st.button("🔍 Audit All Websites", type="primary"):
        urls = [u.strip() for u in urls_text.split("\n") if u.strip()][:100]
        if urls:
            results = []
            with st.spinner("Auditing..."):
                for url in urls:
                    msg, score = check_rebuild_needed(url)
                    enriched = enrich_contacts(url)
                    l = score_lead(Lead(lead_id=str(uuid.uuid4())[:8], website=url, email=enriched['email'], whatsapp=enriched['whatsapp'], source="bulk_audit"))
                    l.rebuild_msg = msg
                    results.append(l)
                st.session_state.audits = results
            st.dataframe(pd.DataFrame([{"Website": r.website, "Score": r.opportunity_score, "Issues": r.rebuild_msg} for r in results]), use_container_width=True)

with tab3:
    st.subheader("Lead Triage & Pitch")
    if not st.session_state.leads: st.info("No leads found yet.")
    else:
        for l in sorted(st.session_state.leads, key=lambda x: x.opportunity_score, reverse=True):
            with st.expander(f"{l.name} • Score: {l.opportunity_score}"):
                st.write(f"**Phone:** {l.phone} | **WA:** {l.whatsapp} | **Email:** {l.email} | **IG:** {l.instagram}")
                st.code(render_pitch(l, {}, "default"), language="text")
                if st.button("Mark Contacted", key=f"c_{l.lead_id}"): st.session_state.contacted.add(l.lead_id); st.success("Marked!")

with tab4:
    st.subheader("Single Business Audit")
    url_input = st.text_input("Paste Business Website URL")
    if st.button("Audit Website"):
        if "google.com/maps" in url_input: st.warning("Paste the business website, not Maps.")
        else:
            msg, score = check_rebuild_needed(url_input)
            enriched = enrich_contacts(url_input)
            l = score_lead(Lead(website=url_input, email=enriched['email'], whatsapp=enriched['whatsapp']))
            st.metric("Opportunity Score", l.opportunity_score)
            st.write("**Issues:**", msg)
            st.json(enriched)

with tab5:
    st.subheader("Export & Strategy")
    if st.session_state.leads:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df = pd.DataFrame([{"Business": l.name, "Phone": l.phone, "WhatsApp": l.whatsapp, "Email": l.email, "Website": l.website, "Instagram": l.instagram, "Score": l.opportunity_score, "Source": l.source} for l in st.session_state.leads])
            df.to_excel(writer, sheet_name="Leads", index=False)
        st.download_button("📊 Download Multi-Sheet Excel", buf.getvalue(), "lead_empire.xlsx")

# Sidebar
st.sidebar.header("⚙️ Settings")
if st.sidebar.button("🗑️ Clear All Data"):
    st.session_state.leads = []
    persist_leads()
    st.rerun()