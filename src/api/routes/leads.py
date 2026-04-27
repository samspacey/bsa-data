"""Lead-capture endpoints.

Whenever someone hits 'Email the report' in the BenchmarkModal we log a
``report_lead_captured`` event with their email address and the society
they were looking at. This module exposes those captures and lets you
retroactively send the PDF to anyone who asked for it - useful when the
SMTP backend wasn't configured at the time of capture, or when you want
to follow up later.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc

from src.api.routes.events import log_event
from src.api.routes.report import _pdf_for_society, _html_body, _text_body
from src.api.services.email_sender import send_report
from src.config.societies import SOCIETY_BY_ID
from src.data.database import get_engine, get_session
from src.data.models import AnalyticsEvent


router = APIRouter(prefix="/leads", tags=["leads"])


class Lead(BaseModel):
    """One person who asked for a benchmark report.

    ``status`` is "pending" until at least one send succeeds, then "sent".
    A previously-failed attempt is still "pending" - check ``last_error``
    to see why the last attempt didn't go through.
    """

    email: str
    society_id: Optional[str] = None
    society_name: Optional[str] = None
    region: Optional[str] = None
    captured_at: datetime
    last_attempt_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    last_error: Optional[str] = None
    status: str  # "pending" | "sent"
    attempts: int = 0


class LeadsResponse(BaseModel):
    leads: list[Lead]
    total: int
    pending: int
    sent: int


def _payload(ev: AnalyticsEvent) -> dict:
    if not ev.payload:
        return {}
    try:
        return json.loads(ev.payload)
    except Exception:  # noqa: BLE001
        return {}


def _collect_leads(window_days: int = 365) -> list[Lead]:
    """Walk the analytics_event log and reconstruct one Lead per
    (email, society) pair. Status is the most recent send outcome.
    """
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    engine = get_engine()
    with get_session(engine) as session:
        # Materialise to plain tuples inside the session — accessing ORM
        # attributes after the session closes raises DetachedInstanceError.
        rows = (
            session.query(
                AnalyticsEvent.event_type,
                AnalyticsEvent.building_society_id,
                AnalyticsEvent.payload,
                AnalyticsEvent.created_at,
            )
            .filter(AnalyticsEvent.created_at >= cutoff)
            .filter(
                AnalyticsEvent.event_type.in_(
                    [
                        "report_lead_captured",
                        "report_email_requested",
                        "report_email_sent",
                        "report_email_failed",
                    ]
                )
            )
            .order_by(AnalyticsEvent.created_at.asc())
            .all()
        )
    events = [
        type("Ev", (), {
            "event_type": r[0],
            "building_society_id": r[1],
            "payload": r[2],
            "created_at": r[3],
        })()
        for r in rows
    ]

    # Group by (email, society_id). Email is the primary key but a person
    # can ask about multiple societies - each combination is its own lead.
    grouped: dict[tuple[str, Optional[str]], dict] = defaultdict(
        lambda: {
            "captured_at": None,
            "last_attempt_at": None,
            "sent_at": None,
            "last_error": None,
            "society_name": None,
            "region": None,
            "attempts": 0,
            "status": "pending",
        }
    )

    for ev in events:
        payload = _payload(ev)
        email = payload.get("to_email")
        if not email:
            continue
        key = (email.lower(), ev.building_society_id)
        slot = grouped[key]

        if ev.event_type == "report_lead_captured":
            if slot["captured_at"] is None or ev.created_at < slot["captured_at"]:
                slot["captured_at"] = ev.created_at
            slot["society_name"] = payload.get("society_name") or slot["society_name"]
            slot["region"] = payload.get("region") or slot["region"]
        elif ev.event_type == "report_email_requested":
            slot["last_attempt_at"] = ev.created_at
            slot["attempts"] += 1
            slot["society_name"] = payload.get("society_name") or slot["society_name"]
        elif ev.event_type == "report_email_sent":
            slot["sent_at"] = ev.created_at
            slot["status"] = "sent"
            slot["last_error"] = None
        elif ev.event_type == "report_email_failed":
            slot["last_attempt_at"] = ev.created_at
            slot["last_error"] = payload.get("error") or "send failed"
            # Don't transition to "failed" - we treat failed-but-not-yet-sent
            # as "pending" so the marketer's mental model ("who do I still
            # owe an email to?") matches what /leads?status=pending returns.
            # The last_error field still reveals the previous failure.

    leads: list[Lead] = []
    for (email, society_id), v in grouped.items():
        # Backfill captured_at from the earliest known event if no
        # explicit lead_captured row (older data, before this change).
        captured_at = v["captured_at"] or v["last_attempt_at"] or datetime.utcnow()
        leads.append(
            Lead(
                email=email,
                society_id=society_id,
                society_name=v["society_name"],
                region=v["region"],
                captured_at=captured_at,
                last_attempt_at=v["last_attempt_at"],
                sent_at=v["sent_at"],
                last_error=v["last_error"],
                status=v["status"],
                attempts=v["attempts"],
            )
        )
    leads.sort(key=lambda l: l.captured_at, reverse=True)
    return leads


@router.get("/", response_model=LeadsResponse)
async def list_leads(
    status: Optional[str] = Query(None, description="Filter: pending | sent | failed"),
    days: int = Query(365, ge=1, le=3650),
) -> LeadsResponse:
    """List captured email leads, newest first.

    Each lead is one (email, society) combination. Status reflects the most
    recent send outcome - so ``pending`` means we have their email but
    never successfully delivered the PDF, ``sent`` means at least one
    attempt succeeded.
    """
    all_leads = _collect_leads(window_days=days)
    if status:
        filtered = [l for l in all_leads if l.status == status]
    else:
        filtered = all_leads
    pending = sum(1 for l in all_leads if l.status == "pending")
    sent = sum(1 for l in all_leads if l.status == "sent")
    return LeadsResponse(
        leads=filtered,
        total=len(all_leads),
        pending=pending,
        sent=sent,
    )


class SendPendingRequest(BaseModel):
    """Optional filter: send to a specific email + society, or omit to
    send to ALL pending leads."""

    email: Optional[str] = Field(None, max_length=254)
    society_id: Optional[str] = Field(None, max_length=50)
    dry_run: bool = False


class SendResult(BaseModel):
    email: str
    society_id: Optional[str] = None
    society_name: Optional[str] = None
    sent: bool
    error: Optional[str] = None


class SendPendingResponse(BaseModel):
    attempted: int
    succeeded: int
    failed: int
    results: list[SendResult]


@router.post("/send-pending", response_model=SendPendingResponse)
async def send_pending(req: SendPendingRequest) -> SendPendingResponse:
    """Retroactively send the PDF to all pending leads.

    Use cases:
    - SMTP wasn't configured when the lead was captured; now it is.
    - You want to follow up with a specific person.
    - Demo: you collected emails on a kiosk and want to fulfil them in batch.

    Pass ``dry_run=true`` to see what would be sent without actually firing
    emails. Pass ``email`` (and optionally ``society_id``) to scope to a
    single recipient.
    """
    all_leads = _collect_leads()
    pending = [l for l in all_leads if l.status == "pending"]

    if req.email:
        pending = [l for l in pending if l.email.lower() == req.email.lower()]
    if req.society_id:
        pending = [l for l in pending if l.society_id == req.society_id]

    if req.dry_run:
        return SendPendingResponse(
            attempted=len(pending),
            succeeded=0,
            failed=0,
            results=[
                SendResult(
                    email=l.email,
                    society_id=l.society_id,
                    society_name=l.society_name,
                    sent=False,
                    error="dry_run",
                )
                for l in pending
            ],
        )

    results: list[SendResult] = []
    succ = 0
    fail = 0
    for lead in pending:
        if not lead.society_id:
            results.append(
                SendResult(
                    email=lead.email,
                    society_id=None,
                    society_name=lead.society_name,
                    sent=False,
                    error="no society_id on lead",
                )
            )
            fail += 1
            continue

        society = SOCIETY_BY_ID.get(lead.society_id)
        if society is None:
            results.append(
                SendResult(
                    email=lead.email,
                    society_id=lead.society_id,
                    society_name=lead.society_name,
                    sent=False,
                    error=f"unknown society: {lead.society_id}",
                )
            )
            fail += 1
            continue

        try:
            pdf_bytes, filename, society_name = _pdf_for_society(lead.society_id, lead.region)
        except Exception as e:  # noqa: BLE001
            results.append(
                SendResult(
                    email=lead.email,
                    society_id=lead.society_id,
                    society_name=society.canonical_name,
                    sent=False,
                    error=f"PDF render failed: {e}",
                )
            )
            fail += 1
            continue

        ok, err = send_report(
            to_email=lead.email,
            subject=f"{society_name} — BSA Member Experience Benchmark",
            html_body=_html_body(society_name),
            text_body=_text_body(society_name),
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )

        log_event(
            event_type="report_email_sent" if ok else "report_email_failed",
            building_society_id=lead.society_id,
            props={
                "to_email": lead.email,
                "society_name": society_name,
                "via": "retroactive_send_pending",
                "error": err,
            },
        )
        results.append(
            SendResult(
                email=lead.email,
                society_id=lead.society_id,
                society_name=society_name,
                sent=ok,
                error=err,
            )
        )
        if ok:
            succ += 1
        else:
            fail += 1

    return SendPendingResponse(
        attempted=len(pending),
        succeeded=succ,
        failed=fail,
        results=results,
    )
