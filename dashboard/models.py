from django.db import models
import cuid



class ExecMember(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    name = models.CharField(max_length=30, null=False)
    email = models.EmailField(null=False)
    imgURL = models.URLField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name

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
        
        member_names = [member.name for member in members]
        if len(member_names) == 1:
            return f"{self.role} - {member_names[0]}"
        
        return f"{self.role} - {', '.join(member_names[:-1])} and {member_names[-1]}"

