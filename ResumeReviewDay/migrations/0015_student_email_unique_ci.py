from django.db import migrations
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("ResumeReviewDay", "0014_dedupe_student_emails"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="student",
            constraint=UniqueConstraint(
                Lower("email"),
                name="resumereviewday_student_email_unique_ci",
            ),
        ),
    ]
