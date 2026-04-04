from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reimbursement_profile",
    )
    vendor_id = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.vendor_id}"
