from django.db import models


class OrgFundingDate(models.Model):
    """
    A funding window/date the chair opens for organizations to request or present against.
    Open dates are surfaced on the public funding form.
    """

    date = models.DateField()
    label = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional cap on how many requests may select this date.",
    )
    is_open = models.BooleanField(
        default=True,
        help_text="When off, the date is hidden from the public form but kept for records.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "id")

    def __str__(self) -> str:
        label = f" — {self.label}" if self.label else ""
        return f"{self.date.isoformat()}{label}"


class OrgFundingRequest(models.Model):
    """A single organization funding request submitted from the public form."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        FUNDED = "funded", "Funded"

    # Requester / organization
    organization_name = models.CharField(max_length=255)
    requester_name = models.CharField(max_length=255)
    requester_email = models.EmailField(max_length=255)
    m_number = models.CharField(max_length=255)
    position = models.CharField(max_length=255)

    # Request details
    requested_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    purpose = models.TextField(blank=True, default="")
    involves_travel = models.BooleanField(default=False)
    funding_date = models.ForeignKey(
        OrgFundingDate,
        on_delete=models.SET_NULL,
        related_name="requests",
        null=True,
        blank=True,
    )
    # List of {"name": str, "email": str, "position": str} for extra people to include.
    additional_contacts = models.JSONField(default=list, blank=True)

    # Uploaded documents
    w9 = models.FileField(upload_to="org_funding/w9/", null=True, blank=True)
    application = models.FileField(
        upload_to="org_funding/applications/", null=True, blank=True
    )
    slides = models.FileField(upload_to="org_funding/slides/", null=True, blank=True)
    travel_authorization = models.FileField(
        upload_to="org_funding/travel_auth/", null=True, blank=True
    )

    # Chair review state
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    checklist_w9 = models.BooleanField(default=False)
    checklist_application = models.BooleanField(default=False)
    checklist_slides = models.BooleanField(default=False)
    checklist_travel_authorization = models.BooleanField(default=False)
    chair_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.organization_name} — {self.requester_name}"
