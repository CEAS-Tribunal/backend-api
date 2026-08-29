from collections import defaultdict

from django.db import migrations


def dedupe_and_normalize_student_emails(apps, schema_editor):
    Student = apps.get_model("ResumeReviewDay", "Student")

    by_email: dict[str, list[str]] = defaultdict(list)
    for student in Student.objects.all().only("id", "email"):
        email = (student.email or "").strip().lower()
        if not email:
            continue
        by_email[email].append(student.id)

    duplicate_ids: list[str] = []
    for email, ids in by_email.items():
        if len(ids) <= 1:
            if ids and Student.objects.filter(pk=ids[0]).exclude(email=email).exists():
                Student.objects.filter(pk=ids[0]).update(email=email)
            continue
        duplicate_ids.extend(ids[1:])
        Student.objects.filter(pk=ids[0]).update(email=email)

    if duplicate_ids:
        Student.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ResumeReviewDay", "0013_resumereviewsettings"),
    ]

    operations = [
        migrations.RunPython(dedupe_and_normalize_student_emails, migrations.RunPython.noop),
    ]
