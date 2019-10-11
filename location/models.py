import datetime
from django.db import models
from django.utils import timezone

class Place(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name

class CheckIn(models.Model):
    person = models.CharField(max_length=50)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "{} at {} at {}".format(self.person, self.place, self.time)

    def check_in_is_fresh(self):
        return self.time >= timezone.now() - timezone.timedelta(hours=2)
