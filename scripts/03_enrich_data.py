#!/usr/bin/env python3
"""Script to enrich reviews with LLM-based sentiment and topic analysis."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.config.settings import settings
from src.data.database import get_engine, get_session
from src.data.models import PublicReview, SentimentAspect, TopicTag
from src.processing.enrichment import ReviewEnricher


async def process_reviews_from_data(
    enricher: ReviewEnricher,
    review_data: list,  # List of (id, society_id, rating, title, body) tuples
    batch_size: int,
    engine,
) -> tuple:
    """Process reviews in batches.

    Args:
        enricher: The review enricher
        review_data: List of (id, society_id, rating, title, body) tuples
        batch_size: Size of each batch
        engine: Database engine

    Returns:
        Tuple of (successful, failed) counts
    """
    successful = 0
    failed = 0

    # Process in batches
    for i in tqdm(range(0, len(review_data), batch_size), desc="Enriching"):
        batch = review_data[i : i + batch_size]

        # Prepare batch data for enricher (id, rating, title, body)
        batch_for_enricher = [
            (r_id, rating, title, body)
            for r_id, _, rating, title, body in batch
        ]

        # Enrich batch
        results = await enricher.enrich_batch(batch_for_enricher)

        # Save results to database
        with get_session(engine) as session:
            for review_tuple, result in zip(batch, results):
                review_id = review_tuple[0]  # (id, society_id, rating, title, body)

                if result is None:
                    failed += 1
                    continue

                successful += 1

                # Save overall sentiment as an aspect
                session.add(
                    SentimentAspect(
                        review_id=review_id,
                        overall_sentiment_label=result.overall_sentiment.value,
                        overall_sentiment_score=result.overall_sentiment_score,
                        aspect="overall",
                        aspect_sentiment_label=result.overall_sentiment.value,
                        aspect_sentiment_score=result.overall_sentiment_score,
                        emotion=result.emotion.value if result.emotion else None,
                        model_version=settings.openai_model,
                    )
                )

                # Save aspect-specific sentiments
                for asp in result.aspect_sentiments:
                    session.add(
                        SentimentAspect(
                            review_id=review_id,
                            overall_sentiment_label=result.overall_sentiment.value,
                            overall_sentiment_score=result.overall_sentiment_score,
                            aspect=asp.aspect,
                            aspect_sentiment_label=asp.sentiment_label.value,
                            aspect_sentiment_score=asp.sentiment_score,
                            model_version=settings.openai_model,
                        )
                    )

                # Save topics
                for topic in result.topics:
                    # Determine topic group
                    topic_lower = topic.lower().replace(" ", "_")
                    if any(
                        kw in topic_lower
                        for kw in ["app", "login", "website", "online", "digital"]
                    ):
                        group = "digital"
                    elif any(kw in topic_lower for kw in ["mortgage", "lending", "loan"]):
                        group = "mortgages"
                    elif any(kw in topic_lower for kw in ["branch", "staff", "visit"]):
                        group = "branches"
                    elif any(
                        kw in topic_lower
                        for kw in ["service", "support", "help", "response"]
                    ):
                        group = "service"
                    else:
                        group = "general"

                    session.add(
                        TopicTag(
                            review_id=review_id,
                            topic_key=topic_lower,
                            topic_group=group,
                            topic_label=topic,
                            relevance_score=1.0,
                            model_version=settings.openai_model,
                        )
                    )

                # Update the review record with enrichment timestamp and inferred fields
                review_record = session.query(PublicReview).filter(PublicReview.id == review_id).first()
                if review_record:
                    if result.channel and not review_record.channel:
                        review_record.channel = result.channel.value
                    if result.product and not review_record.product:
                        review_record.product = result.product.value
                    review_record.enriched_at = datetime.now()

            session.commit()

        # Print progress
        print(
            f"  Batch complete. Success: {successful}, Failed: {failed}, "
            f"Cost: ${enricher.total_cost:.2f}"
        )

    return successful, failed


def main():
    parser = argparse.ArgumentParser(description="Enrich reviews with LLM analysis")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.batch_size,
        help=f"Batch size for processing (default: {settings.batch_size})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of reviews to process (default: all)",
    )
    parser.add_argument(
        "--society",
        type=str,
        default=None,
        help="Process only reviews for a specific society ID",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process already enriched reviews",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making API calls",
    )

    args = parser.parse_args()

    # Get database engine
    engine = get_engine()

    # Query reviews to process
    with get_session(engine) as session:
        query = session.query(PublicReview).filter(
            PublicReview.is_flagged_for_exclusion == False  # noqa: E712
        )

        if not args.force:
            query = query.filter(PublicReview.enriched_at == None)  # noqa: E711

        if args.society:
            query = query.filter(PublicReview.building_society_id == args.society)

        if args.limit:
            query = query.limit(args.limit)

        reviews = query.all()

        # Extract data we need while still in session
        review_data = [
            (r.id, r.building_society_id, r.rating_raw, r.title_text, r.body_text_clean or r.body_text_raw)
            for r in reviews
        ]

    print(f"Found {len(review_data)} reviews to process")

    if not review_data:
        print("No reviews to process")
        return

    if args.dry_run:
        print("Dry run - no API calls will be made")
        for r_id, society_id, rating, _, _ in review_data[:10]:
            print(f"  - {r_id}: {society_id} ({rating}/5)")
        if len(review_data) > 10:
            print(f"  ... and {len(review_data) - 10} more")
        return

    # Initialize enricher
    enricher = ReviewEnricher()

    # Process reviews
    print(f"\nProcessing {len(review_data)} reviews...")
    print(f"Batch size: {args.batch_size}")
    print(f"Max concurrent requests: {settings.max_concurrent_requests}")
    print()

    successful, failed = asyncio.run(
        process_reviews_from_data(enricher, review_data, args.batch_size, engine)
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total processed: {len(review_data)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Estimated cost: ${enricher.total_cost:.2f}")


if __name__ == "__main__":
    main()
