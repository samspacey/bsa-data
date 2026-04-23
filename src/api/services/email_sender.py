"""Email sender for the benchmark report.

Supports two backends:
1. **SMTP** (preferred) — stdlib ``smtplib``, no extra dep. Works with any
   SMTP server: Gmail app password, Outlook, SendGrid SMTP, etc.
2. **Resend** — if ``RESEND_API_KEY`` is set, falls through to the Resend
   HTTP API. Simpler to set up for users without an existing SMTP account.

Pick backend by setting env vars. If neither is configured, ``send_report``
returns ``(False, "email backend not configured")`` and the caller can fall
back to giving the user the PDF as a download.
"""

from __future__ import annotations

import base64
import mimetypes
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from src.config.settings import settings


def _smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def _resend_configured() -> bool:
    return bool(settings.resend_api_key)


def send_via_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> tuple[bool, Optional[str]]:
    if not _smtp_configured():
        return False, "SMTP not configured"

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to_email
        # Plain-text body comes first, HTML as the alternative. Mail clients
        # that support HTML will render that; others show the text body.
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        maintype, subtype = (mimetypes.guess_type(pdf_filename)[0] or "application/pdf").split("/", 1)
        msg.add_attachment(pdf_bytes, maintype=maintype, subtype=subtype, filename=pdf_filename)

        port = settings.smtp_port or 587
        if port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, port, timeout=20) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, port, timeout=20) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

        return True, None
    except Exception as e:  # noqa: BLE001
        return False, f"SMTP send failed: {type(e).__name__}: {e}"


def send_via_resend(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> tuple[bool, Optional[str]]:
    if not _resend_configured():
        return False, "Resend not configured"

    try:
        from_email = settings.resend_from_email or "onboarding@resend.dev"
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
                "attachments": [
                    {
                        "filename": pdf_filename,
                        "content": base64.b64encode(pdf_bytes).decode("ascii"),
                    }
                ],
            },
            timeout=20,
        )
        if resp.status_code >= 300:
            return False, f"Resend {resp.status_code}: {resp.text[:200]}"
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, f"Resend send failed: {type(e).__name__}: {e}"


def send_report(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> tuple[bool, Optional[str]]:
    """Try SMTP first, then Resend. Returns (success, error_message)."""
    if _smtp_configured():
        return send_via_smtp(to_email, subject, html_body, text_body, pdf_bytes, pdf_filename)
    if _resend_configured():
        return send_via_resend(to_email, subject, html_body, text_body, pdf_bytes, pdf_filename)
    return False, (
        "No email backend configured. Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD "
        "or RESEND_API_KEY to enable sending."
    )
