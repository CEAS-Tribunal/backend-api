"""
Management command: seed_expo_mock_data

Creates sample EXPO judges and student teams for local development and testing
of the judge assignment scheduler. Judges use "@mockjudge.example" emails and
teams are named "Mock Team NN", so they are easy to identify and clear.

Usage:
    python manage.py seed_expo_mock_data
    python manage.py seed_expo_mock_data --judges 40 --teams 50
    python manage.py seed_expo_mock_data --clear

Idempotent: skips any judge whose email or team whose name already exists.
Data is generated from a fixed seed, so reruns produce the same records.
"""

import random

from django.core.management.base import BaseCommand

from expo.models import (
    JudgeModel,
    JudgingTimeslots,
    LunchPreferences,
    ProjectCategories,
    StudentModel,
)

MOCK_EMAIL_DOMAIN = "mockjudge.example"
MOCK_TEAM_PREFIX = "Mock Team"

FIRST_NAMES = [
    "Avery", "Blake", "Casey", "Devon", "Emerson", "Finley", "Harper", "Jordan",
    "Kendall", "Logan", "Morgan", "Parker", "Quinn", "Reese", "Riley", "Rowan",
    "Sawyer", "Skyler", "Taylor", "Wren",
]
LAST_NAMES = [
    "Adler", "Brooks", "Carter", "Dalton", "Ellis", "Foster", "Grant", "Hayes",
    "Irving", "Jensen", "Keller", "Lowe", "Monroe", "Nash", "Osborne", "Pierce",
    "Reyes", "Sutton", "Turner", "Vaughn",
]
EMPLOYERS = [
    "Mock GE Aerospace", "Mock P&G", "Mock Kroger Tech", "Mock Fifth Third",
    "Mock Medpace", "Mock Siemens", "Mock Cintas", "Mock Mercy Health",
]
TEAM_WORDS = [
    "Aurora", "Bearcat", "Catalyst", "Delta", "Ember", "Flux", "Granite", "Helix",
    "Ion", "Jetstream", "Kinetic", "Lumen", "Momentum", "Nova", "Orbit", "Pulse",
    "Quantum", "Relay", "Summit", "Tensor", "Unity", "Vector", "Wave", "Zenith",
]

CATEGORY_KEYS = [key for key, _ in ProjectCategories]
SLOT_KEYS = [key for key, _ in JudgingTimeslots]
LUNCH_KEYS = [key for key, _ in LunchPreferences]


class Command(BaseCommand):
    help = "Seed mock EXPO judges and student teams for testing judge assignments."

    def add_arguments(self, parser):
        parser.add_argument("--judges", type=int, default=30, help="Number of judges (default 30).")
        parser.add_argument("--teams", type=int, default=35, help="Number of teams (default 35).")
        parser.add_argument(
            "--backup-ratio",
            type=float,
            default=0.15,
            help="Fraction of judges marked as backup (default 0.15).",
        )
        parser.add_argument("--seed", type=int, default=2026, help="Random seed (default 2026).")
        parser.add_argument(
            "--clear", action="store_true", help="Delete all mock EXPO judges and teams, then exit."
        )

    def handle(self, *args, **options):
        if options["clear"]:
            judges, _ = JudgeModel.objects.filter(email__endswith=f"@{MOCK_EMAIL_DOMAIN}").delete()
            teams, _ = StudentModel.objects.filter(team_name__startswith=MOCK_TEAM_PREFIX).delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {judges} mock judge rows and {teams} mock team rows."))
            return

        rng = random.Random(options["seed"])
        self.stdout.write("=== seed_expo_mock_data ===")

        team_created = 0
        for n in range(1, options["teams"] + 1):
            team_name = f"{MOCK_TEAM_PREFIX} {n:02d} {TEAM_WORDS[(n - 1) % len(TEAM_WORDS)]}"
            category = CATEGORY_KEYS[(n - 1) % len(CATEGORY_KEYS)]
            if StudentModel.objects.filter(team_name=team_name).exists():
                continue
            StudentModel.objects.create(
                team_name=team_name, team_category=category, booth_number=f"B{n:02d}"
            )
            team_created += 1
        self.stdout.write(f"Teams: {team_created} created.")

        backup_count = round(options["judges"] * options["backup_ratio"])
        judge_created = 0
        for n in range(1, options["judges"] + 1):
            first = FIRST_NAMES[(n - 1) % len(FIRST_NAMES)]
            last = LAST_NAMES[(n * 7) % len(LAST_NAMES)]
            email = f"{first.lower()}.{last.lower()}{n}@{MOCK_EMAIL_DOMAIN}"
            categories = rng.sample(CATEGORY_KEYS, rng.randint(2, 4))
            slots = sorted(rng.sample(SLOT_KEYS, rng.randint(4, 10)), key=int)
            attending_lunch = rng.random() < 0.6
            if JudgeModel.objects.filter(email=email).exists():
                continue
            JudgeModel.objects.create(
                first_name=first,
                last_name=f"Mock {last}",
                email=email,
                phone_number=f"+1513555{n:04d}",
                employer_name=rng.choice(EMPLOYERS),
                judging_category=categories,
                judging_timeslot=slots,
                number_of_projects=rng.randint(3, 6),
                is_backup_judge=n > options["judges"] - backup_count,
                is_attending_lunch=attending_lunch,
                lunch_preference=rng.choice(LUNCH_KEYS) if attending_lunch else None,
                dietary_restrictions=rng.choice(["", "", "", "Gluten-free", "Nut allergy"]) or None,
            )
            judge_created += 1
        self.stdout.write(f"Judges: {judge_created} created ({backup_count} backups in the full set).")

        self.stdout.write(self.style.SUCCESS("seed_expo_mock_data complete."))
