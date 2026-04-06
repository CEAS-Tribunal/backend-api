import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


def _exclude_usernames_from_env() -> set[str]:
    raw = (os.environ.get("TRIBUNAL_PASSWORD_RESET_EXCLUDE_USERNAMES") or "").strip()
    return {x.strip() for x in raw.split(",") if x.strip()}


class Command(BaseCommand):
    help = (
        "Set password from TRIBUNAL_RESET_PASSWORD for every user with is_superuser=False. "
        "Superuser accounts are unchanged. Optionally set "
        "TRIBUNAL_PASSWORD_RESET_EXCLUDE_USERNAMES to a comma-separated list of usernames "
        "to skip (e.g. staff who must keep their current password but are not superusers)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected users without changing passwords.",
        )

    def handle(self, *args, **options):
        raw = os.environ.get("TRIBUNAL_RESET_PASSWORD")
        if not raw:
            raise CommandError(
                "Set TRIBUNAL_RESET_PASSWORD in the environment to the new password "
                "(do not commit this value)."
            )

        exclude = _exclude_usernames_from_env()
        qs = User.objects.filter(is_superuser=False).order_by("pk")
        if exclude:
            qs = qs.exclude(username__in=exclude)
        if options["dry_run"]:
            count = qs.count()
            self.stdout.write(
                self.style.WARNING(f"Dry run: would reset {count} user(s) (non-superusers).")
            )
            if exclude:
                self.stdout.write(f"  Excluding usernames: {sorted(exclude)!r}")
            for u in qs.iterator():
                self.stdout.write(f"  pk={u.pk} username={u.username!r} staff={u.is_staff}")
            return

        updated = 0
        for u in qs.iterator():
            u.set_password(raw)
            u.save(update_fields=["password"])
            updated += 1
            self.stdout.write(f"Reset password for pk={u.pk} username={u.username!r}")

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} user(s)."))
