import re
import json
import sqlite3
import threading
import time
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta

from utils import safe_request

_DB_LOCK = threading.Lock()  # FIX-C3: serialize SQLite writes across threads
_DB_PATH = os.path.join("data", "signals_cache.db")
_DB_INITIALIZED = False


def _init_db():
    """Create schema + WAL once at import (single-threaded)."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    with _DB_LOCK:
        if _DB_INITIALIZED:
            return
        try:
            os.makedirs("data", exist_ok=True)
        except Exception:
            pass
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domain_signals (
                    domain TEXT PRIMARY KEY,
                    signals_json TEXT,
                    fetched_at INTEGER
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        _DB_INITIALIZED = True


_init_db()


def extract_site_signals(html: str, url: str) -> dict:  # WS-A1
    r"""
    PURE. No network. Returns:
    {"copyright_year": int|None, "wordpress_major": int|None,
     "jquery_major": int|None, "has_viewport": bool,
     "is_https": bool, "legacy_builder": str|None, "fetch_ok": bool}

    Regex sources:
      copyright: r"(?:©|copyright)\s*(20\d{2})"
      wordpress: r"wordpress[/\s]*([0-9])\."
      jquery:    r"jquery[-/]?([0-9])\."
      viewport:  '<meta' with name="viewport" (case-insensitive)
      legacy:    check for frontpage / dreamweaver / "wix.com" free patterns
    """
    signals = {
        "copyright_year": None,
        "wordpress_major": None,
        "jquery_major": None,
        "has_viewport": False,
        "is_https": url.startswith("https://"),
        "legacy_builder": None,
        "fetch_ok": bool(html),
    }

    # Copyright year
    match = re.search(r"(?:©|copyright)\s*(20\d{2})", html)
    if match:
        signals["copyright_year"] = int(match.group(1))

    # Wordpress major version (multi-digit)
    match = re.search(r"wordpress[/\s]*(\d+)\.", html, re.IGNORECASE)
    if match:
        signals["wordpress_major"] = int(match.group(1))

    # jQuery major version
    match = re.search(r"jquery[-/]?([0-9])\.", html, re.IGNORECASE)
    if match:
        signals["jquery_major"] = int(match.group(1))

    # Viewport meta tag
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE):
        signals["has_viewport"] = True

    # Legacy builder patterns
    legacy_patterns = {
        "FrontPage": r"frontpage",
        "Dreamweaver": r"dreamweaver",
        "Wix": r"wix\.com",
        "GoDaddy": r"godaddy\.com",
        "Squarespace": r"squarespace\.com",
    }
    for builder, pattern in legacy_patterns.items():
        if re.search(pattern, html, re.IGNORECASE):
            signals["legacy_builder"] = builder
            break

    return signals


def fetch_signals(url: str, timeout: int = 8) -> dict:  # WS-A1
    """
    Network wrapper around safe_request. On ANY failure return
    extract_site_signals("", url) with fetch_ok=False. Never raises.
    """
    try:
        response = safe_request(url, timeout=timeout)
        if response.status_code == 200 and response.text:
            return extract_site_signals(response.text, url)
        else:
            return extract_site_signals("", url)
    except Exception:
        return extract_site_signals("", url)


def fetch_signals_cached(url: str) -> dict:  # WS-A1
    """
    SQLite cache. File: data/signals_cache.db.
    Table: domain_signals(domain TEXT PRIMARY KEY, signals_json TEXT,
                          fetched_at INTEGER)
    TTL = 7 days. Key on domain (urlparse(url).netloc). Create table
    on import (idempotent). Return dict.
    """
    if not url:
        return extract_site_signals("", "")

    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if not domain:
        return extract_site_signals("", url)

    try:
        os.makedirs("data", exist_ok=True)
    except Exception:
        pass

    # Lock-free cache read (WAL allows concurrent readers).
    conn = None
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA busy_timeout = 10000")
        cursor = conn.cursor()
        cursor.execute("SELECT signals_json, fetched_at FROM domain_signals WHERE domain = ?", (domain,))
        row = cursor.fetchone()
        if row:
            signals_json, fetched_at = row
            if datetime.now() - datetime.fromtimestamp(fetched_at) < timedelta(days=7):
                return json.loads(signals_json)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    # Network fetch outside the lock; serialize only the DB write.
    signals = fetch_signals(url)
    signals_json = json.dumps(signals)
    fetched_at = int(time.time())

    with _DB_LOCK:  # FIX-C3: serialize DB writes under concurrency
        conn = None
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=10, check_same_thread=False)
            conn.execute("PRAGMA busy_timeout = 10000")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO domain_signals (domain, signals_json, fetched_at)
                VALUES (?, ?, ?)
                """,
                (domain, signals_json, fetched_at),
            )
            conn.commit()
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    return signals


def research_summary(lead: "Lead", signals: dict) -> str:  # WS-E3
    """
    Return a 2-3 sentence summary built from signals (Clay-style "research column").
    NO external API. Pure string assembly. Max ~280 chars.

    Args:
        lead: Lead object.
        signals: Dict from extract_site_signals.

    Returns:
        Human-readable summary string.
    """
    parts = []

    # Website status
    if not lead.website or lead.website == "N/A":
        parts.append("No website found.")
    else:
        https = "yes" if signals.get("is_https") else "no"
        parts.append(f"Site live, HTTPS: {https}.")

    # Rebuild signals
    signals_list = []
    wp = signals.get("wordpress_major")
    if wp and wp < 6:
        signals_list.append(f"Legacy WordPress {wp}.x")
    copyright_year = signals.get("copyright_year")
    if copyright_year and copyright_year < 2022:
        signals_list.append(f"Copyright {copyright_year}")
    legacy = signals.get("legacy_builder")
    if legacy:
        signals_list.append(f"Legacy builder: {legacy}")
    if signals_list:
        parts.append("Rebuild signals: " + "; ".join(signals_list) + ".")

    # Contact gaps
    missing = []
    if not lead.whatsapp or lead.whatsapp == "N/A":
        missing.append("WhatsApp")
    if not lead.instagram or lead.instagram == "N/A":
        missing.append("Instagram")
    if not lead.email or lead.email == "N/A":
        missing.append("Email")
    if missing:
        parts.append("Missing: " + ", ".join(missing) + ".")

    # Opportunity
    opp_parts = []
    if lead.sector.lower() in {"lawyer", "accountant", "dentist", "clinic", "real_estate", "b2b_agency", "architect", "interior_designer"}:
        opp_parts.append("High-ticket sector")
    if lead.review_count and lead.review_count > 50:  # FIX-C5: None is falsy
        opp_parts.append(f"{lead.review_count} reviews")
    if lead.rating and lead.rating >= 4.0:
        opp_parts.append(f"{lead.rating}★")
    if opp_parts:
        parts.append("Opportunity: " + ", ".join(opp_parts) + ".")

    summary = " ".join(parts)
    return summary[:280]