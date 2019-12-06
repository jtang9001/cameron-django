import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " ")

def two_hrs_later(start = None):
    if start == None:
        start = timezone.now()
    return start + timezone.timedelta(hours = 2)

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

def next_rounded_time(start = None, delta = timezone.timedelta(minutes=30)):
    if start == None:
        start = timezone.now()

    rounded = start + (datetime.datetime.min - start) % delta
    if rounded - timezone.now() < timezone.timedelta(minutes=15):
        rounded += timezone.timedelta(minutes=30)
    return rounded

def nlpParseTime(user, entityType, entity):
    if entityType == "datetime":

        if entity["type"] == "value":
            user.send("💡 Since I didn't recognize an end time, I'll check you in for two hours. "
                "You can overwrite this checkin by saying something like 'Cam till 5' or 'Cam from 5 to 7'.")
            start_time = parse_datetime(entity["value"])
            end_time = two_hrs_later(start_time)

        elif entity["type"] == "interval":
            start_time = parse_datetime(entity["from"]["value"]) if "from" in entity else timezone.now()

            if "to" in entity:
                if entity["to"]["grain"] == "hour" and "from" in entity:
                    end_time = parse_datetime(entity["to"]["value"]) - timezone.timedelta(hours=1)
                else:
                    end_time = parse_datetime(entity["to"]["value"])
            else:
                user.send("💡 Since I didn't recognize an end time, I'll check you in for two hours. "
                    "You can overwrite this checkin by saying something like 'Cam till 5' or 'Cam from 5 to 7'.")
                end_time = two_hrs_later(start_time)

        return start_time, end_time

    elif entityType == "duration":
        start_time = timezone.now()
        duration = timezone.timedelta(seconds=entity["normalized"]["value"])
        return start_time, start_time + duration

def getBestEntityFromSubset(entities, subset):
    maxConf = 0
    mostLikelyEntityType = None
    mostLikelyEntity = None

    for entityType in subset:
        print(entityType)
        if entityType in entities:
            entity = entities[entityType][0]
            if entity["confidence"] > maxConf:
                mostLikelyEntityType = entityType
                mostLikelyEntity = entity
                maxConf = entity["confidence"]

    return mostLikelyEntityType, mostLikelyEntity
