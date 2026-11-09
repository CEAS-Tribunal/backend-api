from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expo', '0003_judgemodel_has_checked_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentmodel',
            name='team_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studentmodel',
            name='team_category',
            field=models.CharField(choices=[('1', 'Human-Centered Research and Design'), ('2', 'Innovation, Creativity, and Entrepreneurship'), ('3', 'Interdisciplinary Collaboration'), ('4', 'Real-World Systems, Solutions, or Process Design'), ('5', 'Student Organization Project'), ('6', 'Sustainability and Environmental Responsibility'), ('7', 'Technical Excellence')], default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studentmodel',
            name='booth_number',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
