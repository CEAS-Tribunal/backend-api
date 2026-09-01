import io
import logging
import re
import zipfile
from pathlib import Path

from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from dashboard.permissions import IsStaffUser

from .emailing import send_student_resume_review_confirmation
from .models import Employer, ResumeReviewSettings, Student, Timeslot, MAJOR_CHOICES

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
import pandas as pd

_MAJOR_LABEL = dict(MAJOR_CHOICES)


def _format_time_12h(t):
    """Format datetime.time as e.g. '9:00 AM' (cross-platform; avoids %-I in strftime)."""
    if t is None:
        return ""
    if hasattr(t, "hour"):
        h, m = t.hour, t.minute
        return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    return str(t)


class EmployerViewSet(APIView):
    permission_classes = [AllowAny]
    '''
        Adds an employer to the list of employers
    '''

    def get(self, request):
        """Public list of registered employers with available slot counts."""
        if not ResumeReviewSettings.current().employer_page_open:
            return Response({"detail": "Employer registration is closed."}, status=status.HTTP_404_NOT_FOUND)
        employers = Employer.objects.all().order_by("company_name")
        results = []
        for emp in employers:
            available = Timeslot.objects.filter(employer=emp, student__isnull=True).count()
            labels = [_MAJOR_LABEL.get(code, code) for code in emp.selected_majors]
            results.append(
                {
                    "id": emp.id,
                    "full_name": emp.full_name,
                    "company_name": emp.company_name,
                    "selected_majors": labels,
                    "available_slots": available,
                }
            )
        return Response(results, status=status.HTTP_200_OK)

    def post(self, request):
        if not ResumeReviewSettings.current().employer_page_open:
            return Response({"detail": "Employer registration is closed."}, status=status.HTTP_404_NOT_FOUND)
        try:
            full_name = request.data.get("full_name")
            company_name = request.data.get("company_name")
            email = request.data.get("email")
            phone_number = request.data.get("phone_number")
            diet_restriction = request.data.get("diet_restriction", "")
            start_time = request.data.get("start_time")  # Expecting 'HH:MM' string
            end_time = request.data.get("end_time")
            max_resumes_raw = request.data.get("max_resumes")
            uc_alumni = bool(request.data.get("uc_alumni"))
            selected_majors = request.data.get("selected_majors", [])

            # Parse times (optional: add error checking)
            start_time = datetime.strptime(start_time, "%H:%M").time()
            end_time = datetime.strptime(end_time, "%H:%M").time()
            
            today = datetime.today().date()
            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)

            # Get the interval in minutes
            total_minutes = int((end_dt - start_dt).total_seconds() / 60)
            interval_count = total_minutes // 20

            # Capacity label for admin roster; defaults to number of 20-min slots (capped at 100).
            if max_resumes_raw is None or max_resumes_raw == "":
                max_resumes = min(interval_count, 100) if interval_count > 0 else 100
            else:
                max_resumes = int(max_resumes_raw)

            employer = Employer.objects.create(
                full_name=full_name,
                company_name=company_name,
                email=email,
                phone_number=phone_number,
                diet_restriction=diet_restriction,
                start_time=start_time,
                end_time=end_time,
                max_resumes=max_resumes,
                uc_alumni=uc_alumni,
                selected_majors=selected_majors,
            )

            
            for i in range(interval_count):
               Timeslot.objects.create(
                    employer=employer,
                    timeslot=(start_dt + timedelta(minutes=(20 * i))).time()
               ) 

            return Response({'message': 'Employer and Timeslots created!', 'id': employer.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminResumeRosterView(APIView):
    """Staff-only roster of all RRD employers, timeslots, and assigned students."""

    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        employers = (
            Employer.objects.prefetch_related("timeslot_set", "timeslot_set__student")
            .all()
            .order_by("company_name")
        )
        results = []
        for emp in employers:
            slots = []
            for slot in emp.timeslot_set.all().order_by("timeslot"):
                student = slot.student
                slots.append(
                    {
                        "slot_id": slot.id,
                        "time": _format_time_12h(slot.timeslot),
                        "student": (
                            {
                                "id": student.id,
                                "full_name": student.full_name,
                                "email": student.email,
                                "major": _MAJOR_LABEL.get(student.major, student.major),
                                "grad_year": student.grad_year,
                            }
                            if student
                            else None
                        ),
                    }
                )
            results.append(
                {
                    "id": emp.id,
                    "full_name": emp.full_name,
                    "company_name": emp.company_name,
                    "email": emp.email,
                    "selected_majors": [_MAJOR_LABEL.get(c, c) for c in emp.selected_majors],
                    "start_time": _format_time_12h(emp.start_time),
                    "end_time": _format_time_12h(emp.end_time),
                    "max_resumes": emp.max_resumes,
                    "slots": slots,
                }
            )
        return Response(results, status=status.HTTP_200_OK)


def _safe_path_component(name: str, fallback: str = "Unknown") -> str:
    """Strip characters that are invalid in zip entry paths."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip())
    return (cleaned[:80] or fallback)


def _format_timeslot_for_filename(t) -> str:
    """Format a timeslot for use in a zip entry filename."""
    label = _format_time_12h(t).replace(":", "-").replace(" ", "_")
    return _safe_path_component(label, "Unknown_Time")


class AdminResumeDownloadView(APIView):
    """Staff-only zip of all assigned resumes, grouped by employer company name."""

    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            employers = (
                Employer.objects.prefetch_related("timeslot_set__student")
                .all()
                .order_by("company_name")
            )
            for emp in employers:
                folder = _safe_path_component(emp.company_name)
                used_names: dict[str, int] = {}

                for slot in (
                    emp.timeslot_set.filter(student__isnull=False)
                    .select_related("student")
                    .order_by("timeslot")
                ):
                    student = slot.student
                    if student is None:
                        continue

                    if not student.resume or not student.resume.name:
                        continue

                    ext = Path(student.resume.name).suffix or ".pdf"
                    timeslot_label = _format_timeslot_for_filename(slot.timeslot)
                    student_name = _safe_path_component(student.full_name, "Student")
                    base_name = f"{timeslot_label}_{student_name}"
                    count = used_names.get(base_name, 0)
                    used_names[base_name] = count + 1
                    file_name = base_name if count == 0 else f"{base_name}_{count + 1}"
                    arcname = f"{folder}/{file_name}{ext}"

                    try:
                        with student.resume.open("rb") as resume_file:
                            zf.writestr(arcname, resume_file.read())
                    except OSError:
                        logger.exception(
                            "Failed to read resume for zip download",
                            extra={"student_id": student.id, "employer_id": emp.id},
                        )

        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = (
            'attachment; filename="resume-review-day-resumes.zip"'
        )
        return response


class ResumeReviewSettingsView(APIView):
    """Staff-only read/update endpoint for public registration page availability."""

    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsStaffUser()]
        return [AllowAny()]

    def get(self, request):
        settings = ResumeReviewSettings.current()
        return Response(
            {
                "employer_page_open": settings.employer_page_open,
                "student_page_open": settings.student_page_open,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        settings = ResumeReviewSettings.current()
        update_fields = []
        for field in ("employer_page_open", "student_page_open"):
            if field in request.data:
                value = request.data[field]
                if not isinstance(value, bool):
                    return Response(
                        {field: "This field must be a boolean."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                setattr(settings, field, value)
                update_fields.append(field)

        if not update_fields:
            return Response(
                {"detail": "At least one page availability field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        settings.save(update_fields=update_fields)
        return self.get(request)


class StudentViewSet(APIView):
    permission_classes = [AllowAny]

    _DUPLICATE_EMAIL_MESSAGE = (
        "A student with this email is already registered for Resume Review Day."
    )

    def post(self, request):
        if not ResumeReviewSettings.current().student_page_open:
            return Response({"detail": "Student registration is closed."}, status=status.HTTP_404_NOT_FOUND)
        try:
            full_name = request.data.get("full_name")
            email = (request.data.get("email") or "").strip().lower()
            grad_year = int(request.data.get("grad_year"))
            major = request.data.get("major")
            resume = request.FILES.get("resume")
            timeslot_ids = request.data.get("timeslots", "")
            timeslot_ids = [t.strip() for t in timeslot_ids.split(",") if t.strip()]

            if not email:
                return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

            if Student.objects.filter(email__iexact=email).exists():
                return Response(
                    {"detail": self._DUPLICATE_EMAIL_MESSAGE},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                student = Student.objects.create(
                    full_name=full_name,
                    email=email,
                    grad_year=grad_year,
                    major=major,
                    resume=resume,
                )
            except IntegrityError:
                return Response(
                    {"detail": self._DUPLICATE_EMAIL_MESSAGE},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            assigned_timeslots = []
            updated_slots = []
            for slot_id in timeslot_ids:
                try:
                    timeslot = Timeslot.objects.select_related("employer").get(
                        id=slot_id, student__isnull=True
                    )  # only update if unassigned
                    timeslot.student = student
                    timeslot.save()
                    assigned_timeslots.append(timeslot)
                    updated_slots.append({'id': timeslot.id, 'timeslot': str(timeslot.timeslot)})
                except Timeslot.DoesNotExist:
                    continue 

            # Notify the student. Never block registration on email delivery.
            try:
                send_student_resume_review_confirmation(student, assigned_timeslots)
            except Exception:
                logger.exception(
                    "Student resume review confirmation email failed",
                    extra={"student_id": student.id},
                )

            result = {
                "message": "Student registered and timeslots assigned.",
                "student_id": student.id,
                "full_name": student.full_name,
                "assigned_timeslots": updated_slots,
            }
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
def _parse_time_string(s):
    """Parse '9:00 AM' or 'HH:MM' style string to time object."""
    from datetime import datetime
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _time_matches(t, allowed):
    """Compare time t to list of allowed times by hour/minute (avoids microsecond mismatch from DB)."""
    list_of_matches = []
    for a in allowed:
        if t.hour == a.hour and t.minute == a.minute:
            list_of_matches.append(True)

    return any(list_of_matches)


def _parse_time_params(time_params):
    """Parse query time strings into a list of time objects. Returns empty list if none valid."""
    return [t for t in (_parse_time_string(p) for p in time_params) if t is not None]


def _format_slot(timeslot_obj):
    """Format a Timeslot instance as API dict with id and formatted timeslot string."""
    ts = timeslot_obj.timeslot
    if hasattr(ts, "hour"):
        h, m = ts.hour, ts.minute
        time_str = f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    else:
        time_str = str(ts)
    return {"id": timeslot_obj.id, "timeslot": time_str}


def _slots_for_employer(employer_timeslots, times_filter):
    """Build list of slot dicts for an employer, optionally filtered by times_filter."""
    if times_filter:
        return [_format_slot(t) for t in employer_timeslots if _time_matches(t.timeslot, times_filter)]
    return [_format_slot(t) for t in employer_timeslots]


class TimeslotViewSet(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not ResumeReviewSettings.current().student_page_open:
            return Response({"detail": "Student registration is closed."}, status=status.HTTP_404_NOT_FOUND)
        major = request.query_params.get("major")
        time_params = request.query_params.getlist("time")
        times_filter = _parse_time_params(time_params)



        employers = Employer.objects.all()
        if major:
            employers = employers.filter(selected_majors__contains=major)
        
        results = []
        for employer in employers:
            employer_timeslots = Timeslot.objects.filter(employer=employer, student__isnull=True).all()
            slots = _slots_for_employer(employer_timeslots, times_filter) if employer_timeslots else []
            if slots:
                results.append({
                    "id": employer.id,
                    "full_name": employer.full_name,
                    "company_name": employer.company_name,
                    "timeslots": slots,
                })


        return Response(results, status=status.HTTP_200_OK)
