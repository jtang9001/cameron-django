import datetime
from django.db import models
from django.utils import timezone
from datetime import date
from .utils import two_hrs_later


class Person(models.Model):
    name = models.CharField(max_length=25)

    def getScore(self):
        try:
            totalDuration = timezone.timedelta(minutes=0)
            checkIns = list(self.checkin_set.all().order_by("start_time"))
            currentStart = checkIns[0].start_time
            currentEnd = checkIns[0].end_time
            for i in range(1, len(checkIns)):
                if checkIns[i].overlaps(checkIns[i-1]):
                    currentEnd = checkIns[i].end_time
                else:
                    totalDuration += (currentEnd - currentStart)
                    currentStart = checkIns[i].start_time
                    currentEnd = checkIns[i].end_time

            totalDuration += (currentEnd - currentStart)
            return int(round(totalDuration.total_seconds()/60))
        except Exception:
            return -1

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class Place(models.Model):
    name = models.CharField(max_length=25)
    color = models.CharField(
        max_length=25, 
        default="grey lighten-5"
    )
    photo = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class CheckIn(models.Model):
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=two_hrs_later)
    scratched = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.person} at {self.place}, {self.start_time} to {self.end_time}"

    def pretty(self):
        return f"{self.person}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def is_fresh(self):
        if self.end_time:
            return self.start_time <= timezone.now() <= self.end_time
        else:
            return timezone.now() - timezone.timedelta(hours=2) <= self.start_time <= timezone.now()

    def is_future_fresh(self):
        return timezone.now() <= self.start_time <= timezone.now() + timezone.timedelta(hours=4) 

    def overlaps(self, other) -> bool:
        return self.start_time < other.end_time and self.end_time > other.start_time
