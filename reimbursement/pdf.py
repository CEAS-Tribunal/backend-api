from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .models import ReimbursementRequest


@dataclass(frozen=True)
class FilledPdf:
    filename: str
    content: bytes


def _fmt_date(d: object) -> str:
    if isinstance(d, (datetime, date)):
        return d.strftime("%Y-%m-%d")
    if d is None:
        return ""
    return str(d)


def _fmt_money(v: object) -> str:
    if v is None:
        return ""
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)


def build_filled_reimbursement_pdf(req: ReimbursementRequest) -> FilledPdf | None:
    """
    Fill `reimbursement/assets/reimbursements_template.pdf` with request data.

    Notes:
    - "title in EAST" is the exec position (req.position).
    - Address is only populated for check reimbursements.
    """
    template_path = Path(__file__).resolve().parent / "assets" / "reimbursements_template.pdf"
    if not template_path.exists():
        return None

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)

    reimbursement_type = (req.reimbursement_type or "").strip().lower()
    is_check = reimbursement_type == "check"

    address_parts = [
        (req.reimbursement_address_line1 or "").strip(),
        (req.reimbursement_address_line2 or "").strip(),
        (req.reimbursement_address_city or "").strip(),
        (req.reimbursement_address_state or "").strip(),
        (req.reimbursement_address_zip or "").strip(),
    ]
    address = ", ".join([p for p in address_parts if p]) if is_check else ""

    fields: dict[str, str] = {
        "name": (req.name or "").strip(),
        "title": (req.position or "").strip(),
        "date_submitted": _fmt_date(getattr(req, "created_at", None) or datetime.now()),
        "m_number": (req.m_number or "").strip(),
        "expenditure_date": _fmt_date(req.date),
        "expenditure_vendor": (req.vendor_name or "").strip(),
        "expenditure_amount": _fmt_money(req.amount),
        "expenditure_description": (req.description or "").strip(),
        "vendor_id": (req.vendor_id or "").strip(),
        "address": address,
    }

    # Checkboxes: pypdf typically expects "/Yes" for checked. We'll set via raw values.
    checkbox_values: dict[str, str] = {
        "checkbox_budgeted_yes": "/Yes" if bool(req.budgeted) else "/Off",
        "checkbox_budgeted_no": "/Yes" if not bool(req.budgeted) else "/Off",
        "checkbox_payment_method_check": "/Yes" if is_check else "/Off",
        "checkbox_payment_method_dd": "/Yes" if not is_check else "/Off",
    }

    # If non-budgeted, try to populate approver fields if provided.
    if not bool(req.budgeted):
        if (req.non_budgeted_officer_name or "").strip():
            fields["approver_name"] = (req.non_budgeted_officer_name or "").strip()
        if (req.non_budgeted_officer_position or "").strip():
            fields["approver_position"] = (req.non_budgeted_officer_position or "").strip()

    # Flatten filled values into page content so PDF viewers (email clients,
    # browser preview, etc.) show text without requiring interactive form focus.
    if writer.pages:
        page0 = writer.pages[0]
        writer.update_page_form_field_values(
            page0,
            {**fields, **checkbox_values},
            auto_regenerate=False,
            flatten=True,
        )
        writer.remove_annotations(subtypes="/Widget")

    buf = BytesIO()
    writer.write(buf)
    out = buf.getvalue()
    return FilledPdf(filename=f"reimbursement_request_{req.id}.pdf", content=out)

