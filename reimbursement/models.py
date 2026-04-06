from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reimbursement_profile",
    )
    vendor_id = models.CharField(max_length=255, unique=True)
    m_number = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.vendor_id}"

class ReimbursementRequest(models.Model):
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    m_number = models.CharField(max_length=255)
    vendor_id = models.CharField(max_length=255)
    date = models.DateField(blank=True, null=True)
    vendor_name = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, default="")
    budgeted = models.BooleanField(default=False)
    reimbursement_type = models.CharField(max_length=255)
    itemized_receipt = models.FileField(upload_to='itemized_receipts/', null=True, blank=True)
    supporting_document = models.FileField(upload_to='supporting_documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} - {self.amount}"
