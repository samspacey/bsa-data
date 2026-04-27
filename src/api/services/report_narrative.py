"""Build per-society narrative content for the PDF report.

Replaces the hardcoded quote + recommendations (previously identical
across every society) with content derived from the real review and
score data for the society in question.

Two pieces:

1. ``pick_representative_quote(society_id)`` - pulls a real review from
   the society's corpus that's quotable: strong sentiment (positive or
   negative depending on which is more telling for that society),
   reasonable length, recent.

2. ``recommendations_for(scores)`` - templated guidance based on the
   society's two weakest factors and one strongest. Each factor has its
   own copy for "below avg" and "above avg" framings, so the
   recommendations actually reflect what's specific to this society.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.api.services.scores import ScoreRow
from src.data.models import PublicReview, SentimentAspect


# ─────────────────────────────────────────────────────────────────────
# Quote selection
# ─────────────────────────────────────────────────────────────────────

# A "quotable" body falls in this length window. Too short = no context,
# too long = won't fit in the dark navy quote card on the PDF.
QUOTE_MIN_CHARS = 60
QUOTE_MAX_CHARS = 220


def pick_representative_quote(
    session: Session,
    society_id: str,
    overall_sentiment: float,
) -> tuple[Optional[str], Optional[str]]:
    """Return (quote_text, attribution) for a representative review.

    Picks the strongest signal in the direction the society's overall
    sentiment is leaning. So a society with overall negative sentiment
    gets quoted on a member's negative experience; a society with
    strongly positive sentiment gets quoted on praise. Falls back to
    the most-extreme review if both directions are sparse.
    """
    cutoff = date.today() - timedelta(days=730)

    base_q = (
        session.query(
            PublicReview.body_text_clean,
            PublicReview.body_text_raw,
            PublicReview.review_date,
            PublicReview.source_id,
            SentimentAspect.overall_sentiment_score,
        )
        .join(SentimentAspect, SentimentAspect.review_id == PublicReview.id)
        .filter(PublicReview.building_society_id == society_id)
        .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
        .filter(SentimentAspect.aspect == "overall")
        .filter(PublicReview.review_date >= cutoff)
        .filter(
            func.length(
                func.coalesce(PublicReview.body_text_clean, PublicReview.body_text_raw)
            ).between(QUOTE_MIN_CHARS, QUOTE_MAX_CHARS)
        )
    )

    if overall_sentiment < -0.1:
        # Society is broadly unhappy — quote the strongest negative voice.
        order = SentimentAspect.overall_sentiment_score.asc()
        direction = "negative"
    elif overall_sentiment > 0.1:
        # Society is broadly happy — quote the strongest positive voice.
        order = SentimentAspect.overall_sentiment_score.desc()
        direction = "positive"
    else:
        # Mixed - lean negative (more newsworthy in a board report).
        order = SentimentAspect.overall_sentiment_score.asc()
        direction = "mixed"

    row = base_q.order_by(order).first()

    if row is None:
        return None, None

    body = (row[0] or row[1] or "").strip()
    if not body:
        return None, None

    # Strip leading "Title. Title." duplications that Trustpilot scrapes
    # sometimes produce (where the title and first sentence repeat).
    body = _dedupe_leading_clause(body)

    rev_date = row[2]
    source_id = row[3]
    n_total = base_q.count()

    source_label = {
        "trustpilot": "Trustpilot",
        "smartmoneypeople": "Smart Money People",
        "feefo": "Feefo",
        "app_store": "App Store",
        "play_store": "Play Store",
    }.get(source_id, source_id)

    flavour = "negative review" if direction == "negative" else "positive review"
    attribution = (
        f"Drawn from a {flavour} on {source_label}, "
        f"{rev_date.strftime('%b %Y')}. "
        f"Selected from {n_total} comparable recent reviews."
    )
    return body, attribution


def _dedupe_leading_clause(body: str) -> str:
    """Trustpilot scrapes often produce 'Foo bar baz. Foo bar baz...' where
    the title and first sentence are identical. Trim the duplicate so the
    quote reads cleanly."""
    parts = body.split(". ", 1)
    if len(parts) == 2 and parts[0].strip().lower() == parts[1].split(".", 1)[0].strip().lower():
        return parts[1]
    return body


# ─────────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────────

# Per-factor copy for when the society is BELOW industry average on it.
# Each entry takes a single placeholder for the score so the recommendation
# can reference the actual number.
WEAKNESS_COPY: dict[str, str] = {
    "Customer Service": (
        "Lift customer service. At {score:.1f} you're below the sector average and this is the "
        "factor that drives most word-of-mouth in the data; small wins here compound."
    ),
    "Digital Experience": (
        "Close the digital gap. Score of {score:.1f} reflects friction with the app and sign-in flows; "
        "this is the most-mentioned issue in recent reviews."
    ),
    "Branch Experience": (
        "Protect branch experience. Members anchor their relationship there and your {score:.1f} suggests "
        "recent staffing or hours changes are landing badly."
    ),
    "Mortgage Products": (
        "Reposition mortgage products. {score:.1f} is below sector average; competitive rate windows and "
        "advisor accessibility are the recurring complaints."
    ),
    "Savings Rates": (
        "Revisit savings rate competitiveness. At {score:.1f} you're trailing peers and members are "
        "explicitly comparing your rates to others in their reviews."
    ),
    "Communication": (
        "Tighten communication around complaints. A score of {score:.1f} indicates members feel ignored or "
        "passed around; visible follow-through on complaints would shift this fast."
    ),
    "Local Community": (
        "Re-establish local presence. {score:.1f} is below sector and members are asking for stronger "
        "community signals - branch events, local sponsorship, named contacts."
    ),
}

# Per-factor copy for when the society is ABOVE industry average. These
# frame the strength as something to lean into in marketing or culture.
STRENGTH_COPY: dict[str, str] = {
    "Customer Service": (
        "Lean into your customer service advantage. {score:.1f} puts you above the sector and members "
        "consistently call out staff by name - your story should foreground this."
    ),
    "Digital Experience": (
        "Use your digital lead. At {score:.1f} you're above sector; the app and sign-in flows are a "
        "differentiator most peers can't claim."
    ),
    "Branch Experience": (
        "Protect and amplify branch experience. {score:.1f} is well above sector and is the clearest "
        "differentiator from the digital-only challengers."
    ),
    "Mortgage Products": (
        "Build the mortgage story. {score:.1f} is sector-leading; broker channels and advisor reviews "
        "will travel further than rate-only marketing."
    ),
    "Savings Rates": (
        "Lead with rate competitiveness. At {score:.1f} you're above sector and members reference this "
        "as the reason they joined - lean into it in onboarding."
    ),
    "Communication": (
        "Codify how you handle complaints. {score:.1f} is above sector and the qualitative reviews show "
        "members feel heard - turn this into a process you can scale."
    ),
    "Local Community": (
        "Lead communications with the community narrative. {score:.1f} is among the strongest signals in "
        "the data and is your most under-expressed differentiator."
    ),
}

GENERIC_FALLBACK = (
    "Sustain the broader member experience. The data does not single out a sharp gap or a sharp "
    "strength; the work is in incremental gains across the seven factors."
)


def recommendations_for(scores: list[ScoreRow]) -> list[str]:
    """Generate three bespoke recommendations from the society's scores.

    Strategy: two recommendations on the worst factors (where the gap is
    biggest), one on the strongest factor. If a society has fewer than
    two distinct weaknesses or no clear strength, fill remaining slots
    with a generic fallback so the report always has three.
    """
    if not scores:
        return [GENERIC_FALLBACK] * 3

    by_diff_asc = sorted(scores, key=lambda s: (s.score - s.avg))  # most negative diff first
    by_diff_desc = sorted(scores, key=lambda s: -(s.score - s.avg))

    weaknesses = [s for s in by_diff_asc if s.status == "below"]
    strengths = [s for s in by_diff_desc if s.status == "above"]

    out: list[str] = []
    used_factors: set[str] = set()

    # Up to two weaknesses
    for s in weaknesses[:2]:
        if s.factor in used_factors:
            continue
        template = WEAKNESS_COPY.get(s.factor)
        if template:
            out.append(template.format(score=s.score))
            used_factors.add(s.factor)

    # One strength (skip if already used as weakness, which can't happen,
    # but the guard is cheap).
    for s in strengths[:1]:
        if s.factor in used_factors:
            continue
        template = STRENGTH_COPY.get(s.factor)
        if template:
            out.append(template.format(score=s.score))
            used_factors.add(s.factor)

    # If a society is exclusively above-average (rare but possible for
    # the strongest performers), pad with another strength.
    if len(out) < 3:
        for s in strengths[1:]:
            if s.factor in used_factors:
                continue
            template = STRENGTH_COPY.get(s.factor)
            if template:
                out.append(template.format(score=s.score))
                used_factors.add(s.factor)
            if len(out) >= 3:
                break

    # If a society is exclusively below-average, pad with another weakness.
    if len(out) < 3:
        for s in weaknesses[2:]:
            if s.factor in used_factors:
                continue
            template = WEAKNESS_COPY.get(s.factor)
            if template:
                out.append(template.format(score=s.score))
                used_factors.add(s.factor)
            if len(out) >= 3:
                break

    while len(out) < 3:
        out.append(GENERIC_FALLBACK)

    return out[:3]


def overall_sentiment_for_society(session: Session, society_id: str) -> float:
    """Return the society's overall sentiment_score (avg) used to bias
    quote selection. 0.0 if no data."""
    val = (
        session.query(func.avg(SentimentAspect.overall_sentiment_score))
        .join(PublicReview, PublicReview.id == SentimentAspect.review_id)
        .filter(PublicReview.building_society_id == society_id)
        .filter(SentimentAspect.aspect == "overall")
        .scalar()
    )
    return float(val) if val is not None else 0.0
