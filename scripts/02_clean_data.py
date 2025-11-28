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
from src.data.models import PublicReview
from src.data.schemas import RawReview
from src.processing.cleaner import ReviewCleaner


def load_raw_reviews(source_dir: Path, source_id: str) -> list[RawReview]:
    """Load raw reviews from JSON files.

    Args:
        source_dir: Directory containing raw review files
        source_id: Source identifier (trustpilot, app_store, play_store)

    Returns:
        List of raw reviews
    """
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
                # Convert date string back to date object
                if isinstance(review_data.get("review_date"), str):
                    review_data["review_date"] = datetime.fromisoformat(
                        review_data["review_date"]
                    ).date()
                reviews.append(RawReview(**review_data))
            except Exception as e:
                print(f"  Error parsing review: {e}")
                continue

    return reviews


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
        choices=["trustpilot", "app_store", "play_store", "all"],
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
    sources = (
        ["trustpilot", "app_store", "play_store"]
        if "all" in args.sources
        else args.sources
    )

    total_raw = 0
    total_cleaned = 0
    total_excluded = 0

    for source_id in sources:
        print(f"\nProcessing {source_id}...")

        # Load raw reviews
        raw_reviews = load_raw_reviews(args.input_dir, source_id)
        print(f"  Loaded {len(raw_reviews)} raw reviews")
        total_raw += len(raw_reviews)

        if not raw_reviews:
            continue

        # Clean reviews
        cleaned_reviews = cleaner.clean_reviews(raw_reviews)

        # Separate valid and excluded
        valid_reviews = [r for r in cleaned_reviews if not r.is_flagged_for_exclusion]
        excluded_reviews = [r for r in cleaned_reviews if r.is_flagged_for_exclusion]

        print(f"  Valid reviews: {len(valid_reviews)}")
        print(f"  Excluded reviews: {len(excluded_reviews)}")

        total_cleaned += len(valid_reviews)
        total_excluded += len(excluded_reviews)

        # Save to database
        print("  Saving to database...")
        with get_session(engine) as session:
            for cleaned in cleaned_reviews:
                # Check for duplicates
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
                    is_flagged_for_exclusion=cleaned.is_flagged_for_exclusion,
                    exclusion_reason=cleaned.exclusion_reason,
                    cleaned_at=datetime.now(),
                )
                session.add(review)

            session.commit()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total raw reviews: {total_raw}")
    print(f"Total valid reviews: {total_cleaned}")
    print(f"Total excluded: {total_excluded}")
    print(f"Database: {settings.sqlite_db_path}")


if __name__ == "__main__":
    main()
