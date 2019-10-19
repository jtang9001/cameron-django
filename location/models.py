import datetime
from django.db import models
from django.utils import timezone
from datetime import date

def two_hrs_later():
    return timezone.now() + timezone.timedelta(hours = 2)

class Place(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class CheckIn(models.Model):
    person = models.CharField(max_length=50)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=two_hrs_later)
    scratched = models.BooleanField(default=False)

    def __str__(self):
        return "{} at {}".format(self.person, self.place)

    def is_fresh(self):
        return self.start_time <= timezone.now() <= self.end_time

    def is_future_fresh(self):
        return timezone.now() <= self.start_time <= timezone.now() + timezone.timedelta(hours=4) 
