import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import ExecMember


class Command(BaseCommand):
    help = (
        "Create a Django User (staff) and linked ExecMember with must_change_password=True. "
        "Initial password is read from TRIBUNAL_INITIAL_PASSWORD (never printed or logged)."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="6+2 or exec username")
        parser.add_argument(
            "--email",
            type=str,
            default="",
            help="User email (optional)",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Also set is_superuser (full Django admin permissions for User model)",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        if not username:
            raise CommandError("username is required")

        raw = os.environ.get("TRIBUNAL_INITIAL_PASSWORD")
        if not raw:
            raise CommandError(
                "Set TRIBUNAL_INITIAL_PASSWORD in the environment to the bootstrap password "
                "(do not commit this value)."
            )

        email = (options["email"] or "").strip()

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User already exists: {username}")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=raw,
        )
        user.is_staff = True
        if options["superuser"]:
            user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])

        ExecMember.objects.create(user=user, must_change_password=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created staff user and ExecMember for {username}. "
                "Password was set from TRIBUNAL_INITIAL_PASSWORD (not shown)."
            )
        )
