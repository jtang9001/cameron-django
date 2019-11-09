import requests
import json
import re

from .models import Place, CheckIn, Person
from .tokens import FB_ACCESS_TOKEN

LOCATION_LOOKUP = ["whos in", "who is in"]
PERSON_LOOKUP = ["wheres", "where is"]
CHECK_IN = [re.compile(r"check () into")]

def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " :")

def isSubstringFor(string: str, arrOfSubstrings):
    for substr in arrOfSubstrings:
        if substr in string:
            return True
    return False

def removeSubstrings(string: str, arrOfSubstrings):
    for substr in arrOfSubstrings:
        string = string.replace(substr, "")
    return string.strip()

def handleMessage(user: Person, inMsg):
    msg = cleanMsg(inMsg)
    print("IN:", msg)

    if isSubstringFor(msg, LOCATION_LOOKUP):
        location = removeSubstrings(msg, LOCATION_LOOKUP)
        place = Place.objects.filter(name__icontains = location).first()

        if place is None:
            user.send("I don't know where you mean :(")

        else:
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

    elif isSubstringFor(msg, PERSON_LOOKUP):
        name = removeSubstrings(msg, PERSON_LOOKUP)
        person = Person.objects.filter(name__icontains = name).first()

        if person is None:
            user.send("I don't know who that is :(")

        else:
            checkins = person.checkin_set.all()
            checkinStrs = [checkin.prettyNoName() for checkin in checkins
                            if checkin.is_fresh() or checkin.is_future_fresh()]

            if len(checkinStrs) > 0:
                user.send(f"Here's where {person.name} has checked in:")
                user.send("\n".join(checkinStrs))

            else:
                user.send(f"{person.name} isn't checked in anywhere :(")


    else:
        user.send(f"You said, '{inMsg}'. I don't understand, sorry!")

def getNameFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    return response["first_name"]
