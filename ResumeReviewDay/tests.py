import datetime
import io

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Employer, ResumeReviewSettings, Student, Timeslot
from .views import StudentViewSet


def _make_employer(**overrides):
    """Create a minimal Employer with 20-minute slots from 9:00–11:00 (6 slots)."""
    defaults = {
        "full_name": "Jane Smith",
        "company_name": "TechCorp",
        "email": "jane@techcorp.test",
        "start_time": datetime.time(9, 0),
        "end_time": datetime.time(11, 0),
        "max_resumes": 10,
        "uc_alumni": False,
        "selected_majors": ["cs", "elec"],
    }
    defaults.update(overrides)
    emp = Employer.objects.create(**defaults)
    _create_slots(emp)
    return emp


def _create_slots(employer):
    """Create 20-min timeslots for an employer's window."""
    start = datetime.datetime.combine(datetime.date.today(), employer.start_time)
    end = datetime.datetime.combine(datetime.date.today(), employer.end_time)
    total_min = int((end - start).total_seconds() / 60)
    for i in range(total_min // 20):
        Timeslot.objects.create(
            employer=employer,
            timeslot=(start + datetime.timedelta(minutes=20 * i)).time(),
        )


def _make_student(**overrides):
    defaults = {
        "full_name": "Alice Brown",
        "email": "alice@uc.test",
        "grad_year": 2026,
        "major": "cs",
    }
    defaults.update(overrides)
    stu = Student(**defaults)
    stu.resume.name = ""
    stu.save()
    return stu


def _fake_pdf():
    """Return a tiny in-memory file that simulates a resume upload."""
    content = b"%PDF-1.4 mock resume content"
    return io.BytesIO(content)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class EmployerViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    # ── POST ──────────────────────────────────────────────────────────────

    def test_post_creates_employer_and_slots(self):
        payload = {
            "full_name": "Bob Jones",
            "company_name": "RocketCo",
            "email": "bob@rocket.test",
            "phone_number": "+15135550199",
            "diet_restriction": "",
            "start_time": "09:00",
            "end_time": "11:00",
            "max_resumes": 6,
            "uc_alumni": False,
            "selected_majors": ["cs", "elec"],
        }
        r = self.client.post("/api/resume-review-day/employer/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Employer.objects.count(), 1)
        self.assertIn("id", r.data)
        # 2-hour window → 6 slots
        emp = Employer.objects.first()
        self.assertEqual(Timeslot.objects.filter(employer=emp).count(), 6)

    def test_post_without_max_resumes_defaults_to_slot_count(self):
        payload = {
            "full_name": "No Max Field",
            "company_name": "SlotCo",
            "email": "nomax@slotco.test",
            "phone_number": "+15135550198",
            "diet_restriction": "",
            "start_time": "09:00",
            "end_time": "11:00",
            "uc_alumni": False,
            "selected_majors": ["cs"],
        }
        r = self.client.post("/api/resume-review-day/employer/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        emp = Employer.objects.get(email="nomax@slotco.test")
        # 2-hour window → 6 twenty-minute slots
        self.assertEqual(emp.max_resumes, 6)

    def test_post_missing_required_field_returns_400(self):
        payload = {
            "full_name": "No Company",
            "email": "x@x.test",
            "start_time": "09:00",
            "end_time": "10:00",
            "max_resumes": 3,
            "uc_alumni": False,
            "selected_majors": ["cs"],
            # 'company_name' intentionally omitted → view raises on company_name being None
        }
        r = self.client.post("/api/resume-review-day/employer/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_invalid_time_format_returns_400(self):
        payload = {
            "full_name": "Bad Time",
            "company_name": "X Corp",
            "email": "bad@x.test",
            "start_time": "not-a-time",
            "end_time": "11:00",
            "max_resumes": 3,
            "uc_alumni": False,
            "selected_majors": ["cs"],
        }
        r = self.client.post("/api/resume-review-day/employer/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── GET ───────────────────────────────────────────────────────────────

    def test_get_employer_list_is_public(self):
        _make_employer()
        r = self.client.get("/api/resume-review-day/employer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.data
        self.assertEqual(len(data), 1)
        item = data[0]
        self.assertIn("id", item)
        self.assertIn("full_name", item)
        self.assertIn("company_name", item)
        self.assertIn("selected_majors", item)
        self.assertIn("available_slots", item)

    def test_get_available_slots_decrements_when_student_assigned(self):
        emp = _make_employer()
        slot = Timeslot.objects.filter(employer=emp).first()
        stu = _make_student()
        slot.student = stu
        slot.save()

        r = self.client.get("/api/resume-review-day/employer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        item = r.data[0]
        # 6 total slots, 1 assigned → 5 available
        self.assertEqual(item["available_slots"], 5)

    def test_get_selected_majors_returns_human_readable_labels(self):
        _make_employer(selected_majors=["cs", "mech"])
        r = self.client.get("/api/resume-review-day/employer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        majors = r.data[0]["selected_majors"]
        self.assertIn("Computer Science", majors)
        self.assertIn("Mechanical Engineering", majors)

    def test_get_returns_empty_list_when_no_employers(self):
        r = self.client.get("/api/resume-review-day/employer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, [])


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    MEDIA_ROOT="/tmp/tribunal_test_media",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class StudentViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employer = _make_employer()

    def test_post_registers_student_and_assigns_slots(self):
        slot_ids = list(
            Timeslot.objects.filter(employer=self.employer)
            .values_list("id", flat=True)[:2]
        )
        payload = {
            "full_name": "Carl Lee",
            "email": "carl@uc.test",
            "grad_year": "2025",
            "major": "cs",
            "timeslots": ",".join(slot_ids),
        }
        from django.core.files.uploadedfile import SimpleUploadedFile
        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 mock", content_type="application/pdf")

        r = self.client.post(
            "/api/resume-review-day/student/",
            {**payload, "resume": resume},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Student.objects.count(), 1)
        self.assertIn("student_id", r.data)
        self.assertIn("assigned_timeslots", r.data)
        self.assertEqual(len(r.data["assigned_timeslots"]), 2)
        for sid in slot_ids:
            self.assertIsNotNone(Timeslot.objects.get(id=sid).student)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["carl@uc.test"])
        self.assertIn("Resume Review Day registration confirmed", msg.subject)
        body = msg.alternatives[0][0] if msg.alternatives else msg.body
        self.assertIn("Carl Lee", body)
        self.assertIn("TechCorp", body)
        self.assertIn("Jane Smith", body)

    def test_post_rejects_duplicate_email(self):
        _make_student(email="carl@uc.test")

        slot_ids = list(
            Timeslot.objects.filter(employer=self.employer)
            .values_list("id", flat=True)[:1]
        )
        from django.core.files.uploadedfile import SimpleUploadedFile

        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r = self.client.post(
            "/api/resume-review-day/student/",
            {
                "full_name": "Carl Lee",
                "email": "carl@uc.test",
                "grad_year": "2025",
                "major": "cs",
                "timeslots": ",".join(slot_ids),
                "resume": resume,
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["detail"], StudentViewSet._DUPLICATE_EMAIL_MESSAGE)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_rejects_duplicate_email_case_insensitive(self):
        _make_student(email="carl@uc.test")

        slot_ids = list(
            Timeslot.objects.filter(employer=self.employer)
            .values_list("id", flat=True)[:1]
        )
        from django.core.files.uploadedfile import SimpleUploadedFile

        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r = self.client.post(
            "/api/resume-review-day/student/",
            {
                "full_name": "Carl Lee",
                "email": "Carl@UC.TEST",
                "grad_year": "2025",
                "major": "cs",
                "timeslots": ",".join(slot_ids),
                "resume": resume,
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Student.objects.count(), 1)

    def test_post_ignores_already_taken_slots_gracefully(self):
        """A slot already taken is skipped; the student is still created."""
        stu_a = _make_student(full_name="Existing A", email="a@uc.test")
        slot = Timeslot.objects.filter(employer=self.employer).first()
        slot.student = stu_a
        slot.save()

        from django.core.files.uploadedfile import SimpleUploadedFile
        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r = self.client.post(
            "/api/resume-review-day/student/",
            {
                "full_name": "New Student",
                "email": "new@uc.test",
                "grad_year": "2026",
                "major": "elec",
                "timeslots": slot.id,  # already taken
                "resume": resume,
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        # Slot should still belong to stu_a
        slot.refresh_from_db()
        self.assertEqual(slot.student, stu_a)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@uc.test"])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class EmployerViewSetEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_employer_registration_does_not_send_email(self):
        payload = {
            "full_name": "Bob Jones",
            "company_name": "RocketCo",
            "email": "bob@rocket.test",
            "phone_number": "+15135550199",
            "diet_restriction": "",
            "start_time": "09:00",
            "end_time": "11:00",
            "max_resumes": 6,
            "uc_alumni": False,
            "selected_majors": ["cs", "elec"],
        }
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            r = self.client.post("/api/resume-review-day/employer/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class TimeslotViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.emp_cs = _make_employer(
            full_name="CS Employer",
            company_name="CS Corp",
            email="cs@corp.test",
            selected_majors=["cs"],
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),  # 3 slots
        )
        self.emp_mech = _make_employer(
            full_name="Mech Employer",
            company_name="Mech Co",
            email="mech@co.test",
            selected_majors=["mech"],
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),  # 3 slots starting 10:00
        )

    def test_get_all_available_slots(self):
        r = self.client.get("/api/resume-review-day/timeslots/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # Both employers have open slots
        employer_ids = {item["id"] for item in r.data}
        self.assertIn(self.emp_cs.id, employer_ids)
        self.assertIn(self.emp_mech.id, employer_ids)

    def test_filter_by_major_returns_only_matching_employers(self):
        r = self.client.get("/api/resume-review-day/timeslots/?major=cs")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in r.data}
        self.assertIn(self.emp_cs.id, ids)
        self.assertNotIn(self.emp_mech.id, ids)

    def test_filter_by_time_returns_only_matching_slots(self):
        # Only request slots starting at 10:00 AM
        r = self.client.get("/api/resume-review-day/timeslots/?time=10:00 AM")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # emp_mech has a 10:00 AM slot; emp_cs does not
        ids = {item["id"] for item in r.data}
        self.assertIn(self.emp_mech.id, ids)
        self.assertNotIn(self.emp_cs.id, ids)

    def test_taken_slot_excluded_from_results(self):
        """A slot with a student assigned should not appear in available results."""
        stu = _make_student()
        slot = Timeslot.objects.filter(employer=self.emp_cs).first()
        # Assign student to ALL slots of emp_cs so it drops from results
        for s in Timeslot.objects.filter(employer=self.emp_cs):
            s.student = stu
            s.save()

        r = self.client.get("/api/resume-review-day/timeslots/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in r.data}
        self.assertNotIn(self.emp_cs.id, ids)

    def test_get_is_public_no_auth_needed(self):
        r = self.client.get("/api/resume-review-day/timeslots/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class AdminResumeRosterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="exec99", password="pass12345")
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

    def _auth(self, user=None):
        u = user or self.user
        token = RefreshToken.for_user(u)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    # ── Auth guard ────────────────────────────────────────────────────────

    def test_unauthenticated_returns_401(self):
        r = self.client.get("/api/resume-review-day/roster/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_forbidden(self):
        non_staff = User.objects.create_user(username="nostaff", password="pass12345")
        non_staff.is_staff = False
        non_staff.save(update_fields=["is_staff"])
        self._auth(non_staff)
        r = self.client.get("/api/resume-review-day/roster/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_returns_200(self):
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    # ── Response shape ────────────────────────────────────────────────────

    def test_roster_returns_employer_fields(self):
        emp = _make_employer()
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        item = r.data[0]
        for field in ("id", "full_name", "company_name", "email",
                      "selected_majors", "start_time", "end_time",
                      "max_resumes", "slots"):
            self.assertIn(field, item, msg=f"Missing field: {field}")
        self.assertEqual(item["id"], emp.id)

    def test_roster_slots_include_student_when_assigned(self):
        emp = _make_employer()
        stu = _make_student()
        slot = Timeslot.objects.filter(employer=emp).first()
        slot.student = stu
        slot.save()

        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        emp_data = r.data[0]
        assigned = [s for s in emp_data["slots"] if s["student"] is not None]
        self.assertEqual(len(assigned), 1)
        s_data = assigned[0]["student"]
        self.assertEqual(s_data["full_name"], stu.full_name)
        self.assertIn("email", s_data)
        self.assertIn("major", s_data)
        self.assertIn("grad_year", s_data)

    def test_roster_unassigned_slot_has_null_student(self):
        _make_employer()
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        emp_data = r.data[0]
        # All slots should be unassigned
        for slot in emp_data["slots"]:
            self.assertIsNone(slot["student"])

    def test_roster_slots_time_is_formatted_12h(self):
        _make_employer(start_time=datetime.time(9, 0), end_time=datetime.time(9, 20))
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        slot_time = r.data[0]["slots"][0]["time"]
        # Should be "9:00 AM", not "09:00:00" or similar raw format
        self.assertIn("AM", slot_time.upper())

    def test_roster_ordered_by_company_name(self):
        _make_employer(full_name="Z Person", company_name="Zebra Co", email="z@z.test")
        _make_employer(full_name="A Person", company_name="Alpha Co", email="a@a.test")
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        companies = [item["company_name"] for item in r.data]
        self.assertEqual(companies, sorted(companies))

    def test_roster_majors_are_human_readable(self):
        _make_employer(selected_majors=["cs", "mech"])
        self._auth()
        r = self.client.get("/api/resume-review-day/roster/")
        majors = r.data[0]["selected_majors"]
        self.assertIn("Computer Science", majors)
        self.assertNotIn("cs", majors)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ResumeReviewSettingsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="settings-admin", password="pass12345")
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

    def _auth(self):
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_settings_get_is_public(self):
        response = self.client.get("/api/resume-review-day/settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_settings_patch_requires_staff_authentication(self):
        response = self.client.patch(
            "/api/resume-review-day/settings/",
            {"student_page_open": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_read_and_update_settings(self):
        self._auth()
        response = self.client.get("/api/resume-review-day/settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["employer_page_open"], True)
        self.assertEqual(response.data["student_page_open"], True)

        response = self.client.patch(
            "/api/resume-review-day/settings/",
            {"student_page_open": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["student_page_open"])
        self.assertTrue(ResumeReviewSettings.current().student_page_open is False)

    def test_closed_pages_reject_public_requests(self):
        settings = ResumeReviewSettings.current()
        settings.employer_page_open = False
        settings.student_page_open = False
        settings.save(update_fields=["employer_page_open", "student_page_open"])

        self.assertEqual(
            self.client.get("/api/resume-review-day/employer/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get("/api/resume-review-day/timeslots/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
