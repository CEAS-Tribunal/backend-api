from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("innovation", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="judge",
            name="room",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
    ]
