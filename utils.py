"""
SHARED NETWORK UTILITIES

Every network call must go through safe_request().
Never surface tracebacks to the user.
"""

import random
import time
import requests

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
]

# Simple in-memory rate limit per host
_last_hit: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 1.5


def safe_request(url: str, timeout: int = 10) -> requests.Response:
    """
    Safe GET request with UA rotation, rate limiting, and error suppression.

    Args:
        url: Target URL (query strings may contain PII; only the host is logged on error).
        timeout: Request timeout in seconds.

    Returns:
        requests.Response on success, or a synthetic Response with status_code=-1 on failure.
    """
    try:
        # Rate-limit per host
        host = url.split("//")[-1].split("/")[0]
        now = time.time()
        last = _last_hit.get(host, 0)
        elapsed = now - last
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)
        _last_hit[host] = time.time()

        headers = {"User-Agent": random.choice(_USER_AGENTS)}
        return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except Exception:
        # Synthetic failed response so callers never see tracebacks
        class _FailedResponse:
            status_code = -1
            text = ""
            def json(self):
                raise NotImplementedError("failed response has no JSON body")
        return _FailedResponse()


def redact_url(url: str) -> str:
    """Strip query strings from a URL for safe logging."""
    try:
        base = url.split("?")[0]
        return base
    except Exception:
        return "unknown"


def lead_fingerprint(lead: "Lead") -> str:  # WS-E7
    """
    Hash of (name.lower().strip(), phone or domain or "").
    Used for cross-session deduplication.
    """
    import hashlib
    name = (lead.name or "").lower().strip()
    phone = lead.phone or ""
    domain = ""
    if lead.website and lead.website != "N/A":
        from urllib.parse import urlparse
        domain = urlparse(lead.website).netloc.lower()
    key = f"{name}|{phone}|{domain}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def dedupe_against_history(leads: list, history_path: str = "data/seen.json") -> list:  # WS-E7
    """
    Load seen fingerprints, filter out matches, return new leads only.
    Caller must call mark_as_seen(leads) after user confirms.
    """
    import json
    seen = set()
    try:
        with open(history_path, "r") as f:
            seen = set(json.load(f))
    except Exception:
        pass
    return [l for l in leads if lead_fingerprint(l) not in seen]


def mark_as_seen(leads: list, history_path: str = "data/seen.json"):  # WS-E7
    """Append new fingerprints to history file."""
    import json
    seen = set()
    try:
        with open(history_path, "r") as f:
            seen = set(json.load(f))
    except Exception:
        pass
    for l in leads:
        seen.add(lead_fingerprint(l))
    try:
        with open(history_path, "w") as f:
            json.dump(list(seen), f)
    except Exception:
        pass


def enrich_social_profile(url: str) -> dict:
    """
    Fetch ONE public social profile URL and extract:
      - name (from og:title / <title>, strip platform suffixes)
      - email (from mailto: links or bio text)
      - phone (from tel: links)
      - bio (from og:description, max 280 chars)
      - source (inferred from hostname: facebook/instagram/linkedin/x)
    Returns dict with keys: name, email, phone, bio, source, url.
    Returns {"error": "..."} on failure. Never raises.
    """
    import re
    from urllib.parse import urlparse

    try:
        resp = safe_request(url, timeout=10)
        if resp.status_code != 200 or not resp.text:
            return {"error": f"HTTP {resp.status_code}"}
        
        html = resp.text
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        # Infer source from hostname
        if "facebook.com" in host:
            source = "facebook"
        elif "instagram.com" in host:
            source = "instagram"
        elif "linkedin.com" in host:
            source = "linkedin"
        elif "x.com" in host or "twitter.com" in host:
            source = "x"
        else:
            source = "unknown"
        
        # Extract name from og:title or <title>
        name = None
        og_title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html, re.I)
        if og_title_match:
            name = og_title_match.group(1)
        else:
            title_match = re.search(r"<title>([^<]+)</title>", html, re.I)
            if title_match:
                name = title_match.group(1)
        if name:
            # Strip common platform suffixes
            name = re.sub(r"\s*\|\s*(Facebook|Instagram|LinkedIn|Twitter|X)$", "", name, flags=re.I)
            name = name.strip()
        
        # Extract email from mailto: links or bio text
        email = None
        mailto_match = re.search(r'mailto:([^"\'?&>]+)', html, re.I)
        if mailto_match:
            email = mailto_match.group(1)
        else:
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}', html)
            if email_match:
                email = email_match.group(0)
        
        # Extract phone from tel: links
        phone = None
        tel_match = re.search(r'tel:([^"\'?&>]+)', html, re.I)
        if tel_match:
            phone = tel_match.group(1)
        
        # Extract bio from og:description
        bio = None
        og_desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html, re.I)
        if og_desc_match:
            bio = og_desc_match.group(1)
        elif "instagram.com" in host:
            # Instagram often puts bio in a specific meta tag
            meta_desc = re.search(r'<meta name="description" content="([^"]+)"', html, re.I)
            if meta_desc:
                bio = meta_desc.group(1)
        if bio:
            bio = bio[:280]
        
        return {
            "name": name or "",
            "email": email or "",
            "phone": phone or "",
            "bio": bio or "",
            "source": source,
            "url": url,
        }
    except Exception as e:
        return {"error": str(e)[:200]}