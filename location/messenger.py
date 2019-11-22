import requests
import json
import random

from .models import Place, CheckIn, Person, getPersonByName
from .tokens import FB_ACCESS_TOKEN
from .utils import cleanMsg

from django.core.exceptions import ValidationError
from .utils import nlpParseTime, two_hrs_later, getBestEntityFromSubset
from django.utils import timezone

TRIGGERS = {
    "everybody": ["everyone", "everybody", "people"],
    "locations": ["locations", "places"],
    "leaderboard": ["leaderboard", "leader board", "score", "scoreboard", "scores"],
    "first_person": ["i", "me", "im", "imma", "ill"],
    "short_word_exceptions": ["ed", "i", "me", "im"],
    "checkout": ["wont", "not", "leaving", "leave", "out", "bounce", "bouncing", "left"],
    "location_query": ["who", "anyone", "anybody"]
}

SMALL_TALK_ENTITIES = ["greetings", "bye", "thanks"]

DIALOG = {
    "unsure_place": [
        "I don't know where that is 😅",
        "Not sure where that is 🤔",
        "I don't know where you mean 😓"
    ],
    "unsure_person": [
        "Who's that now? 😅",
        "Not sure who that is 🤔",
        "Never heard of them.",
        "I don't know who that is 😅"
    ],
    "incomprehension": [
        "Not sure what you mean 😅",
        "What's that now? 😅",
        "I don't understand 😓",
        "Kindly try rephrasing? 🤔"
    ],
    "greetings": ["Hey", "Hello!", "Yoohoo!", "Yo", "Sup", "👋", "What's cookin'?"],
    "bye": ["See ya!", "Bye!", "I literally cannot leave", "👋"],
    "thanks": [
        "No problem!",
        "No, thank you 🙄",
        "Good to see the youth of today have some manners!",
        "You're welcome!"
    ],
    "long_msg": [
        "How long did you spend typing that out?",
        "Brevity is the soul of wit, hm?",
        "I got bored fifty words in. (Actually, I stop reading at fifty words.)",
        "Wow, that's a long message! I'm sure you have real friends who would appreciate it more :)",
        "Don't you have, like, real people you can talk to?",
        "I literally cannot read more than fifty words."
    ]

}

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
        user.send(f"{person.name} isn't checked in anywhere")

def sendAllCheckIns(user):
    user.send("Here's everyone that checked in:")
    sentReply = False
    for place in Place.objects.all():
        if place.hasRelevantCheckIns():
            sendForPlace(user, place)
            sentReply = True
    if not sentReply:
        user.send("Nobody's checked in anywhere 😞")

def sendIncomprehension(user, origMsg):
    user.send(f"You said, '{origMsg}'. {random.choice(DIALOG['incomprehension'])}")
    user.send("💡 Try saying, 'locations', 'who's in Cam', 'where's Jiayi', 'I'll be in ECHA in 5', or something like that.")
    user.send("You can send suggestions to https://github.com/jtang9001/cameron-django/issues. Thanks!")

def sendLeaderboard(user):
    people = Person.objects.all()
    people = sorted(people, key=lambda person: person.getScore(), reverse=True)
    peopleStrs = [f"{person} - {person.getScore()}" for person in people]

    medals = ["🥇 ", "🥈 ", "🥉 "]

    for i in range(min(len(medals), len(peopleStrs))):
        peopleStrs[i] = medals[i] + peopleStrs[i]

    user.send("\n".join(peopleStrs))

def sendAllLocations(user):
    user.send("You can check into all of the following places. Ask the real Jiayi to add more places.")
    user.send(", ".join((place.name for place in Place.objects.all())))

def makeNewCheckIn(user, person, place, start_time, end_time):
    try:
        newCheckIn = CheckIn(
            person = person,
            place = place,
            start_time = start_time,
            end_time = end_time
        )
        newCheckIn.clean()
        newCheckIn.save()
        person.cleanCheckIns(newCheckIn, verbose=True)
        user.send(f"✔️ I've checked {person} in for {newCheckIn.prettyNoName()}.")

    except ValidationError as e:
        user.send(e.message)

    except Exception as e:
        user.send(repr(e))

