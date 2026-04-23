#!/usr/bin/env python3
"""Script to clean and normalize scraped review data."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.config.societies import get_all_societies
from src.data.database import get_session, init_database, populate_initial_data, get_engine
from src.data.models import ContentMention, PublicReview
from src.data.schemas import RawMention, RawReview
from src.processing.cleaner import ReviewCleaner


# Sources that emit RawReview (aggregated into summary_metric)
REVIEW_SOURCES = [
    "trustpilot",
    "app_store",
    "play_store",
    "smartmoneypeople",
    "feefo",
    "google",
]

# Sources that emit RawMention (stored but NOT aggregated into summary_metric)
MENTION_SOURCES = [
    "reddit",
    "mse",
    "fairer_finance",
    "which",
]


def load_raw_reviews(source_dir: Path, source_id: str) -> list[RawReview]:
    """Load raw reviews from JSON files."""
    source_path = source_dir / source_id
    if not source_path.exists():
        print(f"  No data directory for {source_id}")
        return []

    reviews = []
    for json_file in source_path.glob("*.json"):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        for review_data in data.get("reviews", []):
            try:
                if isinstance(review_data.get("review_date"), str):
                    review_data["review_date"] = datetime.fromisoformat(
                        review_data["review_date"]
                    ).date()
                reviews.append(RawReview(**review_data))
            except Exception as e:
                print(f"  Error parsing review: {e}")
                continue

    return reviews


def load_raw_mentions(source_dir: Path, source_id: str) -> list[RawMention]:
    """Load raw mentions from JSON files (reddit, mse, fairer_finance, which)."""
    source_path = source_dir / source_id
    if not source_path.exists():
        print(f"  No data directory for {source_id}")
        return []

    mentions = []
    for json_file in source_path.glob("*.json"):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("reviews", []):  # base scraper saves under 'reviews' key
            try:
                if isinstance(item.get("mention_date"), str):
                    item["mention_date"] = datetime.fromisoformat(item["mention_date"]).date()
                mentions.append(RawMention(**item))
            except Exception as e:
                print(f"  Error parsing mention: {e}")
                continue

    return mentions


def main():
    parser = argparse.ArgumentParser(description="Clean and normalize scraped review data")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=settings.raw_data_dir,
        help=f"Input directory with raw data (default: {settings.raw_data_dir})",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=REVIEW_SOURCES + MENTION_SOURCES + ["all"],
        default=["all"],
        help="Sources to process (default: all)",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset the database before loading",
    )

    args = parser.parse_args()

    # Initialize database
    print("Initializing database...")
    engine = get_engine()
    init_database(engine)
    populate_initial_data(engine)

    # Initialize cleaner
    cleaner = ReviewCleaner()

    # Determine sources to process
    if "all" in args.sources:
        review_sources = REVIEW_SOURCES
        mention_sources = MENTION_SOURCES
    else:
        review_sources = [s for s in args.sources if s in REVIEW_SOURCES]
        mention_sources = [s for s in args.sources if s in MENTION_SOURCES]

    total_raw = 0
    total_cleaned = 0
    total_excluded = 0
    total_mentions = 0

    # --- Reviews flow ---
    for source_id in review_sources:
        print(f"\nProcessing {source_id} (reviews)...")

        raw_reviews = load_raw_reviews(args.input_dir, source_id)
        print(f"  Loaded {len(raw_reviews)} raw reviews")
        total_raw += len(raw_reviews)

        if not raw_reviews:
            continue

        cleaned_reviews = cleaner.clean_reviews(raw_reviews)
        valid_reviews = [r for r in cleaned_reviews if not r.is_flagged_for_exclusion]
        excluded_reviews = [r for r in cleaned_reviews if r.is_flagged_for_exclusion]

        print(f"  Valid reviews: {len(valid_reviews)}")
        print(f"  Excluded reviews: {len(excluded_reviews)}")

        total_cleaned += len(valid_reviews)
        total_excluded += len(excluded_reviews)

        # Build a lookup from raw source_review_id -> source_url so cleaned reviews
        # can carry the link through to the DB (cleaner doesn't currently propagate it).
        url_lookup = {r.source_review_id: r.source_url for r in raw_reviews if r.source_url}

        print("  Saving to database...")
        with get_session(engine) as session:
            for cleaned in cleaned_reviews:
                existing = (
                    session.query(PublicReview)
                    .filter_by(
                        source_id=cleaned.source_id,
                        source_review_id=cleaned.source_review_id,
                    )
                    .first()
                )

                if existing:
                    continue

                review = PublicReview(
                    source_id=cleaned.source_id,
                    source_review_id=cleaned.source_review_id,
                    building_society_id=cleaned.building_society_id,
                    review_date=cleaned.review_date,
                    rating_raw=cleaned.rating_raw,
                    rating_normalised=cleaned.rating_normalised,
                    title_text=cleaned.title_text,
                    body_text_raw=cleaned.body_text_raw,
                    body_text_clean=cleaned.body_text_clean,
                    reviewer_language=cleaned.reviewer_language,
                    channel=cleaned.channel.value if cleaned.channel else None,
                    product=cleaned.product.value if cleaned.product else None,
                    location_text=cleaned.location_text,
                    app_version=cleaned.app_version,
                    source_url=url_lookup.get(cleaned.source_review_id),
                    is_flagged_for_exclusion=cleaned.is_flagged_for_exclusion,
                    exclusion_reason=cleaned.exclusion_reason,
                    cleaned_at=datetime.now(),
                )
                session.add(review)

            session.commit()

    # --- Mentions flow ---
    for source_id in mention_sources:
        print(f"\nProcessing {source_id} (mentions)...")

        raw_mentions = load_raw_mentions(args.input_dir, source_id)
        print(f"  Loaded {len(raw_mentions)} mentions")
        total_mentions += len(raw_mentions)

        if not raw_mentions:
            continue

        with get_session(engine) as session:
            for m in raw_mentions:
                existing = (
                    session.query(ContentMention)
                    .filter_by(source_id=m.source_id, source_mention_id=m.source_mention_id)
                    .first()
                )
                if existing:
                    continue

                # Minimal cleaning: trim & drop very short bodies. PII redaction
                # is reused from ReviewCleaner for consistency where it applies.
                body_clean = cleaner.normalize_text(cleaner.remove_pii(m.body or ""))

                session.add(
                    ContentMention(
                        source_id=m.source_id,
                        source_mention_id=m.source_mention_id,
                        building_society_id=m.building_society_id,
                        mention_type=m.mention_type.value if hasattr(m.mention_type, "value") else str(m.mention_type),
                        mention_date=m.mention_date,
                        title_text=m.title,
                        body_text_raw=m.body,
                        body_text_clean=body_clean,
                        author_handle=m.author,
                        source_url=m.source_url,
                        rating_value=m.rating_value,
                        rating_scale_max=m.rating_scale_max,
                        extra_metadata=json.dumps(m.extra) if m.extra else None,
                        cleaned_at=datetime.now(),
                    )
                )

            session.commit()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total raw reviews: {total_raw}")
    print(f"Total valid reviews: {total_cleaned}")
    print(f"Total excluded reviews: {total_excluded}")
    print(f"Total mentions stored: {total_mentions}")
    print(f"Database: {settings.sqlite_db_path}")


if __name__ == "__main__":
    main()
