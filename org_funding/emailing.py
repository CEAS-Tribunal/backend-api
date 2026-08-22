from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from dashboard.models import ExecRole

from .models import OrgFundingRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recipient:
    name: str
    email: str


def _clean(s: str | None) -> str:
    return (s or "").strip()


def _truthy(s: str | None) -> bool:
    return bool(_clean(s))


def _is_org_funding_role(role_name: str | None) -> bool:
    name = _clean(role_name).lower()
    return "funding" in name and ("org" in name or "organization" in name)


def get_org_funding_recipients() -> list[Recipient]:
    """
    Notify the Org Funding chair(s) from dashboard ExecRole, plus any addresses in
    settings.ORG_FUNDING_NOTIFICATION_EMAILS (e.g. the overseeing officer). Deduped.
    """
    seen: set[str] = set()
    out: list[Recipient] = []

    roles = ExecRole.objects.prefetch_related("ExecMember__user").all()
    for role in roles:
        if not _is_org_funding_role(role.role):
            continue
        for em in role.ExecMember.all():
            user = getattr(em, "user", None)
            if not user:
                continue
            email = _clean(getattr(user, "email", ""))
            if not email or email in seen:
                continue
            name = _clean(getattr(user, "get_full_name", lambda: "")()) or _clean(
                getattr(user, "username", "")
            )
            out.append(Recipient(name=name or "Org Funding chair", email=email))
            seen.add(email)

    for email in getattr(settings, "ORG_FUNDING_NOTIFICATION_EMAILS", []) or []:
        e = _clean(email)
        if e and e not in seen:
            out.append(Recipient(name="Org Funding", email=e))
            seen.add(e)

    return out


def _request_details(req: OrgFundingRequest) -> list[tuple[str, str]]:
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

    for contact in req.additional_contacts or []:
        name = _clean(contact.get("name"))
        email = _clean(contact.get("email"))
        position = _clean(contact.get("position"))
        if not name and not email:
            continue
        label = "Also included"
        value = name
        if position:
            value = f"{value} ({position})"
        if email:
            value = f"{value} — {email}"
        details.append((label, value))

    return [(k, v) for (k, v) in details if _truthy(v)]


def _upload_leaf_name(filefield, fallback_filename: str) -> str:
    filename = _clean(getattr(filefield, "name", "")) or fallback_filename
    return filename.replace("\\", "/").split("/")[-1] or fallback_filename


def _attachments(req: OrgFundingRequest, request=None) -> list[dict[str, str]]:
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
            "Failed to attach uploaded org funding file",
            extra={"filename": getattr(filefield, "name", "")},
        )
        return False


def send_org_funding_request_created(
    req: OrgFundingRequest,
    *,
    request=None,
    recipients: Iterable[Recipient] | None = None,
) -> int:
    recips = list(recipients) if recipients is not None else get_org_funding_recipients()
    if not recips:
        logger.warning(
            "No org funding recipients found; skipping email",
            extra={"org_funding_request_id": req.id},
        )
        return 0

    details = _request_details(req)
    attachments = _attachments(req, request=request)
    environ_condition = "DEV - " if settings.DEBUG else ""
    subject = environ_condition + f"New org funding request: {req.organization_name}"

    sent = 0
    for recipient in recips:
        try:
            ctx = {
                "recipient_name": recipient.name,
                "request_id": req.id,
                "organization_name": req.organization_name,
                "details": details,
                "attachments": attachments,
            }
            text_body = render_to_string(
                "org_funding/emails/org_funding_request_created.txt", ctx
            )
            html_body = render_to_string(
                "org_funding/emails/org_funding_request_created.html", ctx
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@tribunal.uc.edu"),
                to=[recipient.email],
            )
            msg.attach_alternative(html_body, "text/html")

            _attach_uploaded_file(msg, req.w9, "w9")
            _attach_uploaded_file(msg, req.application, "application")
            _attach_uploaded_file(msg, req.slides, "slides")
            _attach_uploaded_file(msg, req.travel_authorization, "travel-authorization")

            sent_one = msg.send(fail_silently=True)
            sent += sent_one
            if sent_one != 1:
                logger.warning(
                    "Org funding notification email not accepted by backend",
                    extra={"org_funding_request_id": req.id, "to": recipient.email},
                )
        except Exception:
            logger.exception(
                "Org funding notification email errored",
                extra={"org_funding_request_id": req.id, "to": recipient.email},
            )

    return sent
