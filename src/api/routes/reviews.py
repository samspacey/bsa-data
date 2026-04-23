"""Reviews endpoints — featured reviews for screensaver etc."""

import random
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from src.config.societies import SOCIETY_BY_ID
from src.data.database import get_engine, get_session
from src.data.models import PublicReview


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
    - Rating is extreme (1-2 or 4-5) — more quotable than 3-star 'meh'
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
