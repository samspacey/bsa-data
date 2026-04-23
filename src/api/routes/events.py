"""Analytics events endpoint - POST to record, GET to read back (admin)."""

import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func

from src.data.database import get_engine, get_session
from src.data.models import AnalyticsEvent


router = APIRouter(prefix="/events", tags=["events"])


class EventIn(BaseModel):
    """Payload for recording a usage event."""

    event_type: str = Field(..., max_length=60)
    session_id: Optional[str] = Field(None, max_length=64)
    building_society_id: Optional[str] = Field(None, max_length=50)
    persona_id: Optional[str] = Field(None, max_length=30)
    # Anything specific to this event: question text, email address, button,
    # page, duration, etc.
    props: Optional[dict] = None


class EventOut(BaseModel):
    id: int
    event_type: str
    session_id: Optional[str] = None
    building_society_id: Optional[str] = None
    persona_id: Optional[str] = None
    payload: Optional[dict] = None
    created_at: datetime


def log_event(
    event_type: str,
    session_id: Optional[str] = None,
    building_society_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    props: Optional[dict] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Server-side helper: other routes (chat) call this to log events directly.

    Never raises - analytics failures must not break the app.
    """
    try:
        engine = get_engine()
        with get_session(engine) as session:
            session.add(
                AnalyticsEvent(
                    event_type=event_type,
                    session_id=session_id,
                    building_society_id=building_society_id,
                    persona_id=persona_id,
                    payload=json.dumps(props, default=str) if props else None,
                    user_agent=user_agent[:400] if user_agent else None,
                    ip_address=ip_address[:50] if ip_address else None,
                )
            )
    except Exception as e:  # noqa: BLE001
        print(f"log_event failed ({event_type}): {e}")


@router.post("/")
async def record_event(event: EventIn, request: Request) -> dict:
    """Public endpoint the frontend calls to log user activity."""
    ua = request.headers.get("user-agent")
    # Trust X-Forwarded-For when running behind Railway's edge; fall back to direct.
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)

    log_event(
        event_type=event.event_type,
        session_id=event.session_id,
        building_society_id=event.building_society_id,
        persona_id=event.persona_id,
        props=event.props,
        user_agent=ua,
        ip_address=ip,
    )
    return {"ok": True}


@router.get("/recent")
async def recent_events(limit: int = 200, event_type: Optional[str] = None) -> list[EventOut]:
    """Read back the most recent events. Useful for quick inspection.

    For the demo we leave this open; lock it down behind an admin token before
    anyone other than the team reaches the URL.
    """
    engine = get_engine()
    with get_session(engine) as session:
        q = session.query(AnalyticsEvent).order_by(desc(AnalyticsEvent.created_at))
        if event_type:
            q = q.filter(AnalyticsEvent.event_type == event_type)
        rows = q.limit(max(1, min(limit, 1000))).all()
        out: list[EventOut] = []
        for r in rows:
            payload = None
            if r.payload:
                try:
                    payload = json.loads(r.payload)
                except Exception:  # noqa: BLE001
                    payload = {"_raw": r.payload}
            out.append(
                EventOut(
                    id=r.id,
                    event_type=r.event_type,
                    session_id=r.session_id,
                    building_society_id=r.building_society_id,
                    persona_id=r.persona_id,
                    payload=payload,
                    created_at=r.created_at,
                )
            )
        return out


@router.get("/summary")
async def events_summary(hours: int = 24) -> dict:
    """Per-type counts for the last N hours. Handy at-a-glance health view."""
    cutoff = datetime.utcnow() - timedelta(hours=max(1, min(hours, 24 * 90)))
    engine = get_engine()
    with get_session(engine) as session:
        rows = (
            session.query(
                AnalyticsEvent.event_type,
                func.count(AnalyticsEvent.id),
            )
            .filter(AnalyticsEvent.created_at >= cutoff)
            .group_by(AnalyticsEvent.event_type)
            .all()
        )
        counts = {row[0]: row[1] for row in rows}
        total = sum(counts.values())
        return {
            "window_hours": hours,
            "total": total,
            "by_type": counts,
        }
