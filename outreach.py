"""
OUTREACH TEMPLATE ENGINE (Apollo-style sequences, simplified)

String formatting only. No LLM. No network calls.
"""

from schema import Lead


def render_pitch(lead: Lead, signals: dict, template: str = "default") -> str:  # WS-E4
    """
    Render a multi-line pitch using placeholders.

    Placeholders:
        {name}, {city}, {sector}, {rating}, {reviews},
        {rebuild_reason}, {contact_gap}, {pitch_angle}

    Args:
        lead: Lead object.
        signals: Dict from extract_site_signals.
        template: "default" | "short" | "whatsapp"

    Returns:
        Rendered pitch string.
    """
    # Build rebuild_reason
    rebuild_reason = _build_rebuild_reason(lead, signals)

    # Build contact_gap
    contact_gap = _build_contact_gap(lead)

    # Build pitch_angle based on priority
    pitch_angle = _build_pitch_angle(lead, signals)

    name = lead.name or "there"
    city = lead.city or "your area"
    sector = lead.sector or "your industry"
    rating = f"{lead.rating:.1f}" if lead.rating else "N/A"
    reviews = str(lead.review_count) if lead.review_count else "N/A"

    if template == "short":
        return _short_template(
            name=name, city=city, sector=sector,
            rebuild_reason=rebuild_reason, pitch_angle=pitch_angle
        )
    elif template == "whatsapp":
        return _whatsapp_template(
            name=name, city=city, sector=sector,
            rebuild_reason=rebuild_reason, contact_gap=contact_gap,
            pitch_angle=pitch_angle, rating=rating, reviews=reviews
        )
    else:
        return _default_template(
            name=name, city=city, sector=sector,
            rebuild_reason=rebuild_reason, contact_gap=contact_gap,
            pitch_angle=pitch_angle, rating=rating, reviews=reviews
        )


def _build_rebuild_reason(lead: Lead, signals: dict) -> str:
    """Build a short rebuild reason string from signals."""
    if not lead.website or lead.website == "N/A":
        return "No website found"
    reasons = []
    wp = signals.get("wordpress_major")
    if wp and wp < 6:
        reasons.append(f"Legacy WordPress {wp}.x")
    copyright_year = signals.get("copyright_year")
    if copyright_year and copyright_year < 2022:
        reasons.append(f"Copyright {copyright_year}")
    legacy = signals.get("legacy_builder")
    if legacy:
        reasons.append(f"Legacy builder: {legacy}")
    if not signals.get("has_viewport"):
        reasons.append("Not mobile friendly")
    if not signals.get("is_https"):
        reasons.append("Not HTTPS")
    if not reasons:
        return "Site needs modernization"
    return "; ".join(reasons)


def _build_contact_gap(lead: Lead) -> str:
    """Build a contact gap string."""
    missing = []
    if not lead.whatsapp or lead.whatsapp == "N/A":
        missing.append("WhatsApp")
    if not lead.instagram or lead.instagram == "N/A":
        missing.append("Instagram")
    if not lead.email or lead.email == "N/A":
        missing.append("Email")
    if missing:
        return "Missing: " + ", ".join(missing)
    return "All key contacts available"


def _build_pitch_angle(lead: Lead, signals: dict) -> str:
    """Build pitch angle based on priority."""
    if not lead.website or lead.website == "N/A":
        return "You're invisible on Google"
    wp = signals.get("wordpress_major")
    copyright_year = signals.get("copyright_year")
    legacy = signals.get("legacy_builder")
    if wp and wp < 6:
        return "Your site signals 2015 to customers"
    if copyright_year and copyright_year < 2022:
        return "Your site signals 2015 to customers"
    if legacy:
        return "Your site signals 2015 to customers"
    if not lead.whatsapp or lead.whatsapp == "N/A":
        return "Customers can't reach you on WhatsApp"
    return "Your site needs modernization"


def _default_template(name, city, sector, rebuild_reason, contact_gap, pitch_angle, rating, reviews) -> str:
    return f"""Hi {name},

I checked your {sector} business in {city} — {pitch_angle}.

Rebuild signals: {rebuild_reason}
Contact gaps: {contact_gap}

With {rating}★ and {reviews} reviews, you have strong demand but weak online presence.

I can rebuild your site modern + WhatsApp integration in 3 days for Rs 30k.

Worth a 5-min call?

Thanks!"""


def _short_template(name, city, sector, rebuild_reason, pitch_angle) -> str:
    return f"""Hi {name},

Your {sector} business in {city}: {pitch_angle}.

Rebuild signals: {rebuild_reason}

I can rebuild it modern + WhatsApp booking in 3 days.

Worth a quick call?

Thanks!"""


def _whatsapp_template(name, city, sector, rebuild_reason, contact_gap, pitch_angle, rating, reviews) -> str:
    return f"""Hi {name} 👋

Saw your {sector} in {city} — {pitch_angle}.

Rebuild: {rebuild_reason}
Contact gap: {contact_gap}

{rating}★ / {reviews} reviews — strong demand.

Can I send a 3-day rebuild proposal (Rs 30k)?

Thanks!"""