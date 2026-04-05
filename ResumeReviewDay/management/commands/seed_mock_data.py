"""
Management command: seed_mock_data

Creates clearly-named sample data for local development and testing.
All records are prefixed with "Mock" so they are easy to identify and clear.

Usage:
    python manage.py seed_mock_data

Idempotent: skips creation of any record whose name already exists.
Does NOT touch real exec/user data — only ResumeReviewDay and career_fair models.
"""

import datetime

from django.core.management.base import BaseCommand

from ResumeReviewDay.models import Employer, Student, Timeslot
from career_fair.models import Representative


EMPLOYERS = [
    {
        "full_name": "Mock Alice Chen",
        "company_name": "Mock Acme Corp",
        "email": "alice@mockacme.example",
        "phone_number": "+15135550101",
        "diet_restriction": "",
        "start_time": datetime.time(9, 0),
        "end_time": datetime.time(11, 0),
        "max_resumes": 6,
        "uc_alumni": True,
        "selected_majors": ["cs", "compe"],
    },
    {
        "full_name": "Mock Brian Torres",
        "company_name": "Mock Nexus Labs",
        "email": "brian@mocknexus.example",
        "phone_number": "+15135550102",
        "diet_restriction": "Vegetarian",
        "start_time": datetime.time(10, 0),
        "end_time": datetime.time(12, 0),
        "max_resumes": 6,
        "uc_alumni": False,
        "selected_majors": ["elec", "mech", "aero"],
    },
    {
        "full_name": "Mock Carla Nguyen",
        "company_name": "Mock BioStride",
        "email": "carla@mockbiostride.example",
        "phone_number": "+15135550103",
        "diet_restriction": "",
        "start_time": datetime.time(11, 0),
        "end_time": datetime.time(13, 0),
        "max_resumes": 6,
        "uc_alumni": True,
        "selected_majors": ["bmes", "chem"],
    },
    {
        "full_name": "Mock David Park",
        "company_name": "Mock StructureCo",
        "email": "david@mockstructure.example",
        "phone_number": "+15135550104",
        "diet_restriction": "",
        "start_time": datetime.time(12, 0),
        "end_time": datetime.time(14, 0),
        "max_resumes": 6,
        "uc_alumni": False,
        "selected_majors": ["civil", "const", "ise"],
    },
    {
        "full_name": "Mock Elena Ross",
        "company_name": "Mock CyberShield",
        "email": "elena@mockcyber.example",
        "phone_number": "+15135550105",
        "diet_restriction": "Gluten-free",
        "start_time": datetime.time(13, 0),
        "end_time": datetime.time(15, 0),
        "max_resumes": 6,
        "uc_alumni": True,
        "selected_majors": ["cyber", "cs"],
    },
]

STUDENTS = [
    ("Mock Student One",   "mock1@uc.example", 2026, "cs"),
    ("Mock Student Two",   "mock2@uc.example", 2025, "elec"),
    ("Mock Student Three", "mock3@uc.example", 2027, "mech"),
    ("Mock Student Four",  "mock4@uc.example", 2026, "bmes"),
    ("Mock Student Five",  "mock5@uc.example", 2025, "civil"),
    ("Mock Student Six",   "mock6@uc.example", 2026, "compe"),
    ("Mock Student Seven", "mock7@uc.example", 2027, "aero"),
    ("Mock Student Eight", "mock8@uc.example", 2025, "ise"),
    ("Mock Student Nine",  "mock9@uc.example", 2026, "cyber"),
    ("Mock Student Ten",   "mock10@uc.example", 2027, "chem"),
]

REPRESENTATIVES = [
    {
        "name": "Mock Rep Alpha",
        "company": "Mock AlphaTech",
        "title": "Technical Recruiter",
        "email": "alpha@mockalpha.example",
        "booth_location": "A01",
        "building_location": "rec-center",
    },
    {
        "name": "Mock Rep Beta",
        "company": "Mock BetaSystems",
        "title": "University Relations",
        "email": "beta@mockbeta.example",
        "booth_location": "B12",
        "building_location": "tuc-great-hall",
    },
    {
        "name": "Mock Rep Gamma",
        "company": "Mock GammaSolutions",
        "title": "Engineering Lead",
        "email": "gamma@mockgamma.example",
        "booth_location": "C03",
        "building_location": "rec-center",
    },
    {
        "name": "Mock Rep Delta",
        "company": "Mock DeltaCorp",
        "title": "Recruiter",
        "email": "delta@mockdelta.example",
        "booth_location": "D07",
        "building_location": "tuc-great-hall",
    },
    {
        "name": "Mock Rep Epsilon",
        "company": "Mock EpsilonGroup",
        "title": "Campus Relations",
        "email": "epsilon@mockepsilon.example",
        "booth_location": "E15",
        "building_location": "rec-center",
    },
]


