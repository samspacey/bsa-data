#!/usr/bin/env python3
"""Script to generate embeddings and build the vector index."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.config.settings import settings
from src.data.database import get_engine, get_session
from src.data.models import EmbeddingDocument, PublicReview, SentimentAspect, TopicTag
from src.embeddings.generator import EmbeddingGenerator
from src.embeddings.index import ReviewDocument, VectorIndex


def prepare_text_for_embedding(review: PublicReview) -> str:
    """Prepare review text for embedding.

    Args:
        review: Public review record

    Returns:
        Text suitable for embedding
    """
    parts = []

    # Add title if present
    if review.title_text:
        parts.append(review.title_text)

    # Add body text (prefer cleaned version)
    body = review.body_text_clean or review.body_text_raw
    parts.append(body)

    # Combine and truncate
    text = ". ".join(parts)
    return text[:2000]  # Truncate for embedding


async def process_batch(
    reviews: list[PublicReview],
    generator: EmbeddingGenerator,
    index: VectorIndex,
    session,
) -> int:
    """Process a batch of reviews.

    Args:
        reviews: Reviews to process
        generator: Embedding generator
        index: Vector index
        session: Database session

    Returns:
        Number processed
    """
    # Prepare texts
    texts = [prepare_text_for_embedding(r) for r in reviews]

    # Generate embeddings
    embeddings = await generator.embed_texts(texts, show_progress=False)

    # Create documents for index
    documents = []
    for review, embedding in zip(reviews, embeddings):
        # Get sentiment info
        sentiment = (
            session.query(SentimentAspect)
            .filter(SentimentAspect.review_id == review.id)
            .filter(SentimentAspect.aspect == "overall")
            .first()
        )

        # Get topics
        topics = session.query(TopicTag).filter(TopicTag.review_id == review.id).all()

        # Get aspects
        aspects = (
            session.query(SentimentAspect.aspect)
            .filter(SentimentAspect.review_id == review.id)
            .filter(SentimentAspect.aspect != "overall")
            .distinct()
            .all()
        )

        doc = ReviewDocument(
            id=review.id,
            review_id=review.id,
            building_society_id=review.building_society_id,
            source_id=review.source_id,
            review_date=review.review_date.isoformat(),
            rating=review.rating_raw,
            sentiment_label=sentiment.overall_sentiment_label if sentiment else "neutral",
            aspects=json.dumps([a[0] for a in aspects]),
            topics=json.dumps([t.topic_key for t in topics]),
            text=prepare_text_for_embedding(review),
            vector=embedding,
        )
        documents.append(doc)

        # Also record in SQLite for reference
        embedding_doc = EmbeddingDocument(
            doc_type="review",
            source_review_id=review.id,
            building_society_id=review.building_society_id,
            review_date=review.review_date,
            aspects=json.dumps([a[0] for a in aspects]),
            topics=json.dumps([t.topic_key for t in topics]),
            sentiment_label=sentiment.overall_sentiment_label if sentiment else None,
            text_for_embedding=prepare_text_for_embedding(review),
            vector_id=str(review.id),
            embedding_model=settings.openai_embedding_model,
        )
        session.add(embedding_doc)

    # Add to vector index
    index.add_documents(documents)
    session.commit()

    return len(documents)


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings and build vector index")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of reviews to process",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing index before building",
    )

    args = parser.parse_args()

    engine = get_engine()
    index = VectorIndex()

    if args.clear:
        print("Clearing existing index...")
        index.clear()

    # Query review IDs that have been enriched
    with get_session(engine) as session:
        query = session.query(PublicReview.id).filter(
            PublicReview.enriched_at != None,  # noqa: E711
            PublicReview.is_flagged_for_exclusion == False,  # noqa: E712
        )

        if args.limit:
            query = query.limit(args.limit)

        review_ids = [r[0] for r in query.all()]

    print(f"Found {len(review_ids)} reviews to embed")

    if not review_ids:
        print("No reviews to process")
        return

    # Initialize generator
    generator = EmbeddingGenerator()

    # Process in batches
    total_processed = 0
    for i in tqdm(range(0, len(review_ids), args.batch_size), desc="Processing batches"):
        batch_ids = review_ids[i : i + args.batch_size]

        with get_session(engine) as session:
            batch_reviews = (
                session.query(PublicReview)
                .filter(PublicReview.id.in_(batch_ids))
                .all()
            )

            count = asyncio.run(
                process_batch(batch_reviews, generator, index, session)
            )
            total_processed += count

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total documents: {total_processed}")
    print(f"Index location: {settings.lancedb_path}")
    print(f"Tokens used: {generator.total_tokens:,}")
    print(f"Estimated cost: ${generator.estimated_cost:.4f}")


if __name__ == "__main__":
    main()
