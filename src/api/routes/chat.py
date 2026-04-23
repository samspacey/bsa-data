"""Chat endpoint for the conversational interface."""

import json
import uuid
from typing import AsyncGenerator, Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config.societies import SOCIETY_BY_ID
from src.data.database import get_engine, get_session
from src.data.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamMetadata,
    PersonaSpec,
    QueryIntent,
)
from src.api.services.answer_gen import AnswerGenerator, Persona
from src.api.services.query_parser import QueryParser
from src.api.services.retrieval import RetrievalService
from src.embeddings.index import VectorIndex


router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store (for demo purposes)
_sessions: dict[str, dict] = {}


def get_session_state(session_id: Optional[str]) -> dict:
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {
        "id": new_id,
        "previous_intent": None,
        "turn_count": 0,
    }
    return _sessions[new_id]


def _persona_from_request(spec: Optional[PersonaSpec]) -> Optional[Persona]:
    if spec is None:
        return None
    return Persona(
        id=spec.id,
        name=spec.name,
        first_name=spec.first_name,
        age=spec.age,
        detail=spec.detail,
        concerns=spec.concerns,
    )


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle a chat message (blocking, non-streaming)."""
    session = get_session_state(request.session_id)
    session["turn_count"] += 1

    query_parser = QueryParser()
    answer_generator = AnswerGenerator()
    persona = _persona_from_request(request.persona)
    society = SOCIETY_BY_ID.get(request.society_id) if request.society_id else None
    society_name = society.canonical_name if society else None

    try:
        previous_intent = session.get("previous_intent")
        if previous_intent:
            previous_intent = QueryIntent(**previous_intent)

        intent = query_parser.parse(
            request.message,
            previous_intent,
            forced_society_id=request.society_id,
        )
        session["previous_intent"] = intent.model_dump(mode="json")

        engine = get_engine()
        with get_session(engine) as db_session:
            vector_index = VectorIndex()
            retrieval = RetrievalService(db_session, vector_index)

            metrics = retrieval.get_metrics(intent)
            snippets = await retrieval.get_evidence_snippets(intent, limit=10)
            coverage = retrieval.get_data_coverage(intent)

        if not metrics and not snippets:
            answer = answer_generator.generate_no_data_response(
                request.message, intent, persona=persona
            )
        else:
            answer = answer_generator.generate(
                question=request.message,
                intent=intent,
                metrics=metrics,
                snippets=snippets,
                coverage=coverage,
                society_name=society_name,
                persona=persona,
            )

        assumptions: list[str] = []
        limitations = []
        if persona is None:
            limitations.append(
                "Based on public reviews which may over-represent customers with strong opinions"
            )
        if coverage.total_reviews_considered < 100:
            limitations.append("Limited sample size - results should be treated as indicative")

        return ChatResponse(
            session_id=session["id"],
            answer=answer,
            metrics=metrics[:10] if persona is None else [],
            evidence_snippets=snippets,
            data_coverage=coverage,
            assumptions=assumptions,
            limitations=limitations,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _sse(event: str, data: Union[dict, str]) -> str:
    if isinstance(data, dict):
        payload = json.dumps(data, default=str)
    else:
        payload = json.dumps({"text": data})
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat via SSE. Supports optional society + persona roleplay."""
    session = get_session_state(request.session_id)
    session["turn_count"] += 1

    query_parser = QueryParser()
    answer_generator = AnswerGenerator()
    persona = _persona_from_request(request.persona)
    society = SOCIETY_BY_ID.get(request.society_id) if request.society_id else None
    society_name = society.canonical_name if society else None

    previous_intent = session.get("previous_intent")
    if previous_intent:
        previous_intent = QueryIntent(**previous_intent)
    intent = query_parser.parse(
        request.message,
        previous_intent,
        forced_society_id=request.society_id,
    )
    session["previous_intent"] = intent.model_dump(mode="json")

    engine = get_engine()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        accumulated = ""
        with get_session(engine) as db_session:
            vector_index = VectorIndex()
            retrieval = RetrievalService(db_session, vector_index)

            metrics = retrieval.get_metrics(intent)
            snippets = await retrieval.get_evidence_snippets(intent, limit=10)
            coverage = retrieval.get_data_coverage(intent)

            limitations: list[str] = []
            if persona is None:
                limitations.append(
                    "Based on public reviews which may over-represent customers with strong opinions"
                )
            if coverage.total_reviews_considered < 100:
                limitations.append("Limited sample size - results should be treated as indicative")

            metadata = ChatStreamMetadata(
                session_id=session["id"],
                metrics=metrics[:10] if persona is None else [],
                evidence_snippets=snippets,
                data_coverage=coverage,
                assumptions=[],
                limitations=limitations,
            )
            yield _sse("metadata", metadata.model_dump(mode="json")).encode("utf-8")

            if not metrics and not snippets:
                text = answer_generator.generate_no_data_response(
                    request.message, intent, persona=persona
                )
                accumulated = text
                yield _sse("token", text).encode("utf-8")
            else:
                async for chunk in answer_generator.generate_stream(
                    question=request.message,
                    intent=intent,
                    metrics=metrics,
                    snippets=snippets,
                    coverage=coverage,
                    society_name=society_name,
                    persona=persona,
                ):
                    accumulated += chunk
                    yield _sse("token", chunk).encode("utf-8")

            followups = await answer_generator.generate_followups(
                question=request.message,
                answer=accumulated,
                coverage=coverage,
                persona=persona,
            )
            yield _sse("followups", {"followups": followups}).encode("utf-8")

        yield _sse("done", {}).encode("utf-8")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/reset")
async def reset_session(session_id: Optional[str] = None) -> dict:
    if session_id:
        if session_id in _sessions:
            del _sessions[session_id]
            return {"message": f"Session {session_id} reset"}
        return {"message": "Session not found"}

    _sessions.clear()
    return {"message": "All sessions reset"}
