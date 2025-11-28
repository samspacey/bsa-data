"""LLM-based enrichment for sentiment, topics, and classification."""

import asyncio
import json
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.data.schemas import (
    AspectSentiment,
    Channel,
    Emotion,
    EnrichmentResult,
    Product,
    SentimentLabel,
)


# Note: We don't use a strict Pydantic model because LLM output varies
# Instead we parse the JSON manually with flexibility


ENRICHMENT_SYSTEM_PROMPT = """You are an expert analyst for UK building society customer reviews.
Analyse the given review and extract structured information.

## Sentiment Labels (choose one for overall and per-aspect)
- very_negative: Extremely dissatisfied, angry, would never recommend
- negative: Dissatisfied, disappointed, problems not resolved
- neutral: Mixed feelings, neither satisfied nor dissatisfied
- positive: Generally satisfied, good experience
- very_positive: Extremely satisfied, delighted, highly recommend

## Aspect Categories (only include if mentioned in review)
- digital_banking: Online banking, website, general digital experience
- mobile_app: Mobile application specifically
- branches: Physical branch experience, in-person service
- mortgages: Mortgage products, applications, advice
- savings: Savings accounts, interest rates, ISAs
- current_accounts: Current/checking accounts
- customer_service: General service quality, responsiveness
- complaints_handling: How complaints were dealt with
- fees_and_rates: Charges, interest rates, value for money
- onboarding: Account opening, joining process

## Topics (use these when applicable, or create concise new ones)
Positive: friendly_staff, easy_process, quick_response, good_rates, reliable_service,
         helpful_advice, smooth_experience, clear_communication
Negative: login_issues, slow_processing, poor_communication, unhelpful_staff,
         long_wait_times, app_crashes, hidden_fees, rate_changes, account_access_problems

## Channels
- branch: Physical branch visit
- online: Website/internet banking
- mobile_app: Mobile phone application
- call_centre: Phone call to customer service
- other: Other channels
- unknown: Cannot determine

## Products
- mortgage: Home loans, remortgaging
- savings: Savings accounts, fixed rate bonds
- current_account: Current/checking accounts
- ISA: Individual Savings Accounts
- other: Other products
- unknown: Cannot determine

Respond with valid JSON only. Be concise but accurate."""

ENRICHMENT_USER_TEMPLATE = """Analyse this review:

Rating: {rating}/5
Title: {title}
Review: {body}

Extract: overall sentiment (label + score -1 to +1), aspect sentiments for mentioned aspects only,
primary emotion, key topics (3-5), channel if determinable, product if determinable."""


