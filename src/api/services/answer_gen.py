"""Answer generation using LLM with retrieved context."""

import json
from typing import Optional

from openai import OpenAI

from src.config.settings import settings
from src.data.schemas import (
    DataCoverage,
    MetricSummary,
    QueryIntent,
    ReviewSnippet,
)


ANSWER_SYSTEM_PROMPT = """You are an expert analyst presenting insights about UK building society customer sentiment.
Your answers are based on public reviews from Trustpilot and app stores.

## Guidelines
- Be concise and scannable (users have 20-30 seconds)
- Lead with the key insight
- Use British English
- Focus on themes and evidence, not exact numbers unless asked
- Always mention data coverage and limitations
- Frame statements as "In these public reviews..." not as absolute facts
- Never invent statistics not in the provided data
- If data is sparse, explicitly say so

## Answer Structure
1. **Headline** (2-3 sentences): Key takeaway
2. **Key Metrics** (if applicable): Bullet points with numbers
3. **Key Themes**: 3-5 bullet points on what customers mention
4. **Comparison** (if applicable): Brief comparison text
5. **Evidence**: 2-4 anonymised review excerpts
6. **Data Coverage**: Brief note on timeframe and sample size

Respond in markdown format."""

ANSWER_USER_TEMPLATE = """Based on the following data, answer the user's question.

## User Question
{question}

## Query Intent
{intent}

## Metrics
{metrics}

## Evidence Snippets
{snippets}

## Data Coverage
{coverage}

Please provide a well-structured answer following the guidelines."""


class AnswerGenerator:
    """Generate natural language answers from retrieved data."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.openai_model,
    ):
        """Initialize the generator.

        Args:
            api_key: OpenAI API key
            model: Model to use
        """
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model

    def generate(
        self,
        question: str,
        intent: QueryIntent,
        metrics: list[MetricSummary],
        snippets: list[ReviewSnippet],
        coverage: DataCoverage,
    ) -> str:
        """Generate an answer to the user's question.

        Args:
            question: Original user question
            intent: Parsed query intent
            metrics: Retrieved metrics
            snippets: Evidence snippets
            coverage: Data coverage info

        Returns:
            Generated answer text
        """
        # Format metrics for context
        metrics_text = json.dumps(
            [m.model_dump(mode="json") for m in metrics[:20]],  # Limit for token budget
            indent=2,
            default=str,
        )

        # Format snippets
        snippets_text = "\n\n".join([
            f"**{s.building_society_name}** ({s.source}, {s.review_date}, {s.rating}/5, {s.sentiment_label.value}):\n\"{s.snippet_text}\""
            for s in snippets[:10]
        ])

        # Format coverage
        coverage_text = f"""Snapshot date: {coverage.snapshot_end_date}
Sources: {', '.join(coverage.sources)}
Total reviews: {coverage.total_reviews_considered:,}
Per society: {json.dumps(coverage.per_society_review_counts, default=str)}"""

        # Format intent
        intent_text = json.dumps(intent.model_dump(mode="json"), default=str)

        # Build user message
        user_message = ANSWER_USER_TEMPLATE.format(
            question=question,
            intent=intent_text,
            metrics=metrics_text,
            snippets=snippets_text,
            coverage=coverage_text,
        )

        # Generate answer
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.5,
            max_tokens=1000,
        )

        return response.choices[0].message.content or "Unable to generate answer."

    def generate_no_data_response(self, question: str, intent: QueryIntent) -> str:
        """Generate a response when no data is available.

        Args:
            question: User's question
            intent: Parsed intent

        Returns:
            Response text
        """
        society_names = ", ".join(intent.primary_building_societies) or "the requested societies"

        return f"""I don't have enough data to answer your question about {society_names}.

This could be because:
- The building society may not have sufficient public reviews in our dataset
- The specific time period or aspect you asked about has limited coverage
- The society name may not match our records

**Available societies in our dataset:**
Our analysis covers the major UK building societies including Nationwide, Coventry, Yorkshire, Skipton, Leeds, Principality, West Bromwich, Newcastle, Nottingham, and Cumberland.

Would you like to try rephrasing your question or asking about a different society?"""
