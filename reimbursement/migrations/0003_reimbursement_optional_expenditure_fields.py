# Generated manually for optional receipt-derived / admin-editable fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reimbursement", "0002_reimbursementrequest_userprofile_m_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reimbursementrequest",
            name="date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="reimbursementrequest",
            name="vendor_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="reimbursementrequest",
            name="amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="reimbursementrequest",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
