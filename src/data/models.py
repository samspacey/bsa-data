"""SQLAlchemy ORM models for the BSA Voice of Customer database."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class BuildingSociety(Base):
    """Canonical building society information."""

    __tablename__ = "building_society"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bsa_name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_entity_name: Mapped[Optional[str]] = mapped_column(String(200))
    size_bucket: Mapped[str] = mapped_column(String(20), nullable=False)  # mega, large, regional
    website_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    trustpilot_url: Mapped[Optional[str]] = mapped_column(String(500))
    app_store_id: Mapped[Optional[str]] = mapped_column(String(50))
    play_store_id: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    aliases: Mapped[list["BuildingSocietyAlias"]] = relationship(back_populates="society")
    reviews: Mapped[list["PublicReview"]] = relationship(back_populates="society")
    metrics: Mapped[list["SummaryMetric"]] = relationship(back_populates="society")


class BuildingSocietyAlias(Base):
    """Aliases and alternative names for building societies."""

    __tablename__ = "building_society_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    building_society_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("building_society.id"), nullable=False
    )
    alias_text: Mapped[str] = mapped_column(String(200), nullable=False)
    alias_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # short_name, trading_name, acronym, misspelling, legacy_brand
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    society: Mapped["BuildingSociety"] = relationship(back_populates="aliases")


class DataSource(Base):
    """Data source platforms (Trustpilot, App Store, Play Store)."""

    __tablename__ = "data_source"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # review_platform, app_store, maps
    url_pattern: Mapped[Optional[str]] = mapped_column(String(500))
    terms_version_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    reviews: Mapped[list["PublicReview"]] = relationship(back_populates="source")


class PublicReview(Base):
    """Raw and cleaned public customer reviews."""

    __tablename__ = "public_review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("data_source.id"), nullable=False
    )
    source_review_id: Mapped[str] = mapped_column(String(200), nullable=False)
    building_society_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("building_society.id"), nullable=False
    )

    # Review content
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    rating_raw: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    rating_normalised: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1 or 1-5
    title_text: Mapped[Optional[str]] = mapped_column(Text)
    body_text_raw: Mapped[str] = mapped_column(Text, nullable=False)
    body_text_clean: Mapped[Optional[str]] = mapped_column(Text)  # PII redacted, normalised

    # Metadata
    reviewer_language: Mapped[Optional[str]] = mapped_column(String(10))
    channel: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # branch, online, mobile_app, call_centre, other, unknown
    product: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # mortgage, savings, current_account, ISA, other, unknown
    location_text: Mapped[Optional[str]] = mapped_column(String(200))
    app_version: Mapped[Optional[str]] = mapped_column(String(50))

    # Flags
    is_flagged_for_exclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(String(200))

    # Timestamps
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    cleaned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    source: Mapped["DataSource"] = relationship(back_populates="reviews")
    society: Mapped["BuildingSociety"] = relationship(back_populates="reviews")
    sentiments: Mapped[list["SentimentAspect"]] = relationship(back_populates="review")
    topics: Mapped[list["TopicTag"]] = relationship(back_populates="review")


class SentimentAspect(Base):
    """Sentiment analysis results per review, including aspect-level sentiment."""

    __tablename__ = "sentiment_aspect"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("public_review.id"), nullable=False
    )

    # Overall sentiment
    overall_sentiment_label: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # very_negative, negative, neutral, positive, very_positive
    overall_sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)  # -1 to +1

    # Aspect-level (can be "overall" or specific aspect)
    aspect: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # overall, digital_banking, branches, mortgages, savings, customer_service, etc.
    aspect_sentiment_label: Mapped[Optional[str]] = mapped_column(String(20))
    aspect_sentiment_score: Mapped[Optional[float]] = mapped_column(Float)

    # Emotion
    emotion: Mapped[Optional[str]] = mapped_column(
        String(30)
    )  # angry, frustrated, relieved, delighted, neutral

    # Model info
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    review: Mapped["PublicReview"] = relationship(back_populates="sentiments")


class TopicTag(Base):
    """Topics extracted from reviews."""

    __tablename__ = "topic_tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("public_review.id"), nullable=False
    )

    # Topic details
    topic_key: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., login_issues, slow_mortgage_processing
    topic_group: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # digital, mortgages, service, branches
    topic_label: Mapped[Optional[str]] = mapped_column(
        String(200)
    )  # Human-readable label if different

    # Confidence
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)  # 0-1

    # Model info
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    review: Mapped["PublicReview"] = relationship(back_populates="topics")


class SummaryMetric(Base):
    """Aggregated metrics at society × time × aspect level."""

    __tablename__ = "summary_metric"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    building_society_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("building_society.id"), nullable=False
    )

    # Dimensions
    time_bucket_start: Mapped[date] = mapped_column(Date, nullable=False)
    time_bucket_end: Mapped[date] = mapped_column(Date, nullable=False)
    aspect: Mapped[str] = mapped_column(String(50), nullable=False)  # overall or specific aspect
    product: Mapped[Optional[str]] = mapped_column(String(50))
    channel: Mapped[Optional[str]] = mapped_column(String(50))

    # Metrics
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False)
    avg_sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    pct_negative_reviews: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    pct_positive_reviews: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    net_sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)  # positive - negative

    # Peer comparison
    peer_group_avg_sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    peer_group_review_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Version
    metric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    society: Mapped["BuildingSociety"] = relationship(back_populates="metrics")


class EmbeddingDocument(Base):
    """Documents for the vector index (stored separately, metadata here)."""

    __tablename__ = "embedding_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # review, synthetic_summary, topic_cluster_description
    source_review_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("public_review.id")
    )
    building_society_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("building_society.id"), nullable=False
    )

    # Context for retrieval
    review_date: Mapped[Optional[date]] = mapped_column(Date)
    aspects: Mapped[Optional[str]] = mapped_column(JSON)  # List of aspects
    topics: Mapped[Optional[str]] = mapped_column(JSON)  # List of topics
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20))

    # The text that was embedded
    text_for_embedding: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector DB reference (the actual vector is stored in LanceDB)
    vector_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Version
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
