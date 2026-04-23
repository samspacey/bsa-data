"""Answer generation using OpenAI, with persona-aware roleplay support.

Two modes:
- ``generate()`` - blocking, returns full answer text (legacy ``/api/chat/``)
- ``generate_stream()`` - async generator yielding tokens for SSE streaming

The streaming path supports persona roleplay: pass ``society_name`` and
``persona`` to have the model speak as that archetype member of that society,
citing real review IDs inline as ``[[s_N]]`` markers.
"""

import json
from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from src.config.settings import settings
from src.data.schemas import (
    DataCoverage,
    MetricSummary,
    QueryIntent,
    ReviewSnippet,
)


class Persona(BaseModel):
    """Describe a persona the model should roleplay as."""

    id: str
    name: str            # e.g. "The Loyalist"
    first_name: str      # e.g. "Margaret"
    age: str             # e.g. "70-80"
    detail: str          # e.g. "Uses the Newport branch weekly..."
    concerns: List[str]  # e.g. ["Branch closures", ...]


ANALYST_SYSTEM_PROMPT = """You are an expert analyst presenting insights about UK building society customer sentiment.
Your answers are grounded in public reviews, forum mentions, and editorial ratings.

## Guidelines
- Be concise and scannable (users have 20-30 seconds)
- Lead with the key insight
- Use British English
- Focus on themes and evidence, not exact numbers unless asked
- Always mention data coverage and limitations
- Frame statements as "In these public reviews..." not as absolute facts
- Never invent statistics not in the provided data
- If data is sparse, explicitly say so
- Never use em dashes (the character "—"). Use a comma, full stop, colon, or hyphen-with-spaces instead.

## Citation Format
When you reference a specific review, insert an inline citation marker ``[[s_N]]`` where N is the zero-indexed position of the snippet. Example: "Customers praise the app [[s_0]], though some report login issues [[s_2]]."

Do NOT invent snippet IDs. Only cite snippets from the provided list. Cite at most one snippet per sentence.

## Answer Structure
1. **Headline** (2-3 sentences): Key takeaway, with 1-2 citations
2. **Key Themes**: 3-5 bullet points with citations
3. **Data Coverage**: Brief note on sample size and sources

Respond in markdown format."""


def build_persona_system_prompt(society_name: str, persona: Persona) -> str:
    """Build a system prompt for persona-roleplay chat.

    The model speaks AS the persona - first person, in character - grounded in
    the real reviews passed as context. The citation syntax is preserved so
    the frontend can render pills back to specific reviews.
    """
    concerns = ", ".join(persona.concerns)
    return f"""You are {persona.first_name}, a simulated member of {society_name} who fits the "{persona.name}" archetype.

## Your background
- Age: {persona.age}
- {persona.detail}
- Things you care about: {concerns}

## How to respond
- Speak in first person AS {persona.first_name}. Do not break character.
- Be conversational, not a report. Short paragraphs. Natural speech.
- Use British English. Occasional British idioms fit the persona.
- Never use em dashes (the character "—"). Use a comma, full stop, or hyphen-with-spaces instead.
- Ground what you say in the real reviews provided in the user message. When a specific review supports a point you make, cite it inline using ``[[s_N]]`` where N is the zero-indexed position of that snippet in the Evidence list.
- Only cite snippets that appear in the Evidence list. Do not invent snippet IDs. Cite at most one per sentence.
- If the Evidence is thin for the question asked, say so honestly in character ("I can't really speak to that, it's not something I've run into") rather than making things up.
- You are explicitly a simulation. If asked directly whether you are a real member, acknowledge you're a simulated composite informed by real reviews.

## Context about the society and recent member feedback
You are aware (as a member of this society) of broad sentiment trends in the data, but you speak from personal experience, not as an analyst. Do not quote statistics at the user - leave that to the analysts. Speak as a real member would."""


ANSWER_USER_TEMPLATE_ANALYST = """Based on the following data, answer the user's question.

## User Question
{question}

## Metrics
{metrics}

## Evidence Snippets
{snippets}

## Data Coverage
{coverage}
"""


ANSWER_USER_TEMPLATE_PERSONA = """The board member is asking you (a simulated {society_name} member) a question. Answer in character.

## Question
{question}

## Recent feedback from actual members of {society_name} (use as grounding; cite with [[s_N]] where relevant)
{snippets}

## Summary of how members feel (for your awareness only; do not quote as statistics)
{metrics}
"""


FOLLOWUP_SYSTEM_PROMPT_ANALYST = """You generate 3 short, natural-sounding follow-up questions for a user exploring UK building society customer sentiment.

Return ONLY a JSON array of 3 strings. No commentary."""


FOLLOWUP_SYSTEM_PROMPT_PERSONA = """You generate 3 short follow-up questions a board member or executive might want to ask a simulated member of a UK building society, given the conversation so far.

Questions should be short, direct, and appropriate to ask a real member - not an analyst. They should push the conversation forward or probe a theme that came up.

Return ONLY a JSON array of 3 strings. No commentary."""


