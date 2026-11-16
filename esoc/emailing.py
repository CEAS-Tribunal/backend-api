from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from dashboard.models import ExecMember

from .models import EsocRequest

logger = logging.getLogger(__name__)


def _clean(s: str | None) -> str:
    return (s or "").strip()


def _truthy(s: str | None) -> bool:
    return bool(_clean(s))


def _esoc_notification_emails() -> list[str]:
    members = ExecMember.objects.select_related("user").prefetch_related("execrole_set")
    emails = []
    for member in members:
        roles = list(member.execrole_set.all())
        if len(roles) != 1 or _clean(roles[0].role).casefold() != "esoc chair":
            continue
        email = _clean(member.user.email)
        if email:
            emails.append(email)
    return list(dict.fromkeys(emails))


def _request_details(req: EsocRequest) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = [
        ("Organization", _clean(req.organization_name)),
        ("Requested by", _clean(req.requester_name)),
        ("Requester email", _clean(req.requester_email)),
        ("M Number", _clean(req.m_number)),
        ("Position", _clean(req.position)),
    ]
    if req.requested_amount is not None:
        details.append(("Requested amount", f"${req.requested_amount:.2f}"))
    if _truthy(req.purpose):
        details.append(("Purpose", _clean(req.purpose)))
    details.append(("Involves travel", "Yes" if req.involves_travel else "No"))
    if req.funding_date:
        details.append(("Requested date", req.funding_date.date.strftime("%Y-%m-%d")))

    for club in req.additional_clubs.all():
        club_name = _clean(club.name)
        for person in club.contacts.all():
            name = _clean(person.name)
            email = _clean(person.email)
            role = _clean(person.role)
            if not name and not email:
                continue
            value = name
            if role:
                value = f"{value} ({role})"
            if email:
                value = f"{value} — {email}"
            details.append((club_name or "Additional club", value))

    return [(k, v) for (k, v) in details if _truthy(v)]


def _upload_leaf_name(filefield, fallback_filename: str) -> str:
    filename = _clean(getattr(filefield, "name", "")) or fallback_filename
    return filename.replace("\\", "/").split("/")[-1] or fallback_filename


def _attachments(req: EsocRequest, request=None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    def add(label: str, filefield, fallback_filename: str):
        if not filefield:
            return
        url = ""
        try:
            url = filefield.url
            if request is not None:
                url = request.build_absolute_uri(url)
        except Exception:
            url = ""
        out.append(
            {
                "label": label,
                "url": url,
                "filename": _upload_leaf_name(filefield, fallback_filename),
            }
        )

    add("W-9", req.w9, "w9")
    add("Funding application", req.application, "application")
    add("Presentation slides", req.slides, "slides")
    add("Travel authorization", req.travel_authorization, "travel-authorization")
    return out


def _attach_uploaded_file(msg: EmailMultiAlternatives, filefield, fallback_filename: str) -> bool:
    if not filefield:
        return False
    try:
        with filefield.open("rb") as fh:
            content = fh.read()
        if not content:
            return False
        filename = _upload_leaf_name(filefield, fallback_filename)
        content_type, _ = mimetypes.guess_type(filename)
        msg.attach(filename, content, content_type or "application/octet-stream")
        return True
    except Exception:
        logger.exception(
            "Failed to attach uploaded ESOC file",
            extra={"filename": getattr(filefield, "name", "")},
        )
        return False


def send_esoc_request_created(
    req: EsocRequest,
    *,
    request=None,
) -> int:
    recipients = _esoc_notification_emails()
    if not recipients:
        logger.warning(
            "No ESOC Chair recipients found for notification email",
            extra={"esoc_request_id": req.id},
        )
        return 0

    details = _request_details(req)
    attachments = _attachments(req, request=request)
    environ_condition = "DEV - " if settings.DEBUG else ""
    subject = environ_condition + f"New ESOC request: {req.organization_name}"

    sent = 0
    try:
        ctx = {
            "recipient_name": "CEAS ESOC",
            "request_id": req.id,
            "organization_name": req.organization_name,
            "details": details,
            "attachments": attachments,
        }
        text_body = render_to_string(
            "esoc/emails/esoc_request_created.txt", ctx
        )
        html_body = render_to_string(
            "esoc/emails/esoc_request_created.html", ctx
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@tribunal.uc.edu"),
            to=recipients,
        )
        msg.attach_alternative(html_body, "text/html")

        _attach_uploaded_file(msg, req.w9, "w9")
        _attach_uploaded_file(msg, req.application, "application")
        _attach_uploaded_file(msg, req.slides, "slides")
        _attach_uploaded_file(msg, req.travel_authorization, "travel-authorization")

        sent_one = msg.send(fail_silently=False)
        sent += sent_one
        if sent_one != 1:
            logger.warning(
                "ESOC notification email not accepted by backend",
                extra={"esoc_request_id": req.id, "to": recipients},
            )
    except Exception:
        logger.exception(
            "ESOC notification email errored",
            extra={"esoc_request_id": req.id, "to": recipients},
        )

    return sent
