"""Reviews endpoints - featured reviews for screensaver etc."""

import random
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, desc

from src.config.societies import SOCIETY_BY_ID
from src.data.database import get_engine, get_session
from src.data.models import PublicReview, SentimentAspect


router = APIRouter(prefix="/reviews", tags=["reviews"])


class FeaturedReview(BaseModel):
    """Minimal review payload for the screensaver's 'what members are saying' panel."""

    id: int
    quote: str
    rating: int
    review_date: date
    society_id: str
    society_name: str
    source_id: str


class SocietyReview(BaseModel):
    """Review payload for the per-society evidence panel."""

    id: int
    snippet_id: str
    body: str
    rating: int
    review_date: date
    society_id: str
    society_name: str
    source: str  # human-readable source name
    source_id: str
    sentiment_label: str  # very_positive | positive | neutral | negative | very_negative
    source_url: Optional[str] = None


# Hand-picked fallbacks in case the DB hasn't been populated yet. Keeps the
# screensaver looking alive on a fresh clone.
FALLBACK_QUOTES = [
    FeaturedReview(
        id=-1,
        quote="The branch closes at 3pm now. That's useless if you work. Feels like they're pushing us online.",
        rating=2,
        review_date=date(2026, 2, 1),
        society_id="monmouthshire",
        society_name="Monmouthshire Building Society",
        source_id="trustpilot",
    ),
    FeaturedReview(
        id=-2,
        quote="Our advisor actually listened. She spotted an error on our application we hadn't noticed and fixed it before submission.",
        rating=5,
        review_date=date(2026, 1, 15),
        society_id="yorkshire",
        society_name="Yorkshire Building Society",
        source_id="smartmoneypeople",
    ),
    FeaturedReview(
        id=-3,
        quote="Loyalty doesn't pay. Their rates are half a percent below what I can get elsewhere.",
        rating=2,
        review_date=date(2026, 2, 10),
        society_id="nationwide",
        society_name="Nationwide Building Society",
        source_id="trustpilot",
    ),
    FeaturedReview(
        id=-4,
        quote="It's not just banking. It's a little social outing.",
        rating=5,
        review_date=date(2025, 12, 5),
        society_id="cumberland",
        society_name="Cumberland Building Society",
        source_id="feefo",
    ),
]


@router.get("/featured", response_model=list[FeaturedReview])
async def featured_reviews(limit: int = 10) -> list[FeaturedReview]:
    """Return a variety of real review quotes across different societies.

    Criteria for selection:
    - Body length between 60 and 260 characters (fits the screensaver card)
    - Rating is extreme (1-2 or 4-5) - more quotable than 3-star 'meh'
    - Spread across multiple societies
    - Reasonably recent (last 2 years)
    """
    try:
        engine = get_engine()
        with get_session(engine) as session:
            # Pull a larger candidate set, then dedupe per society in Python for variety.
            cutoff = date(date.today().year - 2, 1, 1)
            q = (
                session.query(PublicReview)
                .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
                .filter(PublicReview.review_date >= cutoff)
                .filter(
                    func.length(
                        func.coalesce(PublicReview.body_text_clean, PublicReview.body_text_raw)
                    )
                    >= 60
                )
                .filter(
                    func.length(
                        func.coalesce(PublicReview.body_text_clean, PublicReview.body_text_raw)
                    )
                    <= 260
                )
                .filter(PublicReview.rating_raw.in_([1, 2, 4, 5]))
            )
            candidates = q.order_by(func.random()).limit(limit * 10).all()

            seen_societies: set[str] = set()
            results: list[FeaturedReview] = []
            # First pass: one per society for variety
            for r in candidates:
                if r.building_society_id in seen_societies:
                    continue
                society = SOCIETY_BY_ID.get(r.building_society_id)
                if society is None:
                    continue
                quote = (r.body_text_clean or r.body_text_raw or "").strip()
                if not quote:
                    continue
                results.append(
                    FeaturedReview(
                        id=r.id,
                        quote=quote,
                        rating=r.rating_raw,
                        review_date=r.review_date,
                        society_id=r.building_society_id,
                        society_name=society.canonical_name,
                        source_id=r.source_id,
                    )
                )
                seen_societies.add(r.building_society_id)
                if len(results) >= limit:
                    break

            # Second pass: fill remaining slots if we didn't reach the limit
            if len(results) < limit:
                already_used_ids = {r.id for r in results}
                for r in candidates:
                    if r.id in already_used_ids:
                        continue
                    society = SOCIETY_BY_ID.get(r.building_society_id)
                    if society is None:
                        continue
                    quote = (r.body_text_clean or r.body_text_raw or "").strip()
                    if not quote:
                        continue
                    results.append(
                        FeaturedReview(
                            id=r.id,
                            quote=quote,
                            rating=r.rating_raw,
                            review_date=r.review_date,
                            society_id=r.building_society_id,
                            society_name=society.canonical_name,
                            source_id=r.source_id,
                        )
                    )
                    if len(results) >= limit:
                        break

            if not results:
                return FALLBACK_QUOTES[:limit]
            random.shuffle(results)
            return results
    except Exception as e:  # noqa: BLE001
        # Never break the screensaver because of a DB issue.
        print(f"featured_reviews error: {e}")
        return FALLBACK_QUOTES[:limit]