class AnswerGenerator:
    """Generate natural language answers from retrieved data using OpenAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        key = api_key or settings.openai_api_key
        self.client = OpenAI(api_key=key)
        self.async_client = AsyncOpenAI(api_key=key)
        self.model = model or settings.openai_model

    def _format_snippets(self, snippets: list[ReviewSnippet]) -> str:
        return "\n\n".join(
            [
                f"[s_{i}] **{s.building_society_name}** ({s.source}, {s.review_date}, "
                f"{s.rating}/5, {s.sentiment_label.value}):\n\"{s.snippet_text}\""
                for i, s in enumerate(snippets[:10])
            ]
        )

    def _format_metrics(self, metrics: list[MetricSummary]) -> str:
        return json.dumps(
            [m.model_dump(mode="json") for m in metrics[:10]],
            indent=2,
            default=str,
        )

    def _format_coverage(self, coverage: DataCoverage) -> str:
        return (
            f"Snapshot date: {coverage.snapshot_end_date}\n"
            f"Sources: {', '.join(coverage.sources)}\n"
            f"Total reviews: {coverage.total_reviews_considered:,}"
        )

    def _build_messages(
        self,
        question: str,
        snippets: list[ReviewSnippet],
        metrics: list[MetricSummary],
        coverage: DataCoverage,
        society_name: Optional[str],
        persona: Optional[Persona],
    ) -> list[dict]:
        """Select system prompt + user template based on persona mode."""
        snippets_text = self._format_snippets(snippets)
        metrics_text = self._format_metrics(metrics)
        coverage_text = self._format_coverage(coverage)

        if persona and society_name:
            system = build_persona_system_prompt(society_name, persona)
            user = ANSWER_USER_TEMPLATE_PERSONA.format(
                society_name=society_name,
                question=question,
                snippets=snippets_text,
                metrics=metrics_text,
            )
        else:
            system = ANALYST_SYSTEM_PROMPT
            user = ANSWER_USER_TEMPLATE_ANALYST.format(
                question=question,
                metrics=metrics_text,
                snippets=snippets_text,
                coverage=coverage_text,
            )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def generate(
        self,
        question: str,
        intent: QueryIntent,
        metrics: list[MetricSummary],
        snippets: list[ReviewSnippet],
        coverage: DataCoverage,
        society_name: Optional[str] = None,
        persona: Optional[Persona] = None,
    ) -> str:
        """Blocking answer generation (legacy ``/api/chat/`` endpoint)."""
        messages = self._build_messages(
            question, snippets, metrics, coverage, society_name, persona
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6 if persona else 0.5,
            max_tokens=1000,
        )
        content = response.choices[0].message.content or "Unable to generate answer."
        return content.replace("\u2014", " - ")

    async def generate_stream(
        self,
        question: str,
        intent: QueryIntent,
        metrics: list[MetricSummary],
        snippets: list[ReviewSnippet],
        coverage: DataCoverage,
        society_name: Optional[str] = None,
        persona: Optional[Persona] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream answer tokens for SSE. Yields plain text chunks."""
        messages = self._build_messages(
            question, snippets, metrics, coverage, society_name, persona
        )
        stream = await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6 if persona else 0.5,
            max_tokens=1000,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                # Belt-and-braces: the system prompt forbids em dashes, but the
                # model occasionally emits one anyway. Strip at the edge so the
                # UI never sees U+2014.
                yield delta.content.replace("\u2014", " - ")

    async def generate_followups(
        self,
        question: str,
        answer: str,
        coverage: DataCoverage,
        persona: Optional[Persona] = None,
    ) -> list[str]:
        """Generate 3 suggested follow-up questions."""
        try:
            system = (
                FOLLOWUP_SYSTEM_PROMPT_PERSONA if persona else FOLLOWUP_SYSTEM_PROMPT_ANALYST
            )
            user_message = (
                f"## User asked:\n{question}\n\n"
                f"## Answer received:\n{answer}\n\n"
                f"Return 3 follow-up questions as a JSON array."
            )
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            raw = (response.choices[0].message.content or "[]").strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            suggestions = json.loads(raw)
            if isinstance(suggestions, list):
                return [str(s)[:140] for s in suggestions[:3] if s]
        except Exception as e:  # noqa: BLE001
            print(f"Follow-up generation error: {e}")
        return []

    def generate_no_data_response(
        self,
        question: str,
        intent: QueryIntent,
        persona: Optional[Persona] = None,
    ) -> str:
        """Fallback when no data is available - short, in-character if persona set."""
        if persona:
            return (
                f"Honestly, I couldn't tell you - that's not something I've come across "
                "as a member. You might want to check with someone who works there."
            )
        society_names = (
            ", ".join(intent.primary_building_societies)
            or "the requested societies"
        )
        return f"I don't have enough data to answer your question about {society_names}. Our coverage is strongest on Trustpilot, app store reviews and Smart Money People. Try rephrasing, or ask about a different society."
