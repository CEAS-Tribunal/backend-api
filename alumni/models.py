from django.db import models


class AlumniProfile(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=200)
    graduation_year = models.IntegerField()
    role_company = models.CharField(max_length=300)
    quote = models.TextField()
    image_url = models.URLField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return self.name