# Lead Empire — Multi-Source Lead Engine

A Streamlit + Playwright lead-generation app that captures real data across every
sector of life: local trades, professional services, B2B, home-based micro-businesses,
creators, e-commerce, real estate, and more.

## Install

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
streamlit run app.py
```

### DEMO_MODE (no Playwright / no network required)

Set the environment variable before running:

```bash
# PowerShell
$env:DEMO_MODE="true"
streamlit run app.py

# CMD
set DEMO_MODE=true
streamlit run app.py
```

When `DEMO_MODE=true`, every source adapter returns 5 mock leads so the app runs
without Playwright installed (ideal for demos / CI / offline presentations).

## Ethical Scraping

Only scrape **publicly visible** data (Google Maps listings, public business pages).
Respect `robots.txt` and rate-limit requests (≥1.5s between hits to the same host).
Do not scrape login-gated content or private data. Delete user data on request —
GDPR / PDPL compliant. Never log full URLs containing PII; query strings are redacted
in logs.

## Tabs

| Tab | Purpose |
|-----|---------|
| 1. Lead Finder | Pick a sector + sub-sector + city; run adapters in parallel; dedupe + score; export CSV/Excel |
| 2. Bulk Auditor | Paste up to 100 URLs or upload CSV; run rebuild scoring + contact enrichment; export Excel |
| 3. Lead Triage | Rank by opportunity score; copy-to-clipboard pitch scripts; mark as contacted |
| 4. Single Audit | Paste one website; get rebuild-score breakdown + enriched contacts + proposal |
| 5. Export & Strategy | Multi-sheet Excel export (Leads / Audits / Scoring Breakdown); per-sector pitch scripts |

## Project Structure

```
app.py              # Main Streamlit app (5 tabs)
sectors.py          # SECTORS dict + choose_sources() router
schema.py           # Normalized Lead dataclass
scoring.py          # score_lead() weighted scoring engine
utils.py            # safe_request() + rate-limit + UA rotation
requirements.txt    # Python dependencies
.streamlit/config.toml  # Dark theme branding
README.md           # This file
.gitignore
```

## Key Fixes (Part A)

- `clean_url()`: guarded `split("q=")[1]` against `IndexError`; replaced chained fallback
  splits with a loop of safe, guarded trims
- Maps URL construction: uses `urllib.parse.quote_plus()` so spaces are encoded
- Playwright block: wrapped in `try/except/finally`; `browser.close()` in `finally`
- Post-`page.goto()`: `wait_for_selector('div[role="article"]')`, no-results warning,
  CAPTCHA/unusual-traffic detection and clean abort
- Removed duplicate `page.locator(...)` call; compute `cards` once
- `page.keyboard.press("Escape")` → `page.mouse.click(10, 10)`
- `page.wait_for_timeout(3500)` → `wait_for_selector` + short 500ms settle
- Progress bar created once; updates with `(i + 1) / max(len(cards), 1)`
- 2-retry loop around card clicks; skip + warn on persistent failure
- `check_rebuild_needed()`: removed hardcoded `"2019"/"2018"`; added anchored regexes
  for copyright year, WordPress major version, legacy jQuery, legacy builders
- Tab 4: rejects Google Maps URLs with a warning; never passes them into
  `check_rebuild_needed` / `enrich_contacts`