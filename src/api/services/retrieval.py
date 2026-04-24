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
    ContentMention,
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
    SourceCount,
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
        exclude_review_ids: Optional[set[int]] = None,
    ) -> list[ReviewSnippet]:
        """Get evidence snippets using semantic search.

        Requires an OpenAI key (embeddings provider). If the key is missing or
        the embedding call fails, returns an empty list so the rest of the
        chat flow (metrics + coverage) still completes.

        ``exclude_review_ids`` removes previously-cited reviews from the
        result so successive turns surface fresh material.
        """
        # Short-circuit if OpenAI key is absent - evidence retrieval depends
        # on OpenAI embeddings regardless of which LLM drives the chat answer.
        if not settings.openai_api_key:
            return []

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

        # Generate query embedding (async). On any OpenAI failure, degrade
        # gracefully - the rest of the chat flow (metrics + coverage) is not
        # blocked by missing evidence snippets.
        try:
            embeddings = await self.embedding_generator.embed_texts(
                [query_text], show_progress=False
            )
            query_vector = embeddings[0]
        except Exception as e:  # noqa: BLE001 - scraper/embedding provider is external
            print(f"Embedding call failed ({type(e).__name__}): {e}")
            return []

        # Determine sentiment filter
        sentiment_labels = None
        if intent.sentiment_focus == "mostly_negative":
            sentiment_labels = ["very_negative", "negative"]
        elif intent.sentiment_focus == "mostly_positive":
            sentiment_labels = ["positive", "very_positive"]

        # Search vector index. Widen the pool so we have room to drop
        # already-cited reviews without running out of top matches.
        society_ids = intent.primary_building_societies + intent.comparison_building_societies
        search_cap = max(limit * 4, (limit * 2) + len(exclude_review_ids or set()))
        results = self.vector_index.search(
            query_vector=query_vector,
            limit=search_cap,
            building_society_ids=society_ids if society_ids else None,
            start_date=intent.timeframe_start,
            end_date=intent.timeframe_end,
            sentiment_labels=sentiment_labels,
            aspects=intent.focus_areas if intent.focus_areas else None,
        )

        # Drop already-cited reviews so consecutive turns get fresh material.
        if exclude_review_ids:
            results = [r for r in results if r.get("id") not in exclude_review_ids]
        # Truncate after filtering.
        results = results[:limit]

        # Bulk-lookup source_urls for the retrieved review IDs in one query
        review_ids = [result.get("id") for result in results[:limit] if result.get("id") is not None]
        url_by_review_id: dict[int, str] = {}
        if review_ids:
            try:
                rows = (
                    self.session.query(PublicReview.id, PublicReview.source_url)
                    .filter(PublicReview.id.in_(review_ids))
                    .all()
                )
                url_by_review_id = {rid: url for rid, url in rows if url}
            except Exception:  # noqa: BLE001
                url_by_review_id = {}

        # Convert to snippets
        snippets = []
        for result in results[:limit]:
            society = SOCIETY_BY_ID.get(result["building_society_id"])

            source = self.session.query(DataSource).filter(
                DataSource.id == result["source_id"]
            ).first()
            source_name = source.name if source else result["source_id"]

            try:
                sentiment = SentimentLabel(result["sentiment_label"])
            except ValueError:
                sentiment = SentimentLabel.NEUTRAL

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
                    source_url=url_by_review_id.get(result.get("id")),
                )
            )

        return snippets

    def get_data_coverage(
        self,
        intent: QueryIntent,
    ) -> DataCoverage:
        """Get data coverage information, including per-source breakdown."""
        society_ids = intent.primary_building_societies + intent.comparison_building_societies

        max_date = self.session.query(func.max(PublicReview.review_date)).scalar()

        sources = self.session.query(DataSource).all()
        source_name_by_id = {s.id: s.name for s in sources}
        source_names = list(source_name_by_id.values())

        # Count reviews per society (for the primary societies in scope).
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

        # Per-source breakdown - reviews (filtered to scoped societies if given)
        per_source_counts: list[SourceCount] = []
        reviews_by_source = self.session.query(
            PublicReview.source_id, func.count(PublicReview.id)
        )
        if society_ids:
            reviews_by_source = reviews_by_source.filter(
                PublicReview.building_society_id.in_(society_ids)
            )
        reviews_by_source = (
            reviews_by_source.filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
            .group_by(PublicReview.source_id)
            .all()
        )
        for source_id, count in reviews_by_source:
            per_source_counts.append(
                SourceCount(
                    source_id=source_id,
                    source_name=source_name_by_id.get(source_id, source_id),
                    count=count,
                )
            )

        # Content mentions (forum + editorial) - surfaced separately so the UI
        # can show them as a distinct band in the coverage chart.
        mentions_by_source_query = self.session.query(
            ContentMention.source_id, func.count(ContentMention.id)
        )
        if society_ids:
            mentions_by_source_query = mentions_by_source_query.filter(
                ContentMention.building_society_id.in_(society_ids)
            )
        mentions_by_source = mentions_by_source_query.group_by(ContentMention.source_id).all()

        mentions_total = 0
        for source_id, count in mentions_by_source:
            per_source_counts.append(
                SourceCount(
                    source_id=source_id,
                    source_name=source_name_by_id.get(source_id, source_id),
                    count=count,
                )
            )
            mentions_total += count

        # Sort descending by count for a clean chart render
        per_source_counts.sort(key=lambda s: s.count, reverse=True)

        return DataCoverage(
            snapshot_end_date=max_date or date.today(),
            sources=source_names,
            total_reviews_considered=total,
            per_society_review_counts=per_society,
            per_source_counts=per_source_counts,
            includes_mentions=mentions_total > 0,
            mentions_considered=mentions_total,
        )
