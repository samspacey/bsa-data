"""LLM-based query parsing for natural language questions."""

import json
from datetime import date
from typing import Optional

from openai import OpenAI
from rapidfuzz import fuzz, process

from src.config.settings import settings
from src.config.societies import ALIAS_TO_SOCIETY_ID, SOCIETY_BY_ID, get_all_societies
from src.data.schemas import QueryIntent


PARSE_QUERY_SYSTEM_PROMPT = """You are a query parser for a UK building society customer sentiment analysis system.
Parse the user's question into structured intent for querying review data.

## Building Societies
Available societies: {society_list}

## Focus Areas (aspects)
- overall: General sentiment
- digital_banking: Online banking, website
- mobile_app: Mobile application
- branches: Physical branches
- mortgages: Mortgage products
- savings: Savings accounts
- current_accounts: Current accounts
- customer_service: Service quality
- complaints_handling: How complaints are handled
- fees_and_rates: Charges and rates

## Question Types
- overall_sentiment: General "how are we doing" questions
- comparison: Comparing with other societies
- trend_over_time: Changes over time
- drivers_of_sentiment: What's causing positive/negative sentiment
- examples_only: Just want example reviews
- volume_and_mix: Questions about review counts and distribution

## Timeframe Types
- all_available: All data
- last_12_months: Last 12 months
- last_24_months: Last 24 months
- calendar_year: Specific year (e.g., 2024)
- since_covid: Since March 2020
- recent_generic: Vague "recently" references

## Sentiment Focus
- all: Both positive and negative
- mostly_negative: Focus on complaints/issues
- mostly_positive: Focus on praise/satisfaction

Respond with valid JSON matching the required schema."""

PARSE_QUERY_FUNCTION = {
    "name": "parse_query",
    "description": "Parse a user question about UK building societies into structured intent",
    "parameters": {
        "type": "object",
        "properties": {
            "is_follow_up": {
                "type": "boolean",
                "description": "True if referring to previous answer",
            },
            "primary_building_societies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Main societies the question is about",
            },
            "comparison_building_societies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Societies used for comparison",
            },
            "timeframe_type": {
                "type": "string",
                "enum": [
                    "all_available",
                    "last_12_months",
                    "last_24_months",
                    "calendar_year",
                    "since_covid",
                    "recent_generic",
                ],
            },
            "calendar_year": {
                "type": "integer",
                "description": "Specific year if timeframe_type is calendar_year",
            },
            "focus_areas": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "overall",
                        "digital_banking",
                        "mobile_app",
                        "branches",
                        "mortgages",
                        "savings",
                        "current_accounts",
                        "customer_service",
                        "complaints_handling",
                        "fees_and_rates",
                    ],
                },
            },
            "question_type": {
                "type": "string",
                "enum": [
                    "overall_sentiment",
                    "comparison",
                    "trend_over_time",
                    "drivers_of_sentiment",
                    "examples_only",
                    "volume_and_mix",
                ],
            },
            "sentiment_focus": {
                "type": "string",
                "enum": ["all", "mostly_negative", "mostly_positive"],
            },
            "detail_level": {
                "type": "string",
                "enum": ["brief", "standard", "board_level_summary"],
            },
        },
        "required": [
            "is_follow_up",
            "primary_building_societies",
            "comparison_building_societies",
            "timeframe_type",
            "focus_areas",
            "question_type",
            "sentiment_focus",
            "detail_level",
        ],
    },
}


