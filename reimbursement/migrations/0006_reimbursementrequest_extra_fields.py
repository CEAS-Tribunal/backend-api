# Generated manually for reimbursement extra fields (address, IC, officer, vendor optional).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reimbursement", "0005_reimbursementrequest_filed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reimbursementrequest",
            name="vendor_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="reimbursement_address_line1",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="reimbursement_address_line2",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="reimbursement_address_city",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="reimbursement_address_state",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="reimbursement_address_zip",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="non_budgeted_officer_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="non_budgeted_officer_position",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="ic_competition",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="ic_participant_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="ic_participant_role",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reimbursementrequest",
            name="ic_participant_email",
            field=models.EmailField(blank=True, default="", max_length=255),
        ),
    ]

