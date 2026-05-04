# Generated manually for reimbursement filing status

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reimbursement", "0004_remove_userprofile_m_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="reimbursementrequest",
            name="filed",
            field=models.BooleanField(
                default=False,
                help_text="Treasurer: set when this reimbursement has been filed with the university.",
            ),
        ),
    ]