class ReviewEnricher:
    """Enrich reviews with LLM-based analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.openai_model,
        max_concurrent: int = settings.max_concurrent_requests,
    ):
        """Initialize the enricher.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Model to use for enrichment
            max_concurrent: Maximum concurrent API requests
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._total_cost = 0.0

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for current event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _parse_sentiment_label(self, label: str) -> SentimentLabel:
        """Parse sentiment label string to enum."""
        label_map = {
            "very_negative": SentimentLabel.VERY_NEGATIVE,
            "negative": SentimentLabel.NEGATIVE,
            "neutral": SentimentLabel.NEUTRAL,
            "positive": SentimentLabel.POSITIVE,
            "very_positive": SentimentLabel.VERY_POSITIVE,
        }
        return label_map.get(label.lower(), SentimentLabel.NEUTRAL)

    def _parse_emotion(self, emotion: Optional[str]) -> Optional[Emotion]:
        """Parse emotion string to enum."""
        if not emotion:
            return None
        emotion_map = {
            "angry": Emotion.ANGRY,
            "frustrated": Emotion.FRUSTRATED,
            "relieved": Emotion.RELIEVED,
            "delighted": Emotion.DELIGHTED,
            "neutral": Emotion.NEUTRAL,
        }
        return emotion_map.get(emotion.lower())

    def _parse_channel(self, channel: Optional[str]) -> Optional[Channel]:
        """Parse channel string to enum."""
        if not channel:
            return None
        channel_map = {
            "branch": Channel.BRANCH,
            "online": Channel.ONLINE,
            "mobile_app": Channel.MOBILE_APP,
            "call_centre": Channel.CALL_CENTRE,
            "other": Channel.OTHER,
            "unknown": Channel.UNKNOWN,
        }
        return channel_map.get(channel.lower())

    def _parse_product(self, product: Optional[str]) -> Optional[Product]:
        """Parse product string to enum."""
        if not product:
            return None
        product_map = {
            "mortgage": Product.MORTGAGE,
            "savings": Product.SAVINGS,
            "current_account": Product.CURRENT_ACCOUNT,
            "isa": Product.ISA,
            "other": Product.OTHER,
            "unknown": Product.UNKNOWN,
        }
        return product_map.get(product.lower())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def _call_llm(
        self, review_id: int, rating: int, title: Optional[str], body: str
    ) -> Optional[dict]:
        """Call the LLM to analyse a review.

        Args:
            review_id: Review ID for tracking
            rating: Star rating (1-5)
            title: Review title (optional)
            body: Review body text

        Returns:
            Parsed JSON dict or None on failure
        """
        async with self._get_semaphore():
            try:
                user_message = ENRICHMENT_USER_TEMPLATE.format(
                    rating=rating,
                    title=title or "(No title)",
                    body=body[:2000],  # Truncate very long reviews
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=500,
                )

                # Track cost (approximate for gpt-4o-mini)
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0
                cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
                self._total_cost += cost

                # Parse response
                content = response.choices[0].message.content
                if not content:
                    return None

                return json.loads(content)

            except Exception as e:
                print(f"  Error enriching review {review_id}: {e}")
                return None

    def _extract_sentiment(self, data: dict) -> tuple:
        """Extract overall sentiment from flexible JSON format.

        Returns:
            Tuple of (label, score)
        """
        overall = data.get("overall_sentiment", {})

        # Handle both formats: string or {'label': ..., 'score': ...}
        if isinstance(overall, str):
            label = overall
            score = data.get("overall_sentiment_score", 0)
        elif isinstance(overall, dict):
            label = overall.get("label", "neutral")
            score = overall.get("score", 0)
        else:
            label = "neutral"
            score = 0

        return label, float(score)

    def _extract_aspect_sentiments(self, data: dict) -> list:
        """Extract aspect sentiments from flexible JSON format."""
        aspects_data = data.get("aspect_sentiments", {})
        results = []

        # Handle list format: [{'aspect': ..., 'sentiment': ..., 'score': ...}]
        if isinstance(aspects_data, list):
            for asp in aspects_data:
                if isinstance(asp, dict):
                    results.append(
                        AspectSentiment(
                            aspect=asp.get("aspect", "unknown"),
                            sentiment_label=self._parse_sentiment_label(
                                asp.get("sentiment", asp.get("label", "neutral"))
                            ),
                            sentiment_score=float(asp.get("score", 0)),
                        )
                    )
        # Handle dict format: {'customer_service': {'label': ..., 'score': ...}}
        elif isinstance(aspects_data, dict):
            for aspect_name, asp_data in aspects_data.items():
                if isinstance(asp_data, dict):
                    results.append(
                        AspectSentiment(
                            aspect=aspect_name,
                            sentiment_label=self._parse_sentiment_label(
                                asp_data.get("label", asp_data.get("sentiment", "neutral"))
                            ),
                            sentiment_score=float(asp_data.get("score", 0)),
                        )
                    )

        return results

    async def enrich_review(
        self, review_id: int, rating: int, title: Optional[str], body: str
    ) -> Optional[EnrichmentResult]:
        """Enrich a single review.

        Args:
            review_id: Database review ID
            rating: Star rating
            title: Review title
            body: Review body

        Returns:
            Enrichment result or None
        """
        data = await self._call_llm(review_id, rating, title, body)
        if not data:
            return None

        # Extract sentiment with flexible parsing
        sentiment_label, sentiment_score = self._extract_sentiment(data)
        aspect_sentiments = self._extract_aspect_sentiments(data)

        # Extract topics (can be list or other format)
        topics = data.get("topics", [])
        if not isinstance(topics, list):
            topics = []

        return EnrichmentResult(
            review_id=review_id,
            overall_sentiment=self._parse_sentiment_label(sentiment_label),
            overall_sentiment_score=sentiment_score,
            aspect_sentiments=aspect_sentiments,
            emotion=self._parse_emotion(data.get("emotion")),
            topics=topics,
            channel=self._parse_channel(data.get("channel")),
            product=self._parse_product(data.get("product")),
        )

    async def enrich_batch(
        self,
        reviews: list[tuple[int, int, Optional[str], str]],
    ) -> list[Optional[EnrichmentResult]]:
        """Enrich a batch of reviews concurrently.

        Args:
            reviews: List of (review_id, rating, title, body) tuples

        Returns:
            List of enrichment results (None for failed enrichments)
        """
        tasks = [
            self.enrich_review(review_id, rating, title, body)
            for review_id, rating, title, body in reviews
        ]
        return await asyncio.gather(*tasks)

    @property
    def total_cost(self) -> float:
        """Get the total estimated API cost so far."""
        return self._total_cost

    def reset_cost_tracking(self):
        """Reset the cost counter."""
        self._total_cost = 0.0