def handleMessage(user: Person, inMsg, nlp):
    msg = cleanMsg(inMsg)
    print(f"{user.name} IN:", msg)

    if isSubstringFor(msg, TRIGGERS["leaderboard"]):
        sendLeaderboard(user)

    elif isSubstringFor(msg, TRIGGERS["locations"]):
        sendAllLocations(user)

    elif isSubstringFor(msg, TRIGGERS["everybody"]):
        sendAllCheckIns(user)

    elif len(msg.split()) < 50:
        print("in general keyword search")
        refdPlaces = set()
        refdPeople = set()
        checkOut = False
        personGiven = False
        bestNLPtype = None

        if any((key in nlp["entities"] for key in SMALL_TALK_ENTITIES)):
            bestNLPtype, bestNLPentity = getBestEntityFromSubset(nlp["entities"], SMALL_TALK_ENTITIES)

        if bestNLPtype == "greetings":
            user.send(random.choice(DIALOG[bestNLPtype]))

        for word in msg.split():
            if len(word) <= 2 and word not in TRIGGERS["short_word_exceptions"]:
                continue

            if word in TRIGGERS["checkout"]:
                print("checkout word detected")
                checkOut = True
                continue

            if word in TRIGGERS["first_person"]:
                refdPeople.add(user)
                personGiven = True
                continue

            placeQ = Place.objects.filter(name__istartswith = word) | Place.objects.filter(aliases__icontains = word)
            personQ = getPersonByName(word.strip("s"))

            if placeQ.exists():
                refdPlaces.add(placeQ.first())

            elif personQ is not None:
                refdPeople.add(personQ.first())
                personGiven = True

        if len(refdPlaces) > 1:
            if len(refdPeople) == 0:
                for place in refdPlaces:
                    sendForPlace(user, place)
            else:
                user.send(f"💡 Too many places ({', '.join(place.name for place in refdPlaces)}) were referenced in your message.")
            return

        elif len(refdPlaces) == 0:
            print("no places referenced")
            if checkOut:
                sentMsg = False
                if len(refdPeople) == 0:
                    refdPeople.add(user)

                for person in refdPeople:
                    checkIns = CheckIn.objects.filter(person = person)
                    for checkin in checkIns:
                        print(checkin)
                        if checkin.is_fresh():
                            user.send(f"Checking {person} out of {checkin.place} 💨")
                            checkin.scratch()
                            sentMsg = True

                    sendForPerson(user, person)

                if not sentMsg:
                    user.send("💡 To delete someone's planned check in, specify the place they're no longer going to.")
            elif len(refdPeople) != 0:
                for person in refdPeople:
                    sendForPerson(user, person)
            else:
                if bestNLPtype is None:
                    sendIncomprehension(user, inMsg)

        elif len(refdPlaces) == 1:
            print("exactly one place referenced")
            place = refdPlaces.pop()

            if len(refdPeople) == 0:
                refdPeople.add(user)

            if checkOut:
                print("checking out")
                for person in refdPeople:
                    checkIns = CheckIn.objects.filter(person = person, place = place)
                    for checkin in checkIns:
                        if checkin.is_future_fresh():
                            user.send(f"❌ Deleting {person}'s future check in at {checkin.prettyNoName()}.")
                            checkin.scratch()
                        elif checkin.is_fresh():
                            user.send(f"Checking {person} out of {place} 💨")
                            checkin.scratch()
                    sendForPerson(user, person)

            else:
                entityType, entity = getBestEntityFromSubset(nlp["entities"], ["datetime", "duration"])

                if entityType is not None:
                    print("dt detected. checking in")
                    start_time, end_time = nlpParseTime(user, entityType, entity)

                    for person in refdPeople:
                        makeNewCheckIn(user, person, place, start_time, end_time)

                else:
                    if all((
                        len(refdPeople) == 1,
                        user in refdPeople,
                        not personGiven
                    )):
                        if not isSubstringFor(msg, TRIGGERS["location_query"]):
                            user.send(f"💡 To check in, specify at least a place and a person (ex. 'I'm in Cam') or a place and a time (ex. 'Cam till 5').")
                    else:
                        start_time = timezone.now()
                        end_time = two_hrs_later()
                        for person in refdPeople:
                            for checkin in CheckIn.objects.filter(person = person, place = place):
                                if checkin.is_fresh():
                                    user.send(f"{person} is already checked in: {checkin.prettyNoName()}.")
                                    user.send("You can specify a new end time to extend the check in.")
                                    break
                            else:
                                makeNewCheckIn(user, person, place, start_time, end_time)


                sendForPlace(user, place)

        if bestNLPtype == "bye" or bestNLPtype == "thanks":
            user.send(random.choice(DIALOG[bestNLPtype]))

    else:
        user.send(random.choice(DIALOG["long_msg"]))


# NICKNAMES = {
#     "Grace Zheng": "Grass"
# }

def getProfileFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name,name,profile_pic&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    # if response["name"] in NICKNAMES:
    #     response["first_name"] = NICKNAMES[response["name"]]
    return response
