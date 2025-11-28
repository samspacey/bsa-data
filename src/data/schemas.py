"""Pydantic schemas for data validation and API contracts."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# Enums for constrained values
class SizeBucket(str, Enum):
    MEGA = "mega"
    LARGE = "large"
    REGIONAL = "regional"


class SourceType(str, Enum):
    REVIEW_PLATFORM = "review_platform"
    APP_STORE = "app_store"
    MAPS = "maps"


class Channel(str, Enum):
    BRANCH = "branch"
    ONLINE = "online"
    MOBILE_APP = "mobile_app"
    CALL_CENTRE = "call_centre"
    OTHER = "other"
    UNKNOWN = "unknown"


class Product(str, Enum):
    MORTGAGE = "mortgage"
    SAVINGS = "savings"
    CURRENT_ACCOUNT = "current_account"
    ISA = "ISA"
    OTHER = "other"
    UNKNOWN = "unknown"


class SentimentLabel(str, Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class Emotion(str, Enum):
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    RELIEVED = "relieved"
    DELIGHTED = "delighted"
    NEUTRAL = "neutral"


# Scraped review schema (before cleaning)
class RawReview(BaseModel):
    """Schema for raw scraped review data."""

    source_id: str
    source_review_id: str
    building_society_id: str
    review_date: date
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = None
    body: str
    reviewer_name: Optional[str] = None  # Will be redacted
    location: Optional[str] = None
    app_version: Optional[str] = None


# Cleaned review schema
class CleanedReview(BaseModel):
    """Schema for cleaned and normalized review data."""

    id: Optional[int] = None
    source_id: str
    source_review_id: str
    building_society_id: str
    review_date: date
    rating_raw: int = Field(ge=1, le=5)
    rating_normalised: float = Field(ge=0, le=1)
    title_text: Optional[str] = None
    body_text_raw: str
    body_text_clean: str
    reviewer_language: Optional[str] = None
    channel: Optional[Channel] = None
    product: Optional[Product] = None
    location_text: Optional[str] = None
    app_version: Optional[str] = None
    is_flagged_for_exclusion: bool = False
    exclusion_reason: Optional[str] = None


# Sentiment extraction output
class AspectSentiment(BaseModel):
    """Sentiment for a specific aspect."""

    aspect: str
    sentiment_label: SentimentLabel
    sentiment_score: float = Field(ge=-1, le=1)


class SentimentResult(BaseModel):
    """Complete sentiment analysis result for a review."""

    review_id: int
    overall_sentiment_label: SentimentLabel
    overall_sentiment_score: float = Field(ge=-1, le=1)
    aspect_sentiments: list[AspectSentiment] = []
    emotion: Optional[Emotion] = None
    model_version: str


# Topic extraction output
class TopicResult(BaseModel):
    """Topic extracted from a review."""

    review_id: int
    topic_key: str
    topic_group: str
    topic_label: Optional[str] = None
    relevance_score: float = Field(ge=0, le=1, default=1.0)
    model_version: str


# LLM enrichment combined output
class EnrichmentResult(BaseModel):
    """Combined enrichment result from LLM analysis."""

    review_id: int
    overall_sentiment: SentimentLabel
    overall_sentiment_score: float = Field(ge=-1, le=1)
    aspect_sentiments: list[AspectSentiment] = []
    emotion: Optional[Emotion] = None
    topics: list[str] = []  # List of topic_keys
    channel: Optional[Channel] = None
    product: Optional[Product] = None


# Summary metrics
class MetricSummary(BaseModel):
    """Aggregated metric for a society."""

    building_society_id: str
    building_society_name: str
    time_bucket_start: date
    time_bucket_end: date
    aspect: str
    review_count: int
    avg_rating: float
    avg_sentiment_score: float
    pct_negative_reviews: float = Field(ge=0, le=1)
    pct_positive_reviews: float = Field(ge=0, le=1)
    net_sentiment_score: float
    peer_group_avg_sentiment_score: Optional[float] = None
    peer_group_review_count: Optional[int] = None


# API schemas
class BuildingSocietyInfo(BaseModel):
    """Building society information for API responses."""

    id: str
    canonical_name: str
    size_bucket: SizeBucket
    aliases: list[str] = []


class ReviewSnippet(BaseModel):
    """Review snippet for evidence in answers."""

    snippet_id: str
    building_society_id: str
    building_society_name: str
    source: str
    review_date: date
    rating: int
    sentiment_label: SentimentLabel
    aspects: list[str] = []
    topics: list[str] = []
    snippet_text: str


class DataCoverage(BaseModel):
    """Data coverage information for transparency."""

    snapshot_end_date: date
    sources: list[str]
    total_reviews_considered: int
    per_society_review_counts: list[dict]


class QueryIntent(BaseModel):
    """Parsed query intent from LLM."""

    is_follow_up: bool = False
    primary_building_societies: list[str] = []
    comparison_building_societies: list[str] = []
    timeframe_type: str = "all_available"
    timeframe_start: Optional[date] = None
    timeframe_end: Optional[date] = None
    focus_areas: list[str] = []
    question_type: str = "overall_sentiment"
    sentiment_focus: str = "all"
    detail_level: str = "standard"


class ChatRequest(BaseModel):
    """Chat API request."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat API response."""

    session_id: str
    answer: str
    metrics: list[MetricSummary] = []
    evidence_snippets: list[ReviewSnippet] = []
    data_coverage: Optional[DataCoverage] = None
    assumptions: list[str] = []
    limitations: list[str] = []
