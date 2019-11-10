from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

def two_hrs_later(start = None):
    if start == None:
        start = timezone.now()
    return start + timezone.timedelta(hours = 2)

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

def nlpParseTime(entityType, entity):
    if entityType == "datetime":

        if entity["type"] == "value":
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
        if entityType in entities:
            entity = entities[entityType][0]
            if entity["confidence"] > maxConf:
                mostLikelyEntityType = entityType
                mostLikelyEntity = entity
                maxConf = entity["confidence"]

    return mostLikelyEntityType, mostLikelyEntity
