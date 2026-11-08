# Contributing to Lead Empire

Thank you for considering a contribution! 🎉

## Ways to Contribute

- **Bug reports** — Open an issue with steps to reproduce, expected vs actual behavior
- **Feature requests** — Describe the use case and proposed solution
- **Code improvements** — PRs for selectors, scoring logic, UI/UX, documentation
- **New sectors/sources** — Add to `sectors.py` and implement adapter in `app.py`

## Development Setup

```bash
git clone https://github.com/jhassanb597-sys/lead-generation.git
cd lead-generation
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```

## Pull Request Guidelines

1. **One change per PR** — Keep it focused
2. **Test locally** — Run with `DEMO_MODE=true` and without
3. **Update docs** — README, code comments, type hints
4. **No secrets** — Never commit API keys, proxies, or `.env` files
5. **Respect ethics** — No login-gated scraping, no private data

## Code Style

- Type hints on all public functions
- `black` formatting (88 chars)
- Clear variable names, minimal comments
- Handle exceptions gracefully (log + continue, don't crash)

## Adding a New Sector

1. Edit `sectors.py` → add entry to `SECTORS` dict:
   ```python
   "NEW_SECTOR": {
       "examples": ["sub1", "sub2"],
       "sources": ["google_maps"]  # or ["google_search_dorking"]
   }
   ```
2. If new source type needed → implement `scrape_new_source()` in `app.py` and add to `ADAPTER_MAP`
3. Test with `DEMO_MODE=true` first

## Reporting Security Issues

Email directly (don't open public issue) for anything involving:
- Proxy credentials leakage
- PII handling
- Rate-limit bypasses

---

**First-time contributor?** Look for `good first issue` labels or ask in Discussions.