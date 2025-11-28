"""Retrieval service for metrics and evidence."""

import json
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.config.societies import SOCIETY_BY_ID
from src.data.models import (
    BuildingSociety,
    DataSource,
    PublicReview,
    SentimentAspect,
    SummaryMetric,
    TopicTag,
)
from src.data.schemas import (
    DataCoverage,
    MetricSummary,
    QueryIntent,
    ReviewSnippet,
    SentimentLabel,
)
from src.embeddings.generator import EmbeddingGenerator
from src.embeddings.index import VectorIndex


class RetrievalService:
    """Retrieve metrics and evidence for query answering."""

    def __init__(
        self,
        session: Session,
        vector_index: Optional[VectorIndex] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        """Initialize the retrieval service.

        Args:
            session: Database session
            vector_index: Vector index for semantic search
            embedding_generator: For generating query embeddings
        """
        self.session = session
        self.vector_index = vector_index or VectorIndex()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()

    def get_metrics(
        self,
        intent: QueryIntent,
    ) -> list[MetricSummary]:
        """Get aggregated metrics for the query intent.

        Args:
            intent: Parsed query intent

        Returns:
            List of metric summaries
        """
        # Get all relevant society IDs
        society_ids = intent.primary_building_societies + intent.comparison_building_societies

        if not society_ids:
            # Default to all societies
            society_ids = [s.id for s in self.session.query(BuildingSociety).all()]

        # Get aspects
        aspects = intent.focus_areas if intent.focus_areas else ["overall"]

        # Query metrics
        query = self.session.query(SummaryMetric).filter(
            SummaryMetric.building_society_id.in_(society_ids),
            SummaryMetric.aspect.in_(aspects),
        )

        # Apply time filter
        if intent.timeframe_start:
            query = query.filter(SummaryMetric.time_bucket_start >= intent.timeframe_start)
        if intent.timeframe_end:
            query = query.filter(SummaryMetric.time_bucket_end <= intent.timeframe_end)

        metrics = query.all()

        # Convert to summary format
        results = []
        for m in metrics:
            society = SOCIETY_BY_ID.get(m.building_society_id)
            results.append(
                MetricSummary(
                    building_society_id=m.building_society_id,
                    building_society_name=society.canonical_name if society else m.building_society_id,
                    time_bucket_start=m.time_bucket_start,
                    time_bucket_end=m.time_bucket_end,
                    aspect=m.aspect,
                    review_count=m.review_count,
                    avg_rating=m.avg_rating,
                    avg_sentiment_score=m.avg_sentiment_score,
                    pct_negative_reviews=m.pct_negative_reviews,
                    pct_positive_reviews=m.pct_positive_reviews,
                    net_sentiment_score=m.net_sentiment_score,
                    peer_group_avg_sentiment_score=m.peer_group_avg_sentiment_score,
                    peer_group_review_count=m.peer_group_review_count,
                )
            )

        return results

    async def get_evidence_snippets(
        self,
        intent: QueryIntent,
        limit: int = 10,
    ) -> list[ReviewSnippet]:
        """Get evidence snippets using semantic search.

        Args:
            intent: Parsed query intent
            limit: Maximum snippets to return

        Returns:
            List of review snippets
        """
        # Build query text for embedding
        query_parts = []

        for society_id in intent.primary_building_societies:
            society = SOCIETY_BY_ID.get(society_id)
            if society:
                query_parts.append(society.canonical_name)

        query_parts.extend(intent.focus_areas)

        if intent.sentiment_focus == "mostly_negative":
            query_parts.append("complaints problems issues negative")
        elif intent.sentiment_focus == "mostly_positive":
            query_parts.append("excellent satisfied happy positive")

        query_text = " ".join(query_parts)

        # Generate query embedding (async)
        embeddings = await self.embedding_generator.embed_texts([query_text], show_progress=False)
        query_vector = embeddings[0]

        # Determine sentiment filter
        sentiment_labels = None
        if intent.sentiment_focus == "mostly_negative":
            sentiment_labels = ["very_negative", "negative"]
        elif intent.sentiment_focus == "mostly_positive":
            sentiment_labels = ["positive", "very_positive"]

        # Search vector index
        society_ids = intent.primary_building_societies + intent.comparison_building_societies
        results = self.vector_index.search(
            query_vector=query_vector,
            limit=limit * 2,  # Get more to allow for filtering
            building_society_ids=society_ids if society_ids else None,
            start_date=intent.timeframe_start,
            end_date=intent.timeframe_end,
            sentiment_labels=sentiment_labels,
            aspects=intent.focus_areas if intent.focus_areas else None,
        )

        # Convert to snippets
        snippets = []
        for result in results[:limit]:
            society = SOCIETY_BY_ID.get(result["building_society_id"])

            # Get source name
            source = self.session.query(DataSource).filter(
                DataSource.id == result["source_id"]
            ).first()
            source_name = source.name if source else result["source_id"]

            # Parse sentiment label
            try:
                sentiment = SentimentLabel(result["sentiment_label"])
            except ValueError:
                sentiment = SentimentLabel.NEUTRAL

            # Truncate text for snippet
            text = result["text"]
            if len(text) > 300:
                text = text[:297] + "..."

            snippets.append(
                ReviewSnippet(
                    snippet_id=str(result["id"]),
                    building_society_id=result["building_society_id"],
                    building_society_name=society.canonical_name if society else result["building_society_id"],
                    source=source_name,
                    review_date=date.fromisoformat(result["review_date"]),
                    rating=result["rating"],
                    sentiment_label=sentiment,
                    aspects=json.loads(result["aspects"]) if result["aspects"] else [],
                    topics=json.loads(result["topics"]) if result["topics"] else [],
                    snippet_text=text,
                )
            )

        return snippets

    def get_data_coverage(
        self,
        intent: QueryIntent,
    ) -> DataCoverage:
        """Get data coverage information.

        Args:
            intent: Query intent

        Returns:
            Data coverage summary
        """
        society_ids = intent.primary_building_societies + intent.comparison_building_societies

        # Get snapshot end date
        max_date = self.session.query(func.max(PublicReview.review_date)).scalar()

        # Get sources used
        sources = self.session.query(DataSource.name).distinct().all()
        source_names = [s[0] for s in sources]

        # Count reviews per society
        per_society = []
        for society_id in society_ids:
            count = (
                self.session.query(func.count(PublicReview.id))
                .filter(PublicReview.building_society_id == society_id)
                .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
                .scalar()
            ) or 0
            society = SOCIETY_BY_ID.get(society_id)
            per_society.append({
                "building_society_id": society_id,
                "building_society_name": society.canonical_name if society else society_id,
                "review_count": count,
            })

        total = sum(s["review_count"] for s in per_society)

        return DataCoverage(
            snapshot_end_date=max_date or date.today(),
            sources=source_names,
            total_reviews_considered=total,
            per_society_review_counts=per_society,
        )
