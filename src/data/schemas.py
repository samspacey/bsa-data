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
    source_url: Optional[str] = None  # Link to the original review, used for citations


class MentionType(str, Enum):
    """Kinds of non-review content about a society."""

    FORUM_POST = "forum_post"
    EDITORIAL_RATING = "editorial_rating"
    NEWS_ARTICLE = "news_article"


class RawMention(BaseModel):
    """Schema for non-review content (forum posts, editorial ratings, news).

    Kept separate from ``RawReview`` so aggregations like average rating or
    avg sentiment score do not mix one-off editorial verdicts with individual
    customer voices. Editorial ratings often have a 10-point or 5-star scale
    that is not comparable to a customer review score.
    """

    source_id: str
    source_mention_id: str
    building_society_id: str
    mention_type: MentionType
    mention_date: date
    title: Optional[str] = None
    body: str
    author: Optional[str] = None  # Redditor handle, journalist, etc.
    source_url: Optional[str] = None
    # Optional rating with its own scale — editorial sources often use 0-5 or 0-10
    rating_value: Optional[float] = None
    rating_scale_max: Optional[float] = None  # 5.0, 10.0, 100.0 etc.
    # Platform-specific extras (subreddit, upvotes, publication, verdict)
    extra: dict = Field(default_factory=dict)


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
    source_url: Optional[str] = None  # Link back to the original review, for citation clicks


class SourceCount(BaseModel):
    """Per-source review/mention count for the coverage visualisation."""

    source_id: str
    source_name: str
    count: int


class DataCoverage(BaseModel):
    """Data coverage information for transparency."""

    snapshot_end_date: date
    sources: list[str]
    total_reviews_considered: int
    per_society_review_counts: list[dict]
    # Per-source breakdown used for the source-coverage chart on the frontend
    per_source_counts: list[SourceCount] = []
    # Whether any ContentMention rows (Reddit, MSE, editorial) contributed
    includes_mentions: bool = False
    mentions_considered: int = 0


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


class PersonaSpec(BaseModel):
    """Persona details for roleplay chat (kiosk flow)."""

    id: str
    name: str
    first_name: str
    age: str
    detail: str
    concerns: list[str] = []


class ChatRequest(BaseModel):
    """Chat API request.

    In the kiosk flow, the UI pins the conversation to a specific society +
    persona — the backend scopes retrieval and prompts the model to roleplay.
    ``society_id`` and ``persona`` are both optional; without them the API
    behaves as an analyst-style Q&A.
    """

    message: str
    session_id: Optional[str] = None
    society_id: Optional[str] = None
    persona: Optional[PersonaSpec] = None


class ChatResponse(BaseModel):
    """Chat API response."""

    session_id: str
    answer: str
    metrics: list[MetricSummary] = []
    evidence_snippets: list[ReviewSnippet] = []
    data_coverage: Optional[DataCoverage] = None
    assumptions: list[str] = []
    limitations: list[str] = []
    followups: list[str] = []  # Suggested next questions


class ChatStreamMetadata(BaseModel):
    """Payload of the initial ``metadata`` SSE event for the streaming endpoint."""

    session_id: str
    metrics: list[MetricSummary] = []
    evidence_snippets: list[ReviewSnippet] = []
    data_coverage: Optional[DataCoverage] = None
    assumptions: list[str] = []
    limitations: list[str] = []