class QueryParser:
    """Parse natural language queries into structured intent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.openai_model,
    ):
        """Initialize the parser.

        Args:
            api_key: OpenAI API key
            model: Model to use
        """
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model

        # Build society list for prompt
        societies = get_all_societies()
        self.society_list = ", ".join([s.canonical_name for s in societies])

    def resolve_society_name(self, name: str) -> tuple[Optional[str], float]:
        """Resolve a society name to its canonical ID.

        Args:
            name: User-provided society name

        Returns:
            Tuple of (society_id, confidence_score)
        """
        name_lower = name.lower().strip()

        # Direct lookup first
        if name_lower in ALIAS_TO_SOCIETY_ID:
            return ALIAS_TO_SOCIETY_ID[name_lower], 1.0

        # Fuzzy match against all aliases
        all_aliases = list(ALIAS_TO_SOCIETY_ID.keys())
        match = process.extractOne(name_lower, all_aliases, scorer=fuzz.ratio)

        if match and match[1] >= 70:  # 70% similarity threshold
            matched_alias = match[0]
            society_id = ALIAS_TO_SOCIETY_ID[matched_alias]
            return society_id, match[1] / 100

        return None, 0.0

    def parse(
        self,
        query: str,
        previous_intent: Optional[QueryIntent] = None,
    ) -> QueryIntent:
        """Parse a query into structured intent.

        Args:
            query: User's natural language query
            previous_intent: Intent from previous turn (for follow-ups)

        Returns:
            Parsed query intent
        """
        # Build system prompt
        system_prompt = PARSE_QUERY_SYSTEM_PROMPT.format(
            society_list=self.society_list
        )

        # Build user message with context
        user_message = f"Parse this question: {query}"
        if previous_intent:
            user_message += f"\n\nPrevious context: {json.dumps(previous_intent.model_dump(), default=str)}"

        # Call LLM with function calling
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=[{"type": "function", "function": PARSE_QUERY_FUNCTION}],
            tool_choice={"type": "function", "function": {"name": "parse_query"}},
            temperature=0.3,
        )

        # Extract function call result
        tool_call = response.choices[0].message.tool_calls[0]
        parsed = json.loads(tool_call.function.arguments)

        # Resolve society names to IDs
        resolved_primary = []
        for name in parsed.get("primary_building_societies", []):
            society_id, confidence = self.resolve_society_name(name)
            if society_id:
                resolved_primary.append(society_id)

        resolved_comparison = []
        for name in parsed.get("comparison_building_societies", []):
            society_id, confidence = self.resolve_society_name(name)
            if society_id:
                resolved_comparison.append(society_id)

        # Handle follow-ups
        if parsed.get("is_follow_up") and previous_intent:
            if not resolved_primary:
                resolved_primary = previous_intent.primary_building_societies
            if not resolved_comparison:
                resolved_comparison = previous_intent.comparison_building_societies
            if parsed.get("timeframe_type") == "all_available":
                parsed["timeframe_type"] = previous_intent.timeframe_type

        # Compute actual dates from timeframe
        timeframe_start = None
        timeframe_end = date.today()

        if parsed.get("timeframe_type") == "last_12_months":
            timeframe_start = date(timeframe_end.year - 1, timeframe_end.month, 1)
        elif parsed.get("timeframe_type") == "last_24_months":
            timeframe_start = date(timeframe_end.year - 2, timeframe_end.month, 1)
        elif parsed.get("timeframe_type") == "calendar_year":
            year = parsed.get("calendar_year", timeframe_end.year)
            timeframe_start = date(year, 1, 1)
            timeframe_end = date(year, 12, 31)
        elif parsed.get("timeframe_type") == "since_covid":
            timeframe_start = date(2020, 3, 1)
        elif parsed.get("timeframe_type") == "recent_generic":
            timeframe_start = date(timeframe_end.year, timeframe_end.month - 6, 1)

        return QueryIntent(
            is_follow_up=parsed.get("is_follow_up", False),
            primary_building_societies=resolved_primary,
            comparison_building_societies=resolved_comparison,
            timeframe_type=parsed.get("timeframe_type", "all_available"),
            timeframe_start=timeframe_start,
            timeframe_end=timeframe_end,
            focus_areas=parsed.get("focus_areas", ["overall"]),
            question_type=parsed.get("question_type", "overall_sentiment"),
            sentiment_focus=parsed.get("sentiment_focus", "all"),
            detail_level=parsed.get("detail_level", "standard"),
        )
