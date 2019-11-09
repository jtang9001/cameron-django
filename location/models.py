import datetime
import json
import requests
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date
from .utils import two_hrs_later, is_later_than_now
from .tokens import FB_ACCESS_TOKEN


class Person(models.Model):
    name = models.CharField(max_length=25)
    facebook_id = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=25, null=True, blank=True)
    last_state_change = models.DateTimeField(auto_now=True, null=True, blank=True)

    def ensureNoOverlapsWith(self, newCheckIn):
        for checkIn in self.checkin_set.all():
            if timezone.now() - checkIn.end_time > timezone.timedelta(weeks=4):
                checkIn.delete()
            if checkIn == newCheckIn:
                continue
            if checkIn.overlaps(newCheckIn):
                checkIn.end_time = timezone.now()
                try:
                    checkIn.clean()
                except ValidationError as e:
                    print(e)
                    print(checkIn)
                    checkIn.delete()
                checkIn.scratched = True
                checkIn.save()

    def send(self, outMsg, msgType = "RESPONSE"):
        print("OUT:", outMsg)
        endpoint = f"https://graph.facebook.com/v5.0/me/messages?access_token={FB_ACCESS_TOKEN}"
        response_msg = json.dumps(
            {
                "messaging_type": msgType,
                "recipient": {"id": self.facebook_id},
                "message": {"text": outMsg}
            }
        )
        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg)
        print(status.json())

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

    def hasFreshCheckIns(self):
        return any(checkin.is_fresh() for checkin in self.checkin_set.all())
    
    def hasFutureCheckIns(self):
        return any(checkin.is_future_fresh() for checkin in self.checkin_set.all())

    def hasRelevantCheckIns(self):
        return self.hasFreshCheckIns() or self.hasFutureCheckIns()

    class Meta:
        ordering = ['name']

class CheckIn(models.Model):
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=two_hrs_later)
    scratched = models.BooleanField(default=False)

    def __str__(self):
        localStart = timezone.localtime(self.start_time)
        localEnd = timezone.localtime(self.end_time)
        return f"{self.person} at {self.place}, {localStart} to {localEnd}"

    def prettyNoPlace(self):
        localStart = timezone.localtime(self.start_time)
        localEnd = timezone.localtime(self.end_time)
        return f"{self.person}: {localStart.strftime('%H:%M')} - {localEnd.strftime('%H:%M')}"

    def prettyNoName(self):
        localStart = timezone.localtime(self.start_time)
        localEnd = timezone.localtime(self.end_time)
        return f"{self.place}: {localStart.strftime('%H:%M')} - {localEnd.strftime('%H:%M')}"

    def is_fresh(self):
        if self.end_time: #should always be in this branch since end_time is now mandatory.
            return self.start_time <= timezone.now() <= self.end_time
        else:
            return timezone.now() - timezone.timedelta(hours=2) <= self.start_time <= timezone.now()

    def is_future_fresh(self):
        return timezone.now() <= self.start_time <= timezone.now() + timezone.timedelta(hours=8) and self.start_time < self.end_time

    def overlaps(self, other) -> bool:
        return self.start_time < other.end_time and self.end_time > other.start_time

    def clean(self):
        is_later_than_now(self.start_time)
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be strictly later than start time")
        if self.end_time - self.start_time > timezone.timedelta(hours=12):    
            raise ValidationError("Check in duration is too long")
        if self.start_time - timezone.now() > timezone.timedelta(hours=18):
            raise ValidationError("Start date is too far in the future")
