import cuid
from django.db import models


class Representative(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    name = models.CharField(max_length=250)
    company = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    email = models.EmailField()
    booth_location = models.CharField(max_length=250)
    building_location = models.CharField(max_length=250)
    signed_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_in_at"]

    def __str__(self) -> str:
        return f"{self.name} - {self.company}"
