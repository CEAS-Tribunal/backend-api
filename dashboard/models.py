from django.db import models
import cuid
from django.contrib.auth.models import User

class ExecMember(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    imgURL = models.URLField(null=True, blank=True)
    must_change_password = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.user.get_full_name()

class ExecRole(models.Model):
    COMMITTEE_CHOICES = [
        ("pres", "President"), 
        ("cos", "Chief of Staff"), 
        ("vpe", "Events Committees"),
        ("vpca", "Collegiate Affairs Committees")
    ] 

    id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=50)
    description = models.TextField(null=False)
    ExecMember = models.ManyToManyField(ExecMember)
    committee = models.CharField(max_length=50, choices=COMMITTEE_CHOICES)

    def __str__(self) -> str:
        members = self.ExecMember.all()
        if not members:
            return self.role
        
        member_names = [str(member) for member in members]
        if len(member_names) == 1:
            return f"{self.role} - {member_names[0]}"
        
        return f"{self.role} - {', '.join(member_names[:-1])} and {member_names[-1]}"

