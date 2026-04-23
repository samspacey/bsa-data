"""Natural-language query parsing using OpenAI with structured outputs."""

import json
from datetime import date
from enum import Enum
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.config.settings import settings
from src.config.societies import ALIAS_TO_SOCIETY_ID, SOCIETY_BY_ID, get_all_societies
from src.data.schemas import QueryIntent


class TimeframeType(str, Enum):
    ALL_AVAILABLE = "all_available"
    LAST_12_MONTHS = "last_12_months"
    LAST_24_MONTHS = "last_24_months"
    CALENDAR_YEAR = "calendar_year"
    SINCE_COVID = "since_covid"
    RECENT_GENERIC = "recent_generic"


class FocusArea(str, Enum):
    OVERALL = "overall"
    DIGITAL_BANKING = "digital_banking"
    MOBILE_APP = "mobile_app"
    BRANCHES = "branches"
    MORTGAGES = "mortgages"
    SAVINGS = "savings"
    CURRENT_ACCOUNTS = "current_accounts"
    CUSTOMER_SERVICE = "customer_service"
    COMPLAINTS_HANDLING = "complaints_handling"
    FEES_AND_RATES = "fees_and_rates"


class QuestionType(str, Enum):
    OVERALL_SENTIMENT = "overall_sentiment"
    COMPARISON = "comparison"
    TREND_OVER_TIME = "trend_over_time"
    DRIVERS_OF_SENTIMENT = "drivers_of_sentiment"
    EXAMPLES_ONLY = "examples_only"
    VOLUME_AND_MIX = "volume_and_mix"


class SentimentFocus(str, Enum):
    ALL = "all"
    MOSTLY_NEGATIVE = "mostly_negative"
    MOSTLY_POSITIVE = "mostly_positive"


class DetailLevel(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    BOARD_LEVEL_SUMMARY = "board_level_summary"


class ParsedIntent(BaseModel):
    """Typed schema for OpenAI structured output."""

    is_follow_up: bool = Field(description="True if referring to previous answer")
    primary_building_societies: list[str] = Field(default_factory=list)
    comparison_building_societies: list[str] = Field(default_factory=list)
    timeframe_type: TimeframeType = TimeframeType.ALL_AVAILABLE
    calendar_year: Optional[int] = None
    focus_areas: list[FocusArea] = Field(default_factory=lambda: [FocusArea.OVERALL])
    question_type: QuestionType = QuestionType.OVERALL_SENTIMENT
    sentiment_focus: SentimentFocus = SentimentFocus.ALL
    detail_level: DetailLevel = DetailLevel.STANDARD


PARSE_QUERY_SYSTEM_PROMPT = """You are a query parser for a UK building society customer sentiment analysis system.
Parse the user's question into structured intent for querying review data.

Available societies: {society_list}

Focus areas: overall, digital_banking, mobile_app, branches, mortgages, savings, current_accounts, customer_service, complaints_handling, fees_and_rates.
Question types: overall_sentiment, comparison, trend_over_time, drivers_of_sentiment, examples_only, volume_and_mix.
Timeframe types: all_available, last_12_months, last_24_months, calendar_year (set calendar_year), since_covid, recent_generic.
Sentiment focus: all, mostly_negative, mostly_positive."""


class QueryParser:
    """Parse natural language queries into structured intent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model or settings.openai_model

        societies = get_all_societies()
        self.society_list = ", ".join([s.canonical_name for s in societies])

    def resolve_society_name(self, name: str) -> tuple[Optional[str], float]:
        """Fuzzy-resolve a society name to its canonical ID."""
        name_lower = name.lower().strip()

        if name_lower in ALIAS_TO_SOCIETY_ID:
            return ALIAS_TO_SOCIETY_ID[name_lower], 1.0

        all_aliases = list(ALIAS_TO_SOCIETY_ID.keys())
        match = process.extractOne(name_lower, all_aliases, scorer=fuzz.ratio)

        if match and match[1] >= 70:
            matched_alias = match[0]
            society_id = ALIAS_TO_SOCIETY_ID[matched_alias]
            return society_id, match[1] / 100

        return None, 0.0

    def parse(
        self,
        query: str,
        previous_intent: Optional[QueryIntent] = None,
        forced_society_id: Optional[str] = None,
    ) -> QueryIntent:
        """Parse a query into structured intent.

        If ``forced_society_id`` is provided (the kiosk flow pins the active
        society), we skip LLM parsing for society extraction and just use that
        ID, letting the model handle timeframe / focus / sentiment / type.
        """
        system_prompt = PARSE_QUERY_SYSTEM_PROMPT.format(society_list=self.society_list)

        user_message = f"Parse this question: {query}"
        if previous_intent:
            user_message += (
                f"\n\nPrevious context: "
                f"{json.dumps(previous_intent.model_dump(), default=str)}"
            )

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                response_format=ParsedIntent,
            )
            parsed: ParsedIntent = response.choices[0].message.parsed
            if parsed is None:
                parsed = ParsedIntent()
        except Exception as e:  # noqa: BLE001
            print(f"Query parser error: {e}")
            parsed = ParsedIntent()

        # Resolve society names to IDs (or pin to forced society)
        if forced_society_id:
            resolved_primary = [forced_society_id]
            resolved_comparison: list[str] = []
        else:
            resolved_primary = []
            for name in parsed.primary_building_societies:
                society_id, _ = self.resolve_society_name(name)
                if society_id:
                    resolved_primary.append(society_id)

            resolved_comparison = []
            for name in parsed.comparison_building_societies:
                society_id, _ = self.resolve_society_name(name)
                if society_id:
                    resolved_comparison.append(society_id)

        timeframe_type = parsed.timeframe_type.value
        if parsed.is_follow_up and previous_intent:
            if not resolved_primary and not forced_society_id:
                resolved_primary = previous_intent.primary_building_societies
            if not resolved_comparison:
                resolved_comparison = previous_intent.comparison_building_societies
            if timeframe_type == "all_available":
                timeframe_type = previous_intent.timeframe_type

        timeframe_start = None
        timeframe_end = date.today()

        if timeframe_type == "last_12_months":
            timeframe_start = date(timeframe_end.year - 1, timeframe_end.month, 1)
        elif timeframe_type == "last_24_months":
            timeframe_start = date(timeframe_end.year - 2, timeframe_end.month, 1)
        elif timeframe_type == "calendar_year":
            year = parsed.calendar_year or timeframe_end.year
            timeframe_start = date(year, 1, 1)
            timeframe_end = date(year, 12, 31)
        elif timeframe_type == "since_covid":
            timeframe_start = date(2020, 3, 1)
        elif timeframe_type == "recent_generic":
            month = timeframe_end.month - 6
            year = timeframe_end.year
            if month <= 0:
                month += 12
                year -= 1
            timeframe_start = date(year, month, 1)

        return QueryIntent(
            is_follow_up=parsed.is_follow_up,
            primary_building_societies=resolved_primary,
            comparison_building_societies=resolved_comparison,
            timeframe_type=timeframe_type,
            timeframe_start=timeframe_start,
            timeframe_end=timeframe_end,
            focus_areas=[f.value for f in parsed.focus_areas],
            question_type=parsed.question_type.value,
            sentiment_focus=parsed.sentiment_focus.value,
            detail_level=parsed.detail_level.value,
        )
