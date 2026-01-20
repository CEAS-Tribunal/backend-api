from django.db import models

class Representative(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    company = models.CharField(max_length=100)
    title = models.CharField(max_length=30)
    email = models.EmailField()
    booth_location = models.CharField(max_length=250)
    building_location = models.CharField(max_length=250)

    def __str__(self):
        return f"{self.name} - {self.company}"
    