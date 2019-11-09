import requests
import json
import random
import itertools

from .models import Place, CheckIn, Person
from .tokens import FB_ACCESS_TOKEN

from django.core.exceptions import ValidationError
from .utils import nlpParseTime

LOCATION_LOOKUP = ["whos in", "who is in", "who in", "who"]
PERSON_LOOKUP = ["wheres", "where is", "where"]
SHORT_WORD_EXCEPTIONS = ["ed"]
CHECK_OUT = ["wont", "not", "leaving", "leave", "out", "bounce", "bouncing", "left"]
FIRST_PERSON = ["i", "me", "im", "imma"]
LEADERBOARD = ["leaderboard", "leader board", "score"]
#CHECK_IN = [re.compile(r"(i will be |ill be |im |i am )?(in |at )?(?P<place>[a-z]+)")]
#CHECK_IN = ["i will be", "ill be", "im", "i am", "in ", "at ", "until ", "till ", "til "]

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
    "greeting": ["Hey", "Hello!", "Yoohoo!", "Yo", "Sup", "👋"],
    "bye": ["See ya!", "Bye!", "I literally cannot leave", "👋"],
    "thanks": [
        "No problem!", 
        "No, thank you 🙄", 
        "Good to see the youth of today have some manners!",
        "You're welcome!"
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
        user.send(f"{person.name} isn't checked in anywhere")

def sendIncomprehension(user, origMsg):
    user.send(f"You said, '{origMsg}'. {random.choice(DIALOG['incomprehension'])}")

def sendLeaderboard(user):
    people = Person.objects.all()
    people = sorted(people, key=lambda person: person.getScore(), reverse=True)
    peopleStrs = [f"{person} - {person.getScore()}" for person in people]

    medals = ["🥇 ", "🥈 ", "🥉 "]

    for i in range(len(medals)):
        peopleStrs[i] = medals[i] + peopleStrs[i]

    user.send("\n".join(peopleStrs))

def handleMessage(user: Person, inMsg, nlp):
    msg = cleanMsg(inMsg)
    print(f"{user.name} IN:", msg)

    if isSubstringFor(msg, LOCATION_LOOKUP):
        print("in location lookup")
        location = removeSubstrings(msg, LOCATION_LOOKUP)
        place = Place.objects.filter(name__istartswith = location).first()

        if place is None:
            user.send(random.choice(DIALOG["unsure_place"]))

        else:
            sendForPlace(user, place)

    elif isSubstringFor(msg, PERSON_LOOKUP):
        print("in person lookup")
        name = removeSubstrings(msg, PERSON_LOOKUP)
        if name in FIRST_PERSON:
            person = user
        else:
            person = Person.objects.filter(name__istartswith = name).first()

        if "every" in msg:
            print("looking up everyone")
            user.send("Here's all the information I have:")
            sentReply = False
            for place in Place.objects.all():
                print(f"looking up in {place}")
                if place.hasRelevantCheckIns():
                    print(f"found checkins in {place}")
                    sendForPlace(user, place)
                    sentReply = True
            if not sentReply:
                user.send("Nobody's checked in anywhere 🥺")

        elif person is None:
            user.send(random.choice(DIALOG["unsure_person"]))

        else:
            sendForPerson(user, person)

    elif isSubstringFor(msg, LEADERBOARD):
        sendLeaderboard(user)

    elif "greetings" in nlp["entities"] or "bye" in nlp["entities"] or "thanks" in nlp["entities"]:
        mostLikelyType, mostConfEntity = max(nlp["entities"].items(), key = lambda entityType, entity: entity[0]["confidence"])
        user.send(random.choice(DIALOG[mostLikelyType]))

    elif len(msg.split()) < 30:
        print("in general keyword search")
        refdPlaces = set()
        refdPeople = set()
        checkOut = False

        for word in msg.split():
            # if len(word) <= 2 and word not in SHORT_WORD_EXCEPTIONS:
            #     continue

            if word in CHECK_OUT:
                print("checkout word detected")
                checkOut = True
                continue

            if word in FIRST_PERSON:
                refdPeople.add(user)

            placeQ = Place.objects.filter(name__istartswith = word)
            personQ = Person.objects.filter(name__istartswith = word.strip("s"))

            if placeQ.exists():
                refdPlaces.add(placeQ.first())

            elif personQ.exists():
                refdPeople.add(personQ.first())


        if len(refdPlaces) > 1:

            user.send(f"💡 Too many places ({', '.join(refdPlaces)}) were referenced in your message.")
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

            else:
                if "datetime" in nlp["entities"]:
                    print("dt detected. checking in")
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
                else:
                    user.send(f"💡 If you want to check in, make sure to specify a time (ex. '{place} in 5 mins' or '{place} till 2') :)")

                sendForPlace(user, place)

    else:
        sendIncomprehension(user, inMsg)

def getNameFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    return response["first_name"]
