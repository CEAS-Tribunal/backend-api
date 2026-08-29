from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import MAJOR_CHOICES, Student, Timeslot

logger = logging.getLogger(__name__)

_MAJOR_LABEL = dict(MAJOR_CHOICES)


def _format_time_12h(t) -> str:
    if t is None:
        return ""
    if hasattr(t, "hour"):
        h, m = t.hour, t.minute
        return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    return str(t)


def _assigned_reviews(timeslots: list[Timeslot]) -> list[dict[str, str]]:
    reviews: list[dict[str, str]] = []
    for slot in sorted(timeslots, key=lambda s: s.timeslot):
        employer = slot.employer
        reviews.append(
            {
                "time": _format_time_12h(slot.timeslot),
                "company_name": employer.company_name,
                "employer_name": employer.full_name,
            }
        )
    return reviews


def send_student_resume_review_confirmation(
    student: Student,
    timeslots: list[Timeslot],
) -> int:
    """Email the student a confirmation after Resume Review Day registration."""
    email = (student.email or "").strip()
    if not email:
        logger.warning(
            "Skipping student resume review confirmation: no email",
            extra={"student_id": student.id},
        )
        return 0

    assigned_reviews = _assigned_reviews(timeslots)
    environ_condition = "DEV - " if settings.DEBUG else ""
    subject = environ_condition + "Resume Review Day registration confirmed"

    ctx = {
        "student_name": student.full_name,
        "major": _MAJOR_LABEL.get(student.major, student.major),
        "grad_year": student.grad_year,
        "assigned_reviews": assigned_reviews,
    }

    try:
        text_body = render_to_string(
            "resume_review_day/emails/student_registration_confirmation.txt",
            ctx,
        )
        html_body = render_to_string(
            "resume_review_day/emails/student_registration_confirmation.html",
            ctx,
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@tribunal.uc.edu"),
            to=[email],
        )
        msg.attach_alternative(html_body, "text/html")
        sent = msg.send(fail_silently=True)
        if sent != 1:
            logger.warning(
                "Student resume review confirmation email not accepted by backend",
                extra={"student_id": student.id, "to": email, "sent": sent},
            )
        return sent
    except Exception:
        logger.exception(
            "Student resume review confirmation email errored",
            extra={"student_id": student.id, "to": email},
        )
        return 0
