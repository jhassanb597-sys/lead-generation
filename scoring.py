"""
SCORING ENGINE

Replaces the weak rebuild heuristic with a weighted multi-factor score.
Returns a copy of the Lead; never mutates the original.
"""

from dataclasses import replace
from datetime import datetime

from schema import Lead


HIGH_TICKET_SECTORS = {
    "lawyer", "accountant", "dentist", "clinic", "real_estate",
    "b2b_agency", "architect", "interior_designer",
}

CURRENT_YEAR = datetime.now().year


def score_lead(lead: Lead, signals: dict | None = None, context: dict | None = None) -> Lead:  # WS-E1
    """
    PURE function. Performs no I/O.

    Score a lead across rebuild potential, contact completeness, and opportunity.
    Supports optional context for tier-based weighting (Apollo-style local tuning).

    Args:
        lead: Original Lead instance (not mutated).
        signals: Optional signals dict from extract_site_signals (cached).
            If None, all signals are considered as None (do NOT fetch).
        context: Optional dict with keys:
            - sector_tier: "high" | "med" | "low"
            - city_tier: "metro" | "secondary"
            - review_velocity: float (review_count / 100)

    Returns:
        New Lead instance with scoring fields populated.
    """
    out = replace(lead)

    # ----- rebuild_score (0-10) weighted sum -----
    rebuild_score = 0.0

    # no website .............................. +4
    if not out.website or out.website == "N/A":
        rebuild_score += 4.0

    # Use signals if provided, otherwise treat as None (do NOT fetch)
    signals_dict = signals or {}

    # copyright_year < current_year-2 .............................. +2
    copyright_year = signals_dict.get("copyright_year")
    if copyright_year and copyright_year < CURRENT_YEAR - 2:
        rebuild_score += 2.0

    # wordpress_major < 6 .................................... +1.5
    wordpress_major = signals_dict.get("wordpress_major")
    if wordpress_major and wordpress_major < 6:
        rebuild_score += 1.5

    # jquery_major < 2 .................................. +1
    jquery_major = signals_dict.get("jquery_major")
    if jquery_major and jquery_major < 2:
        rebuild_score += 1.0

    # legacy_builder .................................... +1
    legacy_builder = signals_dict.get("legacy_builder")
    if legacy_builder:
        rebuild_score += 1.0

    # has_viewport False and website ........................... +1
    has_viewport = signals_dict.get("has_viewport", False)
    if not has_viewport and out.website and out.website != "N/A":
        rebuild_score += 1.0

    # is_https False and website .......................... +0.5
    is_https = signals_dict.get("is_https", False)
    if not is_https and out.website and out.website != "N/A":
        rebuild_score += 0.5

    out.rebuild_score = min(round(rebuild_score, 1), 10.0)

    # ----- contact_completeness (0..1) -----
    contact_fields = [
        out.phone, out.whatsapp, out.email,
        out.instagram, out.facebook, out.website,
    ]
    present = sum(1 for f in contact_fields if f and f != "N/A")
    out.contact_completeness = round(present / len(contact_fields), 2)

    # ----- context defaults -----
    ctx = context or {}
    sector_tier = ctx.get("sector_tier", "med")
    city_tier = ctx.get("city_tier", "secondary")
    # FIX-C5: None review_count = unknown; treat as 0 for velocity (no award, no penalty)
    rc = out.review_count if out.review_count is not None else 0
    review_velocity = ctx.get("review_velocity", min(rc / 100, 1))

    # ----- opportunity_score (0-100) -----
    # rebuild/10 * 45
    rebuild_component = (out.rebuild_score / 10) * 45
    # contact_completeness * 20
    contact_component = out.contact_completeness * 20
    # review_velocity_clamped * 15
    rv_clamped = min(review_velocity, 1.0) if review_velocity else 0.0
    review_component = rv_clamped * 15
    # sector_tier_bonus: high=10, med=5, low=0
    tier_bonus_map = {"high": 10, "med": 5, "low": 0}
    sector_tier_bonus = tier_bonus_map.get(str(sector_tier).lower(), 5)
    # city_tier_bonus: metro=5, secondary=3, other=0
    city_bonus_map = {"metro": 5, "secondary": 3}
    city_tier_bonus = city_bonus_map.get(str(city_tier).lower(), 0)
    # whatsapp_bonus
    whatsapp_bonus = 5 if out.whatsapp and out.whatsapp != "N/A" else 0
    # high_ticket_sector
    high_ticket_bonus = 5 if out.sector.lower() in HIGH_TICKET_SECTORS else 0

    opportunity_score = (
        rebuild_component
        + contact_component
        + review_component
        + sector_tier_bonus
        + city_tier_bonus
        + whatsapp_bonus
        + high_ticket_bonus
    )
    out.opportunity_score = round(min(max(opportunity_score, 0.0), 100.0), 2)
    out.has_website = bool(out.website and out.website != "N/A")

    return out


