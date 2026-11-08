"""
SECTOR TAXONOMY + SOURCE ROUTER

Maps every sector of life to its best data sources.
Used by the Lead Empire app to route scraping across multiple sources.
"""

SECTORS = {
    "HEALTH": {"examples": ["dentist", "clinic", "physio", "pharmacy", "lab", "vet"], "sources": ["google_maps"]},
    "BEAUTY": {"examples": ["salon", "barber", "spa", "nail studio", "makeup artist"], "sources": ["google_maps"]},
    "FITNESS": {"examples": ["gym", "yoga studio", "personal trainer", "martial arts"], "sources": ["google_maps"]},
    "FOOD": {"examples": ["restaurant", "cafe", "bakery", "cloud kitchen", "caterer"], "sources": ["google_maps"]},
    "TRADES": {"examples": ["plumber", "electrician", "carpenter", "painter", "AC repair", "mechanic"], "sources": ["google_maps"]},
    "PROFESSIONAL": {"examples": ["lawyer", "accountant", "tax consultant", "notary"], "sources": ["google_maps"]},
    "REAL_ESTATE": {"examples": ["agent", "broker", "property manager", "interior designer", "architect"], "sources": ["google_maps"]},
    "HEALTHCARE_PROVIDERS": {"examples": ["doctor", "clinic", "dentist", "physician", "medical center"], "sources": ["google_maps"]},
    "SHOPS_SMALL_BUSINESS": {"examples": ["boutique", "grocery store", "electronics shop", "mobile shop", "pet store"], "sources": ["google_maps"]},
    
    # Social & Tech (Uses Google Dorking)
    "TECH_COMPANIES": {"examples": ["software company", "saas", "it agency", "tech startup", "web developer"], "sources": ["google_search_dorking"]},
    "INFLUENCERS": {"examples": ["instagram influencer", "youtube creator", "tiktok creator", "food blogger"], "sources": ["google_search_dorking"]},
}

def choose_sources(sector_name: str) -> list:
    if sector_name not in SECTORS: return ["google_maps"]
    return SECTORS[sector_name].get("sources", ["google_maps"])

def list_sectors() -> list:
    return sorted(SECTORS.keys())

def get_sector_examples(sector_name: str) -> list:
    return SECTORS.get(sector_name, {}).get("examples", [])