class Command(BaseCommand):
    help = (
        "Seed development mock data for ResumeReviewDay and career_fair. "
        "Idempotent — skips records that already exist. "
        "Does NOT modify exec/user/dashboard data."
    )

    def _create_employer_slots(self, employer):
        """Create 20-minute timeslots for an employer's time window."""
        start = datetime.datetime.combine(datetime.date.today(), employer.start_time)
        end = datetime.datetime.combine(datetime.date.today(), employer.end_time)
        total_min = int((end - start).total_seconds() / 60)
        count = total_min // 20
        slots = []
        for i in range(count):
            t = (start + datetime.timedelta(minutes=20 * i)).time()
            slots.append(Timeslot(employer=employer, timeslot=t))
        Timeslot.objects.bulk_create(slots)
        return len(slots)

    def handle(self, *args, **options):
        self.stdout.write("=== seed_mock_data ===")

        # ── Employers + Timeslots ──────────────────────────────────────────
        emp_created = 0
        employer_objects = []
        for spec in EMPLOYERS:
            if Employer.objects.filter(full_name=spec["full_name"]).exists():
                self.stdout.write(f"  [skip] Employer already exists: {spec['full_name']}")
                employer_objects.append(
                    Employer.objects.get(full_name=spec["full_name"])
                )
                continue
            emp = Employer.objects.create(**spec)
            slot_count = self._create_employer_slots(emp)
            employer_objects.append(emp)
            emp_created += 1
            self.stdout.write(
                f"  [+] Employer: {emp.full_name} ({emp.company_name}) — {slot_count} slots"
            )

        self.stdout.write(f"Employers: {emp_created} created, {len(EMPLOYERS) - emp_created} skipped.")

        # ── Students ──────────────────────────────────────────────────────
        stu_created = 0
        student_objects = []
        for full_name, email, grad_year, major in STUDENTS:
            if Student.objects.filter(full_name=full_name).exists():
                self.stdout.write(f"  [skip] Student already exists: {full_name}")
                student_objects.append(Student.objects.get(full_name=full_name))
                continue
            # Create without an actual file — resume field uses blank=False but
            # FileField accepts an empty string in the DB for test/seed purposes.
            stu = Student(
                full_name=full_name,
                email=email,
                grad_year=grad_year,
                major=major,
            )
            stu.resume.name = ""  # intentionally blank for mock data
            stu.save()
            student_objects.append(stu)
            stu_created += 1
            self.stdout.write(f"  [+] Student: {full_name}")

        self.stdout.write(f"Students: {stu_created} created, {len(STUDENTS) - stu_created} skipped.")

        # ── Assign students to available slots (one slot per student) ─────
        assigned = 0
        for student in student_objects:
            already = Timeslot.objects.filter(student=student).exists()
            if already:
                continue
            slot = Timeslot.objects.filter(student__isnull=True).first()
            if slot:
                slot.student = student
                slot.save()
                assigned += 1

        self.stdout.write(f"Assigned {assigned} student(s) to timeslots.")

        # ── Career Fair Representatives ────────────────────────────────────
        rep_created = 0
        for spec in REPRESENTATIVES:
            if Representative.objects.filter(name=spec["name"]).exists():
                self.stdout.write(f"  [skip] Representative already exists: {spec['name']}")
                continue
            Representative.objects.create(**spec)
            rep_created += 1
            self.stdout.write(f"  [+] Representative: {spec['name']} ({spec['company']})")

        self.stdout.write(
            f"Representatives: {rep_created} created, {len(REPRESENTATIVES) - rep_created} skipped."
        )

        self.stdout.write(self.style.SUCCESS("seed_mock_data complete."))