SOURCE_DISPLAY_NAMES = {
    "trustpilot": "Trustpilot",
    "app_store": "App Store",
    "play_store": "Play Store",
    "smartmoneypeople": "Smart Money People",
    "feefo": "Feefo",
    "reddit": "Reddit",
    "mse": "MoneySavingExpert",
    "google": "Google Reviews",
    "fairer_finance": "Fairer Finance",
    "which": "Which?",
}


def _infer_sentiment(rating: int) -> str:
    """Fallback sentiment label when a review has no enrichment row."""
    if rating >= 5:
        return "very_positive"
    if rating == 4:
        return "positive"
    if rating == 3:
        return "neutral"
    if rating == 2:
        return "negative"
    return "very_negative"


# Strong sentiment words that clearly contradict the rating. We only flip
# the label when the body unambiguously signals the opposite direction.
_NEGATIVE_SIGNALS = (
    "terrible", "awful", "useless", "worst", "rubbish", "appalling",
    "disgraceful", "disgusting", " avoid ", "avoid at", "avoid them",
    "scam", "horrible", "shambles", "shameful", "disaster", "diabolical",
    "hate ", "hated ", "shocking", "atrocious", "ripoff", "rip off",
)
_POSITIVE_SIGNALS = (
    "excellent", "brilliant", "fantastic", "amazing", "outstanding",
    "superb", "wonderful", "exceptional", "best bank", "best building society",
    "highly recommend", "love this", "love the", "couldn't be happier",
    "cannot fault",
)


def _apply_sentiment_override(label: str, body: str) -> str:
    """Override a clearly-wrong sentiment label when the body text disagrees.

    Keeps conservative: only flips when there's a strong keyword signal. Avoids
    turning "not terrible" into negative by requiring the raw substring - most
    false negatives of that shape are rare in the corpus.
    """
    if not body:
        return label

    body_lower = body.lower()
    has_negative = any(sig in body_lower for sig in _NEGATIVE_SIGNALS)
    has_positive = any(sig in body_lower for sig in _POSITIVE_SIGNALS)

    if label in ("positive", "very_positive") and has_negative and not has_positive:
        return "negative"
    if label in ("negative", "very_negative") and has_positive and not has_negative:
        return "positive"
    return label


@router.get("/by-society/{society_id}", response_model=list[SocietyReview])
async def reviews_by_society(society_id: str, limit: int = 300) -> list[SocietyReview]:
    """Return up to ``limit`` real reviews for a single building society.

    Used by the kiosk's evidence panel to show the full corpus (not just the
    10 snippets the vector search picks per chat turn). Orders by review_date
    desc so the most recent reviews surface first. Joins the enrichment table
    opportunistically for sentiment; reviews without enrichment fall back to
    a rating-derived label.
    """
    society = SOCIETY_BY_ID.get(society_id)
    if society is None:
        raise HTTPException(status_code=404, detail=f"Unknown society: {society_id}")

    engine = get_engine()
    try:
        with get_session(engine) as session:
            # LEFT JOIN onto SentimentAspect where aspect = 'overall' so we
            # get the enriched label when it exists, None otherwise.
            sent_subq = (
                session.query(
                    SentimentAspect.review_id,
                    SentimentAspect.overall_sentiment_label,
                )
                .filter(SentimentAspect.aspect == "overall")
                .subquery()
            )

            rows = (
                session.query(PublicReview, sent_subq.c.overall_sentiment_label)
                .outerjoin(sent_subq, sent_subq.c.review_id == PublicReview.id)
                .filter(PublicReview.building_society_id == society_id)
                .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
                .filter(
                    func.length(
                        func.coalesce(PublicReview.body_text_clean, PublicReview.body_text_raw)
                    )
                    >= 20
                )
                .order_by(desc(PublicReview.review_date))
                .limit(limit)
                .all()
            )

            results: list[SocietyReview] = []
            for row in rows:
                r: PublicReview = row[0]
                enriched_sent: Optional[str] = row[1]
                body = (r.body_text_clean or r.body_text_raw or "").strip()
                if not body:
                    continue
                sentiment = enriched_sent or _infer_sentiment(r.rating_raw)
                # Safety net: if the label (enriched OR inferred) clearly
                # contradicts strong keywords in the body, flip it. Catches
                # 5-star ratings on "terrible app" bodies that otherwise slip
                # through as "very_positive".
                sentiment = _apply_sentiment_override(sentiment, body)
                results.append(
                    SocietyReview(
                        id=r.id,
                        snippet_id=str(r.id),
                        body=body,
                        rating=r.rating_raw,
                        review_date=r.review_date,
                        society_id=r.building_society_id,
                        society_name=society.canonical_name,
                        source=SOURCE_DISPLAY_NAMES.get(r.source_id, r.source_id),
                        source_id=r.source_id,
                        sentiment_label=sentiment,
                        source_url=r.source_url,
                    )
                )
            return results
    except Exception as e:  # noqa: BLE001
        print(f"reviews_by_society error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviews")