def match_icp(leads: list, icp: dict) -> list:  # WS-E2
    """
    Pure function. Filter leads by Ideal Customer Profile criteria.
    All criteria are optional; None means "skip this filter".

    Args:
        leads: List of Lead objects.
        icp: Dict with optional keys:
            - sectors: list[str] (exact match on sector)
            - cities: list[str] (case-insensitive substring match)
            - min_score: int (opportunity_score >= min_score)
            - max_score: int | None (opportunity_score <= max_score)
            - requires_phone: bool
            - requires_whatsapp: bool
            - has_website: bool | None (True/False/None)
            - min_reviews: int | None (review_count >= min_reviews)

    Returns:
        Filtered list of Lead objects.
    """
    result = []
    for lead in leads:
        # sectors filter
        if "sectors" in icp and icp["sectors"]:
            if lead.sector not in icp["sectors"]:
                continue
        # cities filter (case-insensitive substring)
        if "cities" in icp and icp["cities"]:
            city_lower = (lead.city or "").lower()
            if not any(c.lower() in city_lower for c in icp["cities"]):
                continue
        # min_score
        if "min_score" in icp and icp["min_score"] is not None:
            if lead.opportunity_score < icp["min_score"]:
                continue
        # max_score
        if "max_score" in icp and icp["max_score"] is not None:
            if lead.opportunity_score > icp["max_score"]:
                continue
        # requires_phone
        if "requires_phone" in icp and icp["requires_phone"]:
            if not lead.phone or lead.phone == "N/A":
                continue
        # requires_whatsapp
        if "requires_whatsapp" in icp and icp["requires_whatsapp"]:
            if not lead.whatsapp or lead.whatsapp == "N/A":
                continue
        # has_website
        if "has_website" in icp and icp["has_website"] is not None:
            lead_has = bool(lead.website and lead.website != "N/A")
            if lead_has != icp["has_website"]:
                continue
        # min_reviews
        if "min_reviews" in icp and icp["min_reviews"] is not None:
            # FIX-C5: None review_count fails a min_reviews filter (unknown < threshold)
            if lead.review_count is None or lead.review_count < icp["min_reviews"]:
                continue
        result.append(lead)
    return result


def score_breakdown(lead: Lead, signals: dict | None = None, context: dict | None = None) -> dict:  # WS-E1
    """
    Return component-level breakdown of the opportunity score for UI "why this score" panel.

    Returns dict with keys:
        rebuild_component, contact_component, review_component,
        sector_tier_bonus, city_tier_bonus, whatsapp_bonus, high_ticket_bonus,
        total
    """
    signals_dict = signals or {}
    ctx = context or {}

    # rebuild_score recomputation for breakdown
    rebuild_score = 0.0
    if not lead.website or lead.website == "N/A":
        rebuild_score += 4.0
    copyright_year = signals_dict.get("copyright_year")
    if copyright_year and copyright_year < CURRENT_YEAR - 2:
        rebuild_score += 2.0
    wordpress_major = signals_dict.get("wordpress_major")
    if wordpress_major and wordpress_major < 6:
        rebuild_score += 1.5
    jquery_major = signals_dict.get("jquery_major")
    if jquery_major and jquery_major < 2:
        rebuild_score += 1.0
    legacy_builder = signals_dict.get("legacy_builder")
    if legacy_builder:
        rebuild_score += 1.0
    has_viewport = signals_dict.get("has_viewport", False)
    if not has_viewport and lead.website and lead.website != "N/A":
        rebuild_score += 1.0
    is_https = signals_dict.get("is_https", False)
    if not is_https and lead.website and lead.website != "N/A":
        rebuild_score += 0.5
    rebuild_score = min(round(rebuild_score, 1), 10.0)

    # contact_completeness
    contact_fields = [
        lead.phone, lead.whatsapp, lead.email,
        lead.instagram, lead.facebook, lead.website,
    ]
    present = sum(1 for f in contact_fields if f and f != "N/A")
    contact_completeness = round(present / len(contact_fields), 2)

    # components
    rebuild_component = round((rebuild_score / 10) * 45, 2)
    contact_component = round(contact_completeness * 20, 2)
    # FIX-C5: guard None review_count
    _rc = lead.review_count if lead.review_count is not None else 0
    rv_clamped = min(ctx.get("review_velocity", min(_rc / 100, 1)), 1.0) if ctx.get("review_velocity") else 0.0
    review_component = round(rv_clamped * 15, 2)

    tier_bonus_map = {"high": 10, "med": 5, "low": 0}
    sector_tier_bonus = tier_bonus_map.get(str(ctx.get("sector_tier", "med")).lower(), 5)

    city_bonus_map = {"metro": 5, "secondary": 3}
    city_tier_bonus = city_bonus_map.get(str(ctx.get("city_tier", "secondary")).lower(), 0)

    whatsapp_bonus = 5 if lead.whatsapp and lead.whatsapp != "N/A" else 0
    high_ticket_bonus = 5 if lead.sector.lower() in HIGH_TICKET_SECTORS else 0

    total = round(
        rebuild_component + contact_component + review_component
        + sector_tier_bonus + city_tier_bonus + whatsapp_bonus + high_ticket_bonus, 2
    )

    return {
        "rebuild_component": rebuild_component,
        "contact_component": contact_component,
        "review_component": review_component,
        "sector_tier_bonus": sector_tier_bonus,
        "city_tier_bonus": city_tier_bonus,
        "whatsapp_bonus": whatsapp_bonus,
        "high_ticket_bonus": high_ticket_bonus,
        "total": total,
    }
