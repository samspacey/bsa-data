"""Compute aggregated metrics from enriched reviews."""

from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.data.models import (
    BuildingSociety,
    PublicReview,
    SentimentAspect,
    SummaryMetric,
)


class MetricsComputer:
    """Compute aggregated sentiment and rating metrics."""

    # Standard time buckets
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

    # Predefined periods
    SINCE_COVID = "since_covid"
    PRE_COVID = "pre_covid"
    LAST_12_MONTHS = "last_12_months"
    LAST_24_MONTHS = "last_24_months"

    COVID_START_DATE = date(2020, 3, 1)

    def __init__(self, session: Session, snapshot_date: Optional[date] = None):
        """Initialize the metrics computer.

        Args:
            session: Database session
            snapshot_date: Reference date for "last X months" calculations
        """
        self.session = session
        self.snapshot_date = snapshot_date or date.today()

    def get_time_buckets(
        self,
        granularity: str,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, date]]:
        """Generate time bucket ranges.

        Args:
            granularity: monthly, quarterly, or yearly
            start_date: Start of range
            end_date: End of range

        Returns:
            List of (bucket_start, bucket_end) tuples
        """
        buckets = []
        current = start_date

        while current < end_date:
            if granularity == self.MONTHLY:
                # End of month
                if current.month == 12:
                    bucket_end = date(current.year + 1, 1, 1)
                else:
                    bucket_end = date(current.year, current.month + 1, 1)
                buckets.append((date(current.year, current.month, 1), min(bucket_end, end_date)))
                current = bucket_end

            elif granularity == self.QUARTERLY:
                quarter_month = ((current.month - 1) // 3) * 3 + 1
                quarter_start = date(current.year, quarter_month, 1)
                if quarter_month + 3 > 12:
                    quarter_end = date(current.year + 1, 1, 1)
                else:
                    quarter_end = date(current.year, quarter_month + 3, 1)
                buckets.append((quarter_start, min(quarter_end, end_date)))
                current = quarter_end

            elif granularity == self.YEARLY:
                year_start = date(current.year, 1, 1)
                year_end = date(current.year + 1, 1, 1)
                buckets.append((year_start, min(year_end, end_date)))
                current = year_end

            else:
                raise ValueError(f"Unknown granularity: {granularity}")

        return buckets

    def compute_metrics_for_bucket(
        self,
        society_id: str,
        aspect: str,
        bucket_start: date,
        bucket_end: date,
        channel: Optional[str] = None,
        product: Optional[str] = None,
    ) -> Optional[dict]:
        """Compute metrics for a specific bucket.

        Args:
            society_id: Building society ID
            aspect: Aspect to compute (or "overall")
            bucket_start: Start of time bucket
            bucket_end: End of time bucket
            channel: Optional channel filter
            product: Optional product filter

        Returns:
            Dict of metrics or None if no data
        """
        # Base query
        query = (
            self.session.query(
                func.count(PublicReview.id).label("review_count"),
                func.avg(PublicReview.rating_raw).label("avg_rating"),
            )
            .filter(PublicReview.building_society_id == society_id)
            .filter(PublicReview.review_date >= bucket_start)
            .filter(PublicReview.review_date < bucket_end)
            .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
        )

        if channel:
            query = query.filter(PublicReview.channel == channel)
        if product:
            query = query.filter(PublicReview.product == product)

        result = query.first()
        if not result or result.review_count == 0:
            return None

        review_count = result.review_count
        avg_rating = float(result.avg_rating)

        # Get sentiment scores for this aspect
        sentiment_query = (
            self.session.query(
                func.avg(SentimentAspect.aspect_sentiment_score).label("avg_sentiment"),
                func.count(SentimentAspect.id).label("sentiment_count"),
            )
            .join(PublicReview)
            .filter(PublicReview.building_society_id == society_id)
            .filter(PublicReview.review_date >= bucket_start)
            .filter(PublicReview.review_date < bucket_end)
            .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
            .filter(SentimentAspect.aspect == aspect)
        )

        if channel:
            sentiment_query = sentiment_query.filter(PublicReview.channel == channel)
        if product:
            sentiment_query = sentiment_query.filter(PublicReview.product == product)

        sentiment_result = sentiment_query.first()

        avg_sentiment = 0.0
        if sentiment_result and sentiment_result.avg_sentiment is not None:
            avg_sentiment = float(sentiment_result.avg_sentiment)

        # Count positive and negative reviews
        positive_count = (
            self.session.query(func.count(SentimentAspect.id))
            .join(PublicReview)
            .filter(PublicReview.building_society_id == society_id)
            .filter(PublicReview.review_date >= bucket_start)
            .filter(PublicReview.review_date < bucket_end)
            .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
            .filter(SentimentAspect.aspect == aspect)
            .filter(SentimentAspect.aspect_sentiment_label.in_(["positive", "very_positive"]))
            .scalar()
        ) or 0

        negative_count = (
            self.session.query(func.count(SentimentAspect.id))
            .join(PublicReview)
            .filter(PublicReview.building_society_id == society_id)
            .filter(PublicReview.review_date >= bucket_start)
            .filter(PublicReview.review_date < bucket_end)
            .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
            .filter(SentimentAspect.aspect == aspect)
            .filter(SentimentAspect.aspect_sentiment_label.in_(["negative", "very_negative"]))
            .scalar()
        ) or 0

        pct_positive = positive_count / review_count if review_count > 0 else 0
        pct_negative = negative_count / review_count if review_count > 0 else 0
        net_sentiment = pct_positive - pct_negative

        return {
            "review_count": review_count,
            "avg_rating": avg_rating,
            "avg_sentiment_score": avg_sentiment,
            "pct_positive_reviews": pct_positive,
            "pct_negative_reviews": pct_negative,
            "net_sentiment_score": net_sentiment,
        }

    def compute_peer_average(
        self,
        aspect: str,
        bucket_start: date,
        bucket_end: date,
        exclude_society_id: Optional[str] = None,
    ) -> tuple[Optional[float], Optional[int]]:
        """Compute peer group average sentiment.

        Args:
            aspect: Aspect to compute
            bucket_start: Start of time bucket
            bucket_end: End of time bucket
            exclude_society_id: Society to exclude from peer group

        Returns:
            Tuple of (avg_sentiment, review_count)
        """
        query = (
            self.session.query(
                func.avg(SentimentAspect.aspect_sentiment_score).label("avg_sentiment"),
                func.count(SentimentAspect.id).label("review_count"),
            )
            .join(PublicReview)
            .filter(PublicReview.review_date >= bucket_start)
            .filter(PublicReview.review_date < bucket_end)
            .filter(PublicReview.is_flagged_for_exclusion == False)  # noqa: E712
            .filter(SentimentAspect.aspect == aspect)
        )

        if exclude_society_id:
            query = query.filter(PublicReview.building_society_id != exclude_society_id)

        result = query.first()

        if result and result.avg_sentiment is not None:
            return float(result.avg_sentiment), result.review_count
        return None, None

    def compute_all_metrics(
        self,
        granularity: str = MONTHLY,
        aspects: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        metric_version: str = "v1",
    ) -> list[SummaryMetric]:
        """Compute metrics for all societies and aspects.

        Args:
            granularity: Time bucket granularity
            aspects: List of aspects to compute (default: overall + standard aspects)
            start_date: Start of range
            end_date: End of range
            metric_version: Version string for tracking

        Returns:
            List of SummaryMetric objects
        """
        if aspects is None:
            aspects = [
                "overall",
                "digital_banking",
                "mobile_app",
                "branches",
                "mortgages",
                "savings",
                "customer_service",
            ]

        # Get date range from data if not specified
        if not start_date or not end_date:
            date_range = self.session.query(
                func.min(PublicReview.review_date),
                func.max(PublicReview.review_date),
            ).first()
            start_date = start_date or date_range[0]
            end_date = end_date or date_range[1]

        if not start_date or not end_date:
            return []

        # Get all societies
        societies = self.session.query(BuildingSociety).all()

        # Generate time buckets
        buckets = self.get_time_buckets(granularity, start_date, end_date)

        metrics = []

        for society in societies:
            for bucket_start, bucket_end in buckets:
                for aspect in aspects:
                    # Compute metrics for this combination
                    data = self.compute_metrics_for_bucket(
                        society.id, aspect, bucket_start, bucket_end
                    )

                    if not data:
                        continue

                    # Compute peer average
                    peer_avg, peer_count = self.compute_peer_average(
                        aspect, bucket_start, bucket_end, society.id
                    )

                    metric = SummaryMetric(
                        building_society_id=society.id,
                        time_bucket_start=bucket_start,
                        time_bucket_end=bucket_end,
                        aspect=aspect,
                        review_count=data["review_count"],
                        avg_rating=data["avg_rating"],
                        avg_sentiment_score=data["avg_sentiment_score"],
                        pct_positive_reviews=data["pct_positive_reviews"],
                        pct_negative_reviews=data["pct_negative_reviews"],
                        net_sentiment_score=data["net_sentiment_score"],
                        peer_group_avg_sentiment_score=peer_avg,
                        peer_group_review_count=peer_count,
                        metric_version=metric_version,
                    )
                    metrics.append(metric)

        return metrics
