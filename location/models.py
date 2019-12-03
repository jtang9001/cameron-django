import json
import requests
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .utils import two_hrs_later, is_later_than_now, cleanMsg
from .tokens import FB_ACCESS_TOKEN

class Person(models.Model):
    name = models.CharField(max_length=25)
    facebook_id = models.CharField(max_length=100, null=True, blank=True)
    facebook_photo = models.URLField(blank=True, null=True, max_length=500)
    nicknames = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=25, null=True, blank=True)
    last_state_change = models.DateTimeField(auto_now=True, null=True, blank=True)

    def hasFreshCheckIns(self):
        for checkin in self.checkin_set.all():
            if checkin.is_fresh():
                return True
        return False

    def hasFutureCheckIns(self):
        for checkin in self.checkin_set.all():
            if checkin.is_future_fresh():
                return True
        return False

    def hasRelevantCheckIns(self):
        for checkin in self.checkin_set.all():
            if checkin.is_fresh() or checkin.is_future_fresh():
                return True
        return False

    def cleanCheckIns(self, newCheckIn, verbose = False):
        for checkIn in self.checkin_set.all():
            if timezone.now() - checkIn.end_time > timezone.timedelta(weeks=4):
                print(f"deleting old checkin (>4 weeks): {checkIn}")
                checkIn.delete()
            elif checkIn == newCheckIn:
                continue
            elif checkIn.touches(newCheckIn, assertActive = True):
                if checkIn.place == newCheckIn.place:
                    print(f"merging touching checkins: {checkIn} and {newCheckIn}")
                    if verbose:
                        self.send(f"Merging {self.name}'s check ins at {checkIn.prettyNoName()} "
                                    f"and {newCheckIn.prettyNoName()}.")
                    newCheckIn.start_time = min(newCheckIn.start_time, checkIn.start_time)
                    newCheckIn.end_time = max(newCheckIn.end_time, checkIn.end_time)
                    newCheckIn.clean()
                    newCheckIn.save()
                    checkIn.delete()
                else:
                    print("two checkins touching, letting it pass")
            elif checkIn.overlaps(newCheckIn):
                print(f"deleting overlapping checkin: {checkIn}")
                if verbose:
                    self.send(f"Checking {self.name} out from {checkIn.prettyNoName()} "
                            f"because this overlaps with {newCheckIn.prettyNoName()}.")
                checkIn.scratch()

    def send(self, outMsg, msgType = "RESPONSE", quick_replies = None):
        print("OUT:", outMsg)
        endpoint = f"https://graph.facebook.com/v5.0/me/messages?access_token={FB_ACCESS_TOKEN}"
        
        if quick_replies is None:
            msgDict = {"text": outMsg}
        else:
            msgDict = {
                "text": outMsg,
                "quick_replies": quick_replies.getList()
            }

        response_msg = json.dumps(
            {
                "messaging_type": msgType,
                "recipient": {"id": self.facebook_id},
                "message": msgDict
            }
        )

        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg
        )

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
    name = models.CharField(max_length=12)
    color = models.CharField(
        max_length=25,
        default="grey lighten-5"
    )
    photo = models.URLField(blank=True, null=True)
    aliases = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    def hasFreshCheckIns(self):
        for checkin in self.checkin_set.all():
            if checkin.is_fresh():
                return True
        return False

    def hasFutureCheckIns(self):
        for checkin in self.checkin_set.all():
            if checkin.is_future_fresh():
                return True
        return False

    def hasRelevantCheckIns(self):
        for checkin in self.checkin_set.all():
            print(checkin)
            if checkin.is_fresh() or checkin.is_future_fresh():
                return True
        return False

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
        if localStart <= timezone.now():
            return f"{self.person}: until {localEnd.strftime('%H:%M')}"
        else:
            return f"{self.person}: {localStart.strftime('%H:%M')} - {localEnd.strftime('%H:%M')}"

    def prettyNoName(self):
        localStart = timezone.localtime(self.start_time)
        localEnd = timezone.localtime(self.end_time)
        if localStart <= timezone.now():
            return f"{self.place}: until {localEnd.strftime('%H:%M')}"
        else:
            return f"{self.place}: {localStart.strftime('%H:%M')} - {localEnd.strftime('%H:%M')}"

    def prettyTime(self):
        localStart = timezone.localtime(self.start_time)
        localEnd = timezone.localtime(self.end_time)
        if localStart <= timezone.now():
            return f"Until {localEnd.strftime('%H:%M')}"
        else:
            return f"{localStart.strftime('%H:%M')} - {localEnd.strftime('%H:%M')}"

    def scratch(self):
        print(f"scratching {self}")
        self.scratched = True
        self.end_time = timezone.now()
        try:
            self.clean()
            self.save()
            print("successfully scratched")
        except ValidationError as e:
            print(f"Deleting a checkin with validation error: {self}")
            print(e.message)
            self.delete()
        except Exception as e:
            print(f"Deleting a checkin with general error: {self}")
            print(e)
            self.delete()

    def is_fresh(self):
        if self.end_time: #should always be in this branch since end_time is now mandatory.
            return self.start_time <= timezone.now() <= self.end_time and not self.scratched
        else:
            return timezone.now() - timezone.timedelta(hours=2) <= self.start_time <= timezone.now()

    def is_future_fresh(self):
        return (timezone.now() <= self.start_time <= timezone.now() + timezone.timedelta(hours=12)
                and self.start_time < self.end_time and not self.scratched)

    def overlaps(self, other) -> bool:
        return self.start_time < other.end_time and self.end_time > other.start_time

    def touches(self, other, assertActive = False) -> bool:
        if (self.scratched or other.scratched) and assertActive:
            return False

        minTimeGap = min(
            (self.end_time - other.start_time).total_seconds(),
            (other.end_time - self.start_time).total_seconds(),
            key = lambda x: abs(x))
        print("In checking if touches:", minTimeGap)
        return (
            self.place == other.place and
            abs( minTimeGap ) < 300
        )

    def clean(self):
        is_later_than_now(self.start_time)
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be strictly later than start time")
        if self.end_time - self.start_time > timezone.timedelta(hours=12):
            raise ValidationError("Check in duration is too long")
        if self.start_time - timezone.now() > timezone.timedelta(hours=18):
            raise ValidationError("Start date is too far in the future")


def getOrCreatePerson(name = None, fbid = None):
    if fbid is not None and Person.objects.filter(facebook_id__exact = fbid).exists():
        return Person.objects.get(facebook_id__exact = fbid)
    
    name = cleanMsg(name)
    if Person.objects.filter(name__istartswith = name).exists():
        return Person.objects.filter(name__istartswith = name).first()
    elif Person.objects.filter(nicknames__icontains = name).exists():
        return Person.objects.filter(nicknames__icontains = name).first()
    else:
        person = Person(name = name)
        person.save()
        return Person

def getPersonWithPossibleS(name: str):
    if name.endswith('s'):
        name = name[:-2]
    return Person.objects.filter(name__istartswith = name) | Person.objects.filter(nicknames__icontains = name)

