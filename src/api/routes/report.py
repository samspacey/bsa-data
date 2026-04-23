"""Benchmark report endpoints: PDF download + PDF-attached email send."""

from __future__ import annotations

import base64
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field

from src.api.routes.events import log_event
from src.api.services.email_sender import send_report
from src.api.services.pdf_report import (
    DEFAULT_RECOMMENDATIONS,
    DEFAULT_SCORES,
    ReportScore,
    render_report_pdf,
)
from src.config.societies import SOCIETY_BY_ID


router = APIRouter(prefix="/report", tags=["report"])


def _safe_filename(society_name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", society_name).strip("-").lower()
    return f"benchmark-{slug}-{date.today().isoformat()}.pdf"


def _pdf_for_society(society_id: str, region: Optional[str] = None) -> tuple[bytes, str, str]:
    """Render the PDF for a given society. Returns (pdf_bytes, filename, society_name).

    ``region`` is passed from the frontend (where the Society type has it);
    the backend config doesn't store it so we accept it as an override.
    """
    society = SOCIETY_BY_ID.get(society_id)
    if society is None:
        raise HTTPException(status_code=404, detail=f"Unknown society: {society_id}")

    try:
        pdf_bytes = render_report_pdf(
            society_name=society.canonical_name,
            society_region=region or "",
        )
    except RuntimeError as e:
        # WeasyPrint missing in the environment.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF render failed: {e}")

    filename = _safe_filename(society.canonical_name)
    return pdf_bytes, filename, society.canonical_name


@router.get("/pdf")
async def get_report_pdf(
    society_id: str = Query(...),
    region: str = Query(""),
    session_id: str = Query(""),
):
    """Download the benchmark PDF directly. Triggers a file download in the browser."""
    pdf_bytes, filename, society_name = _pdf_for_society(society_id, region)
    log_event(
        event_type="report_downloaded_pdf",
        session_id=session_id or None,
        building_society_id=society_id,
        props={"filename": filename, "society_name": society_name},
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class EmailReportRequest(BaseModel):
    society_id: str = Field(..., max_length=50)
    to_email: EmailStr
    region: Optional[str] = Field(None, max_length=80)
    session_id: Optional[str] = Field(None, max_length=64)


class EmailReportResponse(BaseModel):
    email_sent: bool
    error: Optional[str] = None
    pdf_base64: Optional[str] = None
    filename: str


@router.post("/email", response_model=EmailReportResponse)
async def email_report(req: EmailReportRequest) -> EmailReportResponse:
    """Generate the PDF and email it to the recipient.

    Always renders the PDF (so the caller can download it client-side as a
    fallback if the email send fails). Logs both the request and outcome.
    """
    pdf_bytes, filename, society_name = _pdf_for_society(req.society_id, req.region)

    log_event(
        event_type="report_email_requested",
        session_id=req.session_id,
        building_society_id=req.society_id,
        props={"to_email": req.to_email, "society_name": society_name},
    )

    subject = f"{society_name} — BSA Member Experience Benchmark"
    text_body = _text_body(society_name)
    html_body = _html_body(society_name)

    ok, err = send_report(
        to_email=req.to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    log_event(
        event_type="report_email_sent" if ok else "report_email_failed",
        session_id=req.session_id,
        building_society_id=req.society_id,
        props={"to_email": req.to_email, "error": err},
    )

    # Whether or not email succeeded, return the PDF so the frontend can fall
    # back to a direct download. This keeps the feature useful even without
    # email creds configured.
    return EmailReportResponse(
        email_sent=ok,
        error=err,
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        filename=filename,
    )


def _text_body(society_name: str) -> str:
    return (
        f"Hi,\n\n"
        f"Attached is the Woodhurst Member Experience Benchmark for {society_name}.\n\n"
        "It compares the society against 42 UK building societies across seven factors: "
        "customer service, digital experience, branch experience, mortgage products, "
        "savings rates, communication, and local community.\n\n"
        "Open bsa-member-chat.vercel.app to explore the underlying reviews interactively.\n\n"
        "— Woodhurst Consulting\n"
        "Data & Digital Advisory"
    )


def _html_body(society_name: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #0F1033; margin: 0; padding: 0; background: #FAFAFC;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: #FAFAFC;">
    <tr>
      <td align="center" style="padding: 32px 16px;">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width: 560px; background: #FFFFFF; border: 1px solid #E1E3EE; border-radius: 12px; overflow: hidden;">
          <tr>
            <td style="background: #1E205F; height: 8px;"></td>
          </tr>
          <tr>
            <td style="padding: 32px 36px 20px;">
              <div style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; color: #FF5773; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 14px;">
                Member Experience Benchmark
              </div>
              <h1 style="font-size: 26px; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 10px; color: #1E205F;">
                {society_name}
              </h1>
              <p style="font-size: 14px; line-height: 1.6; color: #3A3C6A; margin: 14px 0 0;">
                Here's your benchmark, attached as a PDF. It compares the society against 42 UK
                building societies across seven factors, with scores, industry average, rank, and
                recommended focus.
              </p>
              <p style="font-size: 14px; line-height: 1.6; color: #3A3C6A; margin: 14px 0 0;">
                Open the interactive dashboard to talk to a simulated member and explore the
                underlying reviews in real time.
              </p>
              <div style="margin: 24px 0 6px;">
                <a href="https://bsa-member-chat.vercel.app" style="display: inline-block; background: #1E205F; color: #FFFFFF; text-decoration: none; font-weight: 600; font-size: 13px; padding: 11px 20px; border-radius: 999px;">
                  Open the dashboard
                </a>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding: 18px 36px 26px; border-top: 1px solid #E1E3EE; font-size: 11px; color: #9B9DBA;">
              Woodhurst Consulting &middot; Data &amp; Digital Advisory &middot; Confidential
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
