"""Chat endpoint for the conversational interface."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.data.database import get_engine, get_session
from src.data.schemas import ChatRequest, ChatResponse, QueryIntent
from src.api.services.answer_gen import AnswerGenerator
from src.api.services.query_parser import QueryParser
from src.api.services.retrieval import RetrievalService
from src.embeddings.index import VectorIndex


router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store (for demo purposes)
_sessions: dict[str, dict] = {}


def get_session_state(session_id: Optional[str]) -> dict:
    """Get or create session state."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {
        "id": new_id,
        "previous_intent": None,
        "turn_count": 0,
    }
    return _sessions[new_id]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle a chat message.

    Args:
        request: Chat request with message and optional session ID

    Returns:
        Chat response with answer and supporting data
    """
    # Get session state
    session = get_session_state(request.session_id)
    session["turn_count"] += 1

    # Initialize services
    query_parser = QueryParser()
    answer_generator = AnswerGenerator()

    try:
        # Parse the query
        previous_intent = session.get("previous_intent")
        if previous_intent:
            previous_intent = QueryIntent(**previous_intent)

        intent = query_parser.parse(request.message, previous_intent)

        # Store intent for follow-ups
        session["previous_intent"] = intent.model_dump(mode="json")

        # Get database session
        engine = get_engine()
        with get_session(engine) as db_session:
            # Initialize retrieval
            vector_index = VectorIndex()
            retrieval = RetrievalService(db_session, vector_index)

            # Get metrics
            metrics = retrieval.get_metrics(intent)

            # Get evidence snippets (async)
            snippets = await retrieval.get_evidence_snippets(intent, limit=10)

            # Get data coverage
            coverage = retrieval.get_data_coverage(intent)

        # Generate answer
        if not metrics and not snippets:
            answer = answer_generator.generate_no_data_response(request.message, intent)
        else:
            answer = answer_generator.generate(
                question=request.message,
                intent=intent,
                metrics=metrics,
                snippets=snippets,
                coverage=coverage,
            )

        # Build assumptions list
        assumptions = []
        for society_id in intent.primary_building_societies:
            # Check if we fuzzy-matched
            if society_id not in request.message.lower():
                from src.config.societies import SOCIETY_BY_ID
                society = SOCIETY_BY_ID.get(society_id)
                if society:
                    assumptions.append(
                        f"Interpreted query as referring to {society.canonical_name}"
                    )

        # Build limitations
        limitations = [
            "Based on public reviews which may over-represent customers with strong opinions",
        ]
        if coverage.total_reviews_considered < 100:
            limitations.append("Limited sample size - results should be treated as indicative")

        return ChatResponse(
            session_id=session["id"],
            answer=answer,
            metrics=metrics[:10],  # Limit for response size
            evidence_snippets=snippets,
            data_coverage=coverage,
            assumptions=assumptions,
            limitations=limitations,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(session_id: Optional[str] = None) -> dict:
    """Reset a chat session.

    Args:
        session_id: Session to reset (all sessions if not specified)

    Returns:
        Confirmation message
    """
    if session_id:
        if session_id in _sessions:
            del _sessions[session_id]
            return {"message": f"Session {session_id} reset"}
        return {"message": "Session not found"}

    _sessions.clear()
    return {"message": "All sessions reset"}
