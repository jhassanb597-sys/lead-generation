<p align="center">
  <img src="https://img.shields.io/badge/Lead%20Empire-Multi--Source%20Lead%20Engine-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Lead Empire" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
</p>

<h1 align="center">🔥 Lead Empire — One-Click Lead Generation for Local & B2B Businesses</h1>

<p align="center">
  <strong>Find verified leads across 11+ sectors in seconds.</strong> Google Maps scraping + Google Search dorking for Instagram & LinkedIn. Built with Streamlit + Playwright.
</p>

---

## 🎯 Why Lead Empire?

| Problem | Solution |
|---------|----------|
| ❌ Buying stale lead lists | ✅ **Real-time** Google Maps data — fresh every run |
| ❌ No contact info on listings | ✅ **Auto-enrichment** — Website → WhatsApp, Email, IG, LinkedIn, FB |
| ❌ Wasting time on bad fits | ✅ **Smart scoring** — Opportunity Score (0-100) ranks by rebuild potential, contact completeness & reviews |
| ❌ Manual copy-paste | ✅ **One click** → CSV/Excel export → ready for outreach |
| ❌ Getting blocked by Google | ✅ **Coordinate forcing** — Search *exactly* your target city, not your IP location |

---

## 🚀 Quick Start

```bash
# 1. Clone & install
git clone https://github.com/jhassanb597-sys/lead-generation.git
cd lead-generation
pip install -r requirements.txt
playwright install chromium

# 2. Run
streamlit run app.py
# Opens at http://localhost:8501
```

### 🎭 DEMO MODE (no browser, no network)
Perfect for presentations, CI, or offline testing:
```bash
# PowerShell
$env:DEMO_MODE="true"
streamlit run app.py

# CMD
set DEMO_MODE=true
streamlit run app.py
```

---

## 📋 Features at a Glance

### 📍 Tab 1 — Lead Finder
- **11 sectors**: Health, Beauty, Fitness, Food, Trades, Professional, Real Estate, Healthcare, Shops, Tech Companies, Influencers
- **Cascading Country → City dropdowns** (built-in, no external API)
- **Coordinate forcing** — forces Google Maps to your selected city (bypasses IP-based local results)
- **Two engines**:
  - `google_maps` — Maps listings (name, phone, website, address, rating, reviews)
  - `google_search_dorking` — Instagram & LinkedIn profiles via Google dorks
- **Smart dedupe** — by (name + phone), cross-session history
- **Opportunity scoring** — rebuild potential, contact completeness, WhatsApp bonus, high-ticket sector bonus
- **Export** → CSV / Excel

### 🔍 Tab 2 — Bulk Website Auditor
- Paste up to 100 URLs or upload CSV
- **Rebuild scoring**: outdated copyright, legacy WP/jQuery, missing viewport, mobile-friendly
- **Contact enrichment** from each website
- Export scored results to Excel

### 📊 Tab 3 — Triage & Pitch
- Leads ranked by Opportunity Score
- **Per-sector pitch scripts** (copy-to-clipboard)
- Mark contacted / track outreach

### 🏢 Tab 4 — Single Business Audit
- Deep-dive one website: rebuild score + issues + enriched contacts + proposal text

### 📤 Tab 5 — Export & Strategy
- Multi-sheet Excel: Leads | Audits | Scoring Breakdown
- Universal scaling process + ethical scraping notice

---

## 🏗️ Architecture

```
app.py              # Streamlit UI (5 tabs, ~1200 lines)
sectors.py          # 11 sectors + source routing (Maps vs Dorking)
schema.py           # Lead dataclass (normalized fields)
scoring.py          # Weighted opportunity_score engine
utils.py            # safe_request, rate-limit, UA rotation, URL cleaning
enrich.py           # Website → WhatsApp/Email/IG/LI/FB extraction
outreach.py         # Pitch templates per sector
requirements.txt    # Pinned dependencies
```

---

## 🔑 Key Technical Highlights

| Feature | Implementation |
|---------|----------------|
| **Google Maps IP bypass** | URL format: `https://google.com/maps/search/{query}/@{lat},{lng},12z` using `CITY_COORDS` dict |
| **CAPTCHA/consent detection** | `page.locator('text="Before you continue"').is_visible()` — aborts cleanly with error message |
| **Fallback selectors** | Tries `div[role="article"]` → `a[href*="/maps/place/"]` → `div.Nv2PK` |
| **Debug artifacts** | Saves `debug/maps_page.png` + `debug/maps_page.html` on every run |
| **Contact enrichment** | Single HTTP request per website → BeautifulSoup extraction |
| **Scoring engine** | Rebuild (40%) + Contact completeness (30%) + Reviews (15%) + WhatsApp bonus (5%) + High-ticket (10%) |

---

## 📦 Requirements

```
streamlit>=1.35
pandas>=2.1
playwright>=1.40
beautifulsoup4>=4.12
lxml>=4.9
openpyxl>=3.1
```

---

## 🛡️ Ethical Scraping

- Only **publicly visible** data (Maps listings, public business pages, public IG/LI profiles via search)
- Respects `robots.txt` and rate-limits (≥1.5s between requests)
- No login-gated scraping, no private data
- GDPR/PDPL compliant — delete on request
- Query strings redacted in logs

---

## 🗺️ Roadmap

- [ ] Proxy rotation support
- [ ] CAPTCHA solving integration
- [ ] More dorking patterns (Twitter, YouTube, TikTok)
- [ ] CRM webhook export (HubSpot, Pipedrive, Close)
- [ ] Scheduled runs via cron

---

## 🤝 Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork → branch → PR
2. Keep changes focused & tested
3. Update docs if behavior changes

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⭐ Star This Repo

If Lead Empire helps you close deals, **give it a star** — it helps others discover it!

<p align="center">
  <a href="https://github.com/jhassanb597-sys/lead-generation/stargazers">
    <img src="https://img.shields.io/github/stars/jhassanb597-sys/lead-generation?style=social" alt="Stars" />
  </a>
  <a href="https://github.com/jhassanb597-sys/lead-generation/forks">
    <img src="https://img.shields.io/github/forks/jhassanb597-sys/lead-generation?style=social" alt="Forks" />
  </a>
</p>

---

**Keywords:** lead generation, google maps scraper, lead scraper, b2b lead generation, local business leads, streamlit app, playwright scraper, contact enrichment, opportunity scoring, sales intelligence