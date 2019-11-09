import datetime
import json
import requests
from django.db import models
from django.utils import timezone
from datetime import date
from .utils import two_hrs_later
from .tokens import FB_ACCESS_TOKEN


class Person(models.Model):
    name = models.CharField(max_length=25)
    facebook_id = models.CharField(max_length=100)
    state = models.CharField(max_length=25)
    last_state_change = models.DateTimeField(auto_now=True)



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
        return timezone.now() <= self.start_time <= timezone.now() + timezone.timedelta(hours=4)

    def overlaps(self, other) -> bool:
        return self.start_time < other.end_time and self.end_time > other.start_time
