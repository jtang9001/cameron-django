from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Person

def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " ")

def two_hrs_later(start = None):
    if start == None:
        start = timezone.now()
    return start + timezone.timedelta(hours = 2)

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

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

def getOrCreatePersonByName(name):
    name = cleanMsg(name)
    if Person.objects.filter(name__istartswith = name).exists():
        return Person.objects.filter(name__istartswith = name).first()
    elif Person.objects.filter(nicknames__icontains = name).exists():
        return Person.objects.filter(nicknames__icontains = name).first()
    else:
        person = Person(name = name)
        person.save()
        return Person

def getPersonByName(name):
    name = cleanMsg(name)
    if Person.objects.filter(name__istartswith = name).exists():
        return Person.objects.filter(name__istartswith = name).first()
    elif Person.objects.filter(nicknames__icontains = name).exists():
        return Person.objects.filter(nicknames__icontains = name).first()
    else:
        return None