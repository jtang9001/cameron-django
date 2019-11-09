import requests
import json
import random

from .models import Place, CheckIn, Person
from .tokens import FB_ACCESS_TOKEN

from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from .utils import two_hrs_later, nlpParseTime

LOCATION_LOOKUP = ["whos in", "who is in", "who in", "who"]
PERSON_LOOKUP = ["wheres", "where is", "where"]
SHORT_WORD_EXCEPTIONS = ["ed"]
CHECK_OUT = ["wont", "not", "leaving", "leave", "out", "bounce", "bouncing"]
FIRST_PERSON = ["i", "me", "im"]
#CHECK_IN = [re.compile(r"(i will be |ill be |im |i am )?(in |at )?(?P<place>[a-z]+)")]
#CHECK_IN = ["i will be", "ill be", "im", "i am", "in ", "at ", "until ", "till ", "til "]

DIALOG = {
    "unsure_place": [
        "I don't know where that is :(", 
        "Not sure where that is :(", 
        "I don't know where you mean :("
    ],
    "unsure_person": [
        "Who's that now?",
        "Not sure who that is :(",
        "Never heard of them.",
        "I don't know who that is :("
    ],
    "incomprehension": [
        "Not sure what you mean :(",
        "What's that now?",
        "I don't understand :(",
        "Kindly try rephrasing?"
    ]
}

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

def sendForPerson(user, person):
    checkins = person.checkin_set.all()
    checkinStrs = [checkin.prettyNoName() for checkin in checkins
                    if checkin.is_fresh() or checkin.is_future_fresh()]

    if len(checkinStrs) > 0:
        user.send(f"Here's where {person.name} has checked in:")
        user.send("\n".join(checkinStrs))

    else:
        user.send(f"{person.name} isn't checked in anywhere :(")

def sendIncomprehension(user, origMsg):
    user.send(f"You said, '{origMsg}'. {random.choice(DIALOG['incomprehension'])}")

def handleMessage(user: Person, inMsg, nlp):
    msg = cleanMsg(inMsg)
    print(f"{user.name} IN:", msg)

    if isSubstringFor(msg, LOCATION_LOOKUP):
        location = removeSubstrings(msg, LOCATION_LOOKUP)
        place = Place.objects.filter(name__istartswith = location).first()

        if place is None:
            user.send(random.choice(DIALOG["unsure_place"]))

        else:
            sendForPlace(user, place)

    elif isSubstringFor(msg, PERSON_LOOKUP):
        name = removeSubstrings(msg, PERSON_LOOKUP)
        person = Person.objects.filter(name__istartswith = name).first()

        if "every" in msg:
            for place in Place.objects.all():
                if place.hasRelevantCheckIns():
                    sendForPlace(user, place)

        elif person is None:
            user.send(random.choice(DIALOG["unsure_person"]))

        else:
            sendForPerson(user, person)

    if len(msg.split()) < 30:
        refdPlaces = set()
        refdPeople = set()
        checkOut = False

        for word in msg.split():
            # if len(word) <= 2 and word not in SHORT_WORD_EXCEPTIONS:
            #     continue

            if word in CHECK_OUT:
                checkOut = True
                continue

            if word in FIRST_PERSON:
                refdPeople.add(user)

            placeQ = Place.objects.filter(name__istartswith = word)
            personQ = Person.objects.filter(name__istartswith = word)

            if placeQ.exists():
                refdPlaces.add(placeQ.first())
                
            elif personQ.exists():
                refdPeople.add(personQ.first())


        if len(refdPlaces) > 1:
            user.send(f"Too many places ({', '.join(refdPlaces)}) were referenced in your message.")
            return

        elif len(refdPlaces) == 0:
            if len(refdPeople) == 0:
                if checkOut:
                    checkIns = CheckIn.objects.filter(person = user)
                    for checkin in checkIns:
                        if checkin.is_fresh():
                            checkin.scratch()
                else:
                    sendIncomprehension(user, inMsg)
            else:
                for person in refdPeople:
                    sendForPerson(user, person)

        elif len(refdPlaces) == 1:
            place = refdPlaces.pop()

            if len(refdPeople) == 0:
                refdPeople.add(user)

            if checkOut:
                for person in refdPeople:
                    checkIns = CheckIn.objects.filter(person = person, place = place)
                    for checkin in checkIns:
                        if person == user and checkin.is_future_fresh():
                            checkin.scratch()
                        elif checkin.is_fresh():
                            checkin.scratch()

            else:
                if "datetime" in nlp["entities"]:
                    start_time, end_time = nlpParseTime(nlp["entities"]["datetime"][0])
            
                    for person in refdPeople:
                        try:
                            newCheckIn = CheckIn(
                                person = person,
                                place = place,
                                start_time = start_time,
                                end_time = end_time
                            )
                            newCheckIn.clean()
                            newCheckIn.save()
                            person.ensureNoOverlapsWith(newCheckIn)
                            user.send(f"✔️ I've checked {person} in for {newCheckIn.prettyNoName()}.")

                        except ValidationError as e:
                            user.send(e.message)
                            break
                        
                        except Exception as e:
                            user.send(repr(e))
                            break

                sendForPlace(user, place)

    else:
        sendIncomprehension(user, inMsg)

def getNameFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    return response["first_name"]
