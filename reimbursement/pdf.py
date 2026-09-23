from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

from .models import ReimbursementRequest

_DESCRIPTION_FIELD = "expenditure_description"
# pypdf only wraps multiline text when /DA font size is 0 (autosize). The
# template locks the description at 12pt, so long values render as one clipped
# line. Autosize wraps to the description textbox and scales to stay inside it.
_DA_FONT_SIZE_RE = re.compile(r"(\S+)\s+[\d.]+\s+Tf")


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


def _wrap_description_in_textbox(page) -> None:
    annots = page.get("/Annots")
    if not annots:
        return
    for annot in annots:
        widget = annot.get_object()
        if str(widget.get("/T") or "") != _DESCRIPTION_FIELD:
            continue
        da = widget.get("/DA")
        if not da:
            return
        widget[NameObject("/DA")] = TextStringObject(
            _DA_FONT_SIZE_RE.sub(r"\1 0 Tf", str(da), count=1)
        )
        return


def build_filled_reimbursement_pdf(req: ReimbursementRequest) -> FilledPdf | None:
    """
    Fill `reimbursement/assets/template.pdf` with request data.

    Notes:
    - "title in EAST" is the exec position (req.position).
    - Name/title/email use IC participant fields when ic_competition is set.
    - Address is only populated for check reimbursements.
    """
    template_path = Path(__file__).resolve().parent / "assets" / "template.pdf"
    if not template_path.exists():
        return None

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)

    if req.ic_competition:
        name = req.ic_participant_name
        title = req.ic_participant_role
        email = (req.ic_participant_email or "").strip()
    else:
        name = req.name
        title = req.position
        email = (req.email or "").strip()

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
        "name": name,
        "title": title,
        "email": email,
        "date_top": _fmt_date(getattr(req, "created_at", None) or datetime.now()),
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

    # Keep widgets editable. Regenerate appearances so filled values show in
    # PDF readers without requiring field focus (email inline previews may
    # still look blank until the attachment is opened).
    if writer.pages:
        page0 = writer.pages[0]
        _wrap_description_in_textbox(page0)
        writer.update_page_form_field_values(
            page0,
            {**fields, **checkbox_values},
            auto_regenerate=True,
            flatten=False,
        )

    buf = BytesIO()
    writer.write(buf)
    out = buf.getvalue()
    return FilledPdf(filename=f"reimbursement_request_{req.id}.pdf", content=out)

