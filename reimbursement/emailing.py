from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import logging
import mimetypes

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from dashboard.models import ExecRole

from .models import ReimbursementRequest
from .pdf import build_filled_reimbursement_pdf

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass(frozen=True)
class TreasurerRecipient:
    name: str
    email: str


logger = logging.getLogger(__name__)


def _clean(s: str | None) -> str:
    return (s or "").strip()


def _truthy(s: str | None) -> bool:
    return bool(_clean(s))


def get_treasurer_recipients() -> list[TreasurerRecipient]:
    """
    Preferred: pull recipients from dashboard ExecRole('Treasurer').
    Fallback: settings.TREASURER_NOTIFICATION_EMAILS.
    """
    roles = (
        ExecRole.objects.filter(role__iexact="Treasurer")
        .prefetch_related("ExecMember__user")
        .all()
    )

    seen: set[str] = set()
    out: list[TreasurerRecipient] = []
    for role in roles:
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
            out.append(TreasurerRecipient(name=name or "Treasurer", email=email))
            seen.add(email)

    if out:
        return out

    for email in getattr(settings, "TREASURER_NOTIFICATION_EMAILS", []) or []:
        e = _clean(email)
        if e and e not in seen:
            out.append(TreasurerRecipient(name="Treasurer", email=e))
            seen.add(e)
    return out


def _request_details(req: ReimbursementRequest, request=None) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = []

    # Always-present core fields
    details.append(("Submitted by", _clean(req.name)))
    if _truthy(req.position):
        details.append(("Position", _clean(req.position)))
    if _truthy(req.email):
        details.append(("Submitter email", _clean(req.email)))
    if _truthy(req.m_number):
        details.append(("M Number", _clean(req.m_number)))
    if _truthy(req.vendor_id):
        details.append(("Vendor ID", _clean(req.vendor_id)))
    if req.date:
        try:
            details.append(("Date", req.date.strftime("%Y-%m-%d")))
        except Exception:
            # Defensive: tolerate non-date types created outside serializer/model validation.
            details.append(("Date", _clean(str(req.date))))
    if _truthy(req.vendor_name):
        details.append(("Vendor name", _clean(req.vendor_name)))
    if req.amount is not None:
        details.append(("Amount", f"${req.amount:.2f}"))
    if _truthy(req.description):
        details.append(("Description", _clean(req.description)))
    details.append(("Budgeted", "Yes" if bool(req.budgeted) else "No"))
    if _truthy(req.reimbursement_type):
        details.append(("Reimbursement type", _clean(req.reimbursement_type)))

    # Conditional sections
    if _clean(req.reimbursement_type).lower() == "check":
        if any(
            _truthy(x)
            for x in [
                req.reimbursement_address_line1,
                req.reimbursement_address_line2,
                req.reimbursement_address_city,
                req.reimbursement_address_state,
                req.reimbursement_address_zip,
            ]
        ):
            if _truthy(req.reimbursement_address_line1):
                details.append(("Mailing address line 1", _clean(req.reimbursement_address_line1)))
            if _truthy(req.reimbursement_address_line2):
                details.append(("Mailing address line 2", _clean(req.reimbursement_address_line2)))
            if _truthy(req.reimbursement_address_city):
                details.append(("Mailing address city", _clean(req.reimbursement_address_city)))
            if _truthy(req.reimbursement_address_state):
                details.append(("Mailing address state", _clean(req.reimbursement_address_state)))
            if _truthy(req.reimbursement_address_zip):
                details.append(("Mailing address ZIP", _clean(req.reimbursement_address_zip)))

    if not bool(req.budgeted):
        if _truthy(req.non_budgeted_officer_name):
            details.append(("Officer name (non-budgeted)", _clean(req.non_budgeted_officer_name)))
        if _truthy(req.non_budgeted_officer_position):
            details.append(
                ("Officer position (non-budgeted)", _clean(req.non_budgeted_officer_position))
            )

    if bool(req.ic_competition):
        details.append(("IC competition", "Yes"))
        if _truthy(req.ic_participant_name):
            details.append(("IC participant name", _clean(req.ic_participant_name)))
        if _truthy(req.ic_participant_role):
            details.append(("IC participant role", _clean(req.ic_participant_role)))
        if _truthy(req.ic_participant_email):
            details.append(("IC participant email", _clean(req.ic_participant_email)))

    return [(k, v) for (k, v) in details if _truthy(v)]


def _upload_leaf_name(filefield, fallback_filename: str) -> str:
    filename = _clean(getattr(filefield, "name", "")) or fallback_filename
    return filename.replace("\\", "/").split("/")[-1] or fallback_filename


def _attachments(req: ReimbursementRequest, request=None) -> list[dict[str, str]]:
    """
    Return uploaded document metadata for email rendering.
    Each entry is {label, url, filename}; url may be empty when only attached inline.
    """
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

    add("Itemized receipt", req.itemized_receipt, "receipt")
    add("Supporting document", req.supporting_document, "supporting-document")
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
            "Failed to attach uploaded reimbursement file",
            extra={"filename": getattr(filefield, "name", "")},
        )
        return False


def send_treasurer_reimbursement_request_created(
    req: ReimbursementRequest,
    *,
    request=None,
    recipients: Iterable[TreasurerRecipient] | None = None,
) -> int:
    recips = list(recipients) if recipients is not None else get_treasurer_recipients()
    if not recips:
        logger.warning("No treasurer recipients found; skipping email", extra={"reimbursement_request_id": req.id})
        return 0

    details = _request_details(req, request=request)
    attachments = _attachments(req, request=request)
    environ_condition = "DEV - " if settings.DEBUG else ""
    subject  = environ_condition + f"New reimbursement request: {req.name} (${req.amount:.2f})" if req.amount else f"New reimbursement request: {req.name}"

    sent = 0
    for treasurer in recips:
        try:
            ctx = {
                "treasurer_name": treasurer.name,
                "request_id": req.id,
                "details": details,
                "attachments": attachments,
            }
            text_body = render_to_string(
                "reimbursement/emails/treasurer_reimbursement_request_created.txt",
                ctx,
            )
            html_body = render_to_string(
                "reimbursement/emails/treasurer_reimbursement_request_created.html",
                ctx,
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@tribunal.uc.edu"),
                to=[treasurer.email],
            )
            msg.attach_alternative(html_body, "text/html")

            # Attach uploaded receipt/supporting docs and a filled-out PDF template.
            _attach_uploaded_file(msg, req.itemized_receipt, "receipt")
            _attach_uploaded_file(msg, req.supporting_document, "supporting-document")
            try:
                filled = build_filled_reimbursement_pdf(req)
                if filled is not None and filled.content:
                    msg.attach(filled.filename, filled.content, "application/pdf")
            except Exception:
                logger.exception(
                    "Failed to generate filled reimbursement PDF",
                    extra={"reimbursement_request_id": req.id},
                )

            sent_one = msg.send(fail_silently=True)
            sent += sent_one
            if sent_one != 1:
                logger.warning(
                    "Treasurer notification email not accepted by backend",
                    extra={"reimbursement_request_id": req.id, "to": treasurer.email, "sent": sent_one},
                )
        except Exception:
            logger.exception(
                "Treasurer notification email errored",
                extra={"reimbursement_request_id": req.id, "to": treasurer.email},
            )

    return sent

