"""Answer generation using OpenAI, with persona-aware roleplay support.

Two modes:
- ``generate()`` - blocking, returns full answer text (legacy ``/api/chat/``)
- ``generate_stream()`` - async generator yielding tokens for SSE streaming

The streaming path supports persona roleplay: pass ``society_name`` and
``persona`` to have the model speak as that archetype member of that society,
citing real review IDs inline as ``[[s_N]]`` markers.
"""

import json
import re
from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel


# Match a full citation marker so we can strip out-of-range indices.
_CITE_RE = re.compile(r"\[\[s_(\d+)\]\]")


def _strip_invalid_citations(text: str, max_valid_index: int) -> str:
    """Remove `[[s_N]]` markers where N > max_valid_index.

    The model is told only s_0..s_{max_valid_index} are valid, but gpt-4o-mini
    occasionally emits higher indices. Those lead to ghost pills in the UI
    (the inline superscript renders but the pill can't resolve), so we scrub
    them at the edge.
    """
    if max_valid_index < 0:
        # No snippets provided - strip all markers.
        return _CITE_RE.sub("", text)

    def _replace(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return "" if idx > max_valid_index else m.group(0)

    return _CITE_RE.sub(_replace, text)

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


ANALYST_SYSTEM_PROMPT = """You are a board-level analyst presenting insights about UK building society customer sentiment. Your audience is time-poor executives who want the truth, not reassurance.

## Length
- **One short paragraph only. Maximum 60 words.**
- No preamble ("Great question", "Here's an analysis"). Start with the substance.
- No closing summary. Stop when the point is made.

## Tone
- Balanced and honest. If complaints outweigh praise in the data, lead with the complaints. Do NOT default to positive framing.
- Use British English.
- Frame as "In these reviews..." not as absolute fact.
- Never invent statistics not in the provided data.
- If data is sparse, say so in one sentence and stop.
- Never use em dashes (the character "—"). Use a comma, full stop, colon, or hyphen-with-spaces.

## Citations — STRICT
- You MUST include at least 2 `[[s_N]]` citations pointing to DIFFERENT snippets. Never cite the same snippet twice in one answer.
- Valid indices are ONLY `s_0` through `s_{LAST}` where LAST is the highest zero-indexed snippet you see in the Evidence list. If you are unsure, do not cite. Never emit `[[s_N]]` for an N beyond what you were given.
- Cite at most one per sentence.
- Example: "Customers praise the staff [[s_1]] but report app login issues [[s_4]]."

Respond in plain markdown."""


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
- **One short paragraph only. Maximum 60 words.** Think a quick reply, not a speech.
- Be honest. If the reviews show frustration, complain. If they show praise, say so. Do NOT sugarcoat. A real member airs grievances when asked a direct question.
- Don't deflect with "on the other hand" every time you raise a complaint. Let criticism land on its own.
- No preamble. No closing summary. Just answer like a person would.
- Use British English. Occasional British idioms fit the persona.
- Never use em dashes (the character "—"). Use a comma, full stop, or hyphen-with-spaces.

## Citations — STRICT
- You MUST include at least 2 `[[s_N]]` citations pointing to DIFFERENT snippets in your answer. Never cite the same snippet twice.
- Valid indices are ONLY those that appear in the Evidence list below (e.g. `s_0`, `s_1`, ... up to the highest index shown). If you are unsure, do not cite. Never emit `[[s_N]]` for an N beyond what you were given.
- Cite at most one per sentence.
- If the Evidence is thin for the question, say so honestly in character and stop, don't make things up.
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
            max_tokens=180,
        )
        content = response.choices[0].message.content or "Unable to generate answer."
        content = content.replace("\u2014", " - ")
        max_valid = min(len(snippets), 10) - 1
        return _strip_invalid_citations(content, max_valid)

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
        """Stream answer tokens for SSE.

        Yields plain text chunks with em-dashes replaced and invalid
        ``[[s_N]]`` markers stripped. Uses a small buffer so a citation
        marker that straddles a chunk boundary is still caught.
        """
        messages = self._build_messages(
            question, snippets, metrics, coverage, society_name, persona
        )
        stream = await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6 if persona else 0.5,
            max_tokens=180,
            stream=True,
        )

        max_valid = min(len(snippets), 10) - 1
        # Hold back text that could still form a citation marker. A full
        # marker is at most `[[s_N]]` = 8 chars, so buffering 9 chars worth
        # of "tail" is enough to guarantee any in-flight marker completes
        # before we yield.
        buffer = ""
        MIN_TAIL = 9

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not (delta and delta.content):
                continue

            buffer += delta.content.replace("\u2014", " - ")

            # Emit everything except the last MIN_TAIL chars, because those
            # could still be part of an incomplete marker.
            if len(buffer) > MIN_TAIL:
                emit = buffer[:-MIN_TAIL]
                buffer = buffer[-MIN_TAIL:]
                cleaned = _strip_invalid_citations(emit, max_valid)
                if cleaned:
                    yield cleaned

        # Drain the buffer at the end.
        if buffer:
            cleaned = _strip_invalid_citations(buffer, max_valid)
            if cleaned:
                yield cleaned

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
