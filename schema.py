"""
NORMALIZED LEAD SCHEMA

Single canonical Lead dataclass used by all adapters and scoring.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Lead:
    """Canonical lead record populated by source adapters and scoring."""
    lead_id: str = ""
    name: str = ""
    sector: str = ""
    sub_sector: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    whatsapp: str = ""
    email: str = ""
    website: str = ""
    instagram: str = ""
    facebook: str = ""
    tiktok: str = ""
    linkedin: str = ""
    address: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None  # FIX-C5: None = unknown (Maps may not report it)
    rebuild_msg: str = ""               # FIX-M3: rebuild issues message (dataclass field)
    price_level: Optional[int] = None
    hours: str = ""
    source: str = ""
    source_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Scoring / enrichment fields
    has_website: bool = False
    rebuild_score: float = 0.0            # 0-10
    contact_completeness: float = 0.0     # 0..1 fraction
    opportunity_score: float = 0.0        # 0-100
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)