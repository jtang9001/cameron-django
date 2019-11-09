import requests
import json
import re

from .models import Place, CheckIn, Person
from .tokens import FB_ACCESS_TOKEN

from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .utils import two_hrs_later

LOCATION_LOOKUP = ["whos in", "who is in"]
PERSON_LOOKUP = ["wheres", "where is"]
#CHECK_IN = [re.compile(r"(i will be |ill be |im |i am )?(in |at )?(?P<place>[a-z]+)")]
#CHECK_IN = ["i will be", "ill be", "im", "i am", "in ", "at ", "until ", "till ", "til "]

def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " ")

def isSubstringFor(string: str, arrOfSubstrings):
    for substr in arrOfSubstrings:
        if substr in string:
            return True
    return False

def reMatchesFor(string: str, patterns):
    for pattern in patterns:
        if pattern.search(string):
            return True
    return False

def removeSubstrings(string: str, arrOfSubstrings):
    for substr in arrOfSubstrings:
        string = string.replace(substr, "")
    return string.strip()

def sendForPlace(user, place):
    print(place)

    checkins = CheckIn.objects.filter(place = place)
    freshCheckIns = [checkin for checkin in checkins if checkin.is_fresh()]
    futureCheckIns = [checkin for checkin in checkins if checkin.is_future_fresh()]

    if len(freshCheckIns) > 0:
        user.send(f"Here's who's in {place.name}:")
        user.send("\n".join(checkin.prettyNoPlace() for checkin in freshCheckIns))

    if len(futureCheckIns) > 0:
        user.send(f"Here's who will be in {place.name}:")
        user.send("\n".join(checkin.prettyNoPlace() for checkin in futureCheckIns))

    elif len(freshCheckIns) == 0 and len(futureCheckIns) == 0:
        user.send(f"Nobody's checked into {place.name}.")
        user.state = "checking_in"

def sendForPerson(user, person):
    checkins = person.checkin_set.all()
    checkinStrs = [checkin.prettyNoName() for checkin in checkins
                    if checkin.is_fresh() or checkin.is_future_fresh()]

    if len(checkinStrs) > 0:
        user.send(f"Here's where {person.name} has checked in:")
        user.send("\n".join(checkinStrs))

    else:
        user.send(f"{person.name} isn't checked in anywhere :(")

def handleMessage(user: Person, inMsg, nlp):
    print(user.name)
    msg = cleanMsg(inMsg)
    print("IN:", msg)

    if isSubstringFor(msg, LOCATION_LOOKUP):
        location = removeSubstrings(msg, LOCATION_LOOKUP)
        place = Place.objects.filter(name__istartswith = location).first()

        if place is None:
            user.send("I don't know where you mean :(")

        else:
            sendForPlace(user, place)

    elif isSubstringFor(msg, PERSON_LOOKUP):
        name = removeSubstrings(msg, PERSON_LOOKUP)
        person = Person.objects.filter(name__istartswith = name).first()

        if person is None:
            user.send("I don't know who that is :(")

        else:
            sendForPerson(user, person)

    elif len(msg.split()) < 20:
        for word in msg.split():
            placeQ = Place.objects.filter(name__istartswith = word)
            personQ = Person.objects.filter(name__istartswith = word)

            if placeQ.exists():

                if "datetime" in nlp["entities"]:
                    if nlp["entities"]["datetime"][0]["type"] == "value":
                        newCheckIn = CheckIn(
                            person = user,
                            place = placeQ.first(),
                            start_time = parse_datetime(nlp["entities"]["datetime"][0]["value"]),
                            end_time = two_hrs_later(parse_datetime(nlp["entities"]["datetime"][0]["value"]))
                        )
                        newCheckIn.save()
                        user.ensureNoOverlapsWith(newCheckIn)
                    elif nlp["entities"]["datetime"][0]["type"] == "interval":
                        start_time = parse_datetime(nlp["entities"]["datetime"][0]["from"]["value"]) if "from" in nlp["entities"]["datetime"][0] else timezone.now()
                        if "to" in nlp["entities"]["datetime"][0]:
                            if nlp["entities"]["datetime"][0]["to"]["grain"] == "hour":
                                end_time = parse_datetime(nlp["entities"]["datetime"][0]["to"]["value"]) - timezone.timedelta(hours=1)
                            else:
                                end_time = parse_datetime(nlp["entities"]["datetime"][0]["to"]["value"])
                        else:
                            end_time = two_hrs_later(start_time)
                        newCheckIn = CheckIn(
                            person = user,
                            place = placeQ.first(),
                            start_time = start_time,
                            end_time = end_time
                        )
                        newCheckIn.save()
                        user.ensureNoOverlapsWith(newCheckIn)


                sendForPlace(user, placeQ.first())
                break

            elif personQ.exists():
                sendForPerson(user, personQ.first())
                break
        else:
            user.send(f"You said, '{inMsg}'. I don't understand, sorry!")

    else:
        user.send(f"You said, '{inMsg}'. I don't understand, sorry!")

def getNameFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    return response["first_name"]
