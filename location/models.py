import datetime
from django.db import models
from django.utils import timezone
from datetime import date

class Place(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class CheckIn(models.Model):
    person = models.CharField(max_length=50)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    time = models.TimeField(default=timezone.now)
    scratched = models.BooleanField(default=False)

    def __str__(self):
        return "{} at {} at {}".format(self.person, self.place, self.time)

    def is_fresh(self):
        return self.date == date.today() and self.time - timezone.now() < timezone.timedelta(hours = 2)
