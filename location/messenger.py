import requests
import json
import random

from .models import Place, CheckIn, Person, getPersonWithPossibleS
from .tokens import FB_ACCESS_TOKEN
from .utils import cleanMsg, nlpParseTime, two_hrs_later, getBestEntityFromSubset, next_rounded_time

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count

class QuickReply:
    def __init__(self, text, payload = None, img = None):
        self.text = text
        self.payload = text if payload is None else payload
        self.img = img

    def getDict(self):
        returnDict = {
            "content_type": "text",
            "title": self.text,
            "payload": self.payload
        }

        if self.img is not None:
            returnDict["image_url"] = self.img

        return returnDict

class QuickReplyArray:
    def __init__(self, arr):
        self.qrs = []
        for item in arr:
            if isinstance(item, QuickReply):
                self.qrs.append(item)
            else:
                self.qrs.append(QuickReply(str(item)))

    def getList(self):
        return [qr.getDict() for qr in self.qrs]

TRIGGERS = {
    "everybody": ["everyone", "everybody", "people", "checked in"],
    "locations": ["locations", "places"],
    "leaderboard": ["leaderboard", "leader board", "score", "scoreboard", "scores", "top"],
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


def sendForPlace(user, place, quick_replies = None):
    print("Send for", place)

    checkins = CheckIn.objects.filter(place = place)
    freshCheckIns = [checkin for checkin in checkins if checkin.is_fresh()]
    futureCheckIns = [checkin for checkin in checkins if checkin.is_future_fresh()]

    if len(freshCheckIns) > 0:
        user.send(f"Here's who's in {place.name}:")
        user.send("\n".join(checkin.prettyNoPlace() for checkin in freshCheckIns),
            quick_replies=quick_replies)

    if len(futureCheckIns) > 0:
        user.send(f"Here's who will be in {place.name}:")
        user.send("\n".join(checkin.prettyNoPlace() for checkin in futureCheckIns),
            quick_replies=quick_replies)

    elif len(freshCheckIns) == 0 and len(futureCheckIns) == 0:
        user.send(f"Nobody's checked into {place.name}.",
            quick_replies=QuickReplyArray([f"I'm in {place}"]))


def sendForPerson(user, person, quick_replies = None):
    checkins = person.checkin_set.all()
    checkinStrs = [checkin.prettyNoName() for checkin in checkins
                    if checkin.is_fresh() or checkin.is_future_fresh()]

    if len(checkinStrs) > 0:
        user.send(f"Here's where {person.name} has checked in:")
        user.send("\n".join(checkinStrs), quick_replies=quick_replies)

    else:
        user.send(f"{person.name} isn't checked in anywhere", quick_replies=quick_replies)


def sendAllCheckIns(user):
    sentReply = False
    for place in Place.objects.all():
        if place.hasRelevantCheckIns():
            sendForPlace(user, place)
            sentReply = True
    if not sentReply:
        user.send(
            "Nobody's checked in anywhere 😞",
            quick_replies=QuickReplyArray(["😠", "😤", "😭", "😲", "😒"])
        )


def sendIncomprehension(user, origMsg):
    randomPerson = random.choice(Person.objects.filter(facebook_photo__isnull=False))
    user.send(f"You said, '{origMsg}'. {random.choice(DIALOG['incomprehension'])}")
    user.send("💡 Try saying, 'locations', 'who's in Cam', 'where's Jiayi', 'I'll be in ECHA in 5', or something like that.")
    user.send("You can send suggestions to https://github.com/jtang9001/cameron-django/issues. Thanks!",
        quick_replies=QuickReplyArray([
            "Locations",
            "Who's checked in?",
            f"Who's in {random.choice(Place.objects.all())}?",
            QuickReply(f"Where's {randomPerson}?", img=randomPerson.facebook_photo),
            "Leaderboard"
        ])
    )


def sendLeaderboard(user):
    people = Person.objects.all()
    people = sorted(people, key=lambda person: person.getScore(), reverse=True)
    peopleStrs = [f"{person} - {person.getScore()}" for person in people]

    medals = ["🥇 ", "🥈 ", "🥉 "]

    for i in range(min(len(medals), len(peopleStrs))):
        peopleStrs[i] = medals[i] + peopleStrs[i]

    user.send("\n".join(peopleStrs))


def sendAllLocations(user):
    user.send("You can check into all of the following places. Request new places at https://github.com/jtang9001/cameron-django/issues.")
    user.send(
        ", ".join( (place.name for place in Place.objects.all()) ),
        quick_replies=QuickReplyArray(
            [f"I'm in {place.name}" for place in Place.objects.filter(
            ).annotate(checkin_count=Count("checkin")).order_by('-checkin_count')[:5]]
        )
    )


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

        user.send(f"✔️ I've checked {'you' if person == user else person} in for {newCheckIn.prettyNoName()}.")
        if person != user:
            person.send(f"✔️ {user} checked you in for {newCheckIn.prettyNoName()}.",
                quick_replies=QuickReplyArray(["I'm leaving"]))

    except ValidationError as e:
        user.send(e.message)

    except Exception as e:
        user.send(repr(e))


def checkout(checkin, user, person, allowFuture = False):
    #returns if a message was sent or not

    if checkin.is_fresh():
        user.send(
            f"Checking {'you' if person == user else person} out of {checkin.place} 💨"
        )
        if person != user:
            person.send(
                f"{user} checked you out of {checkin.place} 💨",
                quick_replies=QuickReplyArray([QuickReply(
                    f"I'm in {checkin.place}",
                    payload=f"{person} in {checkin.place}" #remember: NLP doesn't apply to payloads
                )])
            )
        checkin.scratch()
        return QuickReplyArray([QuickReply(
            f"{person}'s in {checkin.place}",
            payload=f"{person} in {checkin.place}",
            img=person.facebook_photo
        )])

    elif allowFuture and checkin.is_future_fresh():
        dispName = 'your' if person == user else person.name + '\'s'
        user.send(
            f"❌ Deleting {dispName} upcoming check in at {checkin.prettyNoName()}."
        )
        if person != user:
            person.send(
                f"{user} deleted your upcoming check in at {checkin.prettyNoName()}.",
                quick_replies=QuickReplyArray([QuickReply(
                    f"I'm in {checkin.place}",
                    payload=f"{person} in {checkin.place}"
                )])
            )
        checkin.scratch()
        return QuickReplyArray([QuickReply(
            f"{person}'s in {checkin.place}",
            payload=f"{person} in {checkin.place}",
            img=person.facebook_photo
        )])

    else:
        return None


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
        doCheckOut = False
        personGiven = False
        bestNLPtype = None

        if nlp is not None and any((key in nlp["entities"] for key in SMALL_TALK_ENTITIES)):
            bestNLPtype, bestNLPentity = getBestEntityFromSubset(nlp["entities"], SMALL_TALK_ENTITIES)

        if bestNLPtype == "greetings":
            user.send(random.choice(DIALOG[bestNLPtype]))

        for word in msg.split():
            if len(word) <= 2 and word not in TRIGGERS["short_word_exceptions"]:
                continue

            if word in TRIGGERS["checkout"]:
                print("checkout word detected")
                doCheckOut = True
                continue

            if word in TRIGGERS["first_person"]:
                refdPeople.add(user)
                personGiven = True
                continue

            placeQ = Place.objects.filter(name__istartswith = word) | Place.objects.filter(aliases__icontains = word)
            personQ = getPersonWithPossibleS(name = word)

            if placeQ.exists():
                print(placeQ.first())
                refdPlaces.add(placeQ.first())

            elif personQ.exists():
                print(personQ.first())
                refdPeople.add(personQ.first())
                personGiven = True

        if len(refdPlaces) > 1:
            if len(refdPeople) == 0:
                for place in refdPlaces:
                    sendForPlace(user, place)
            else:
                user.send(f"💡 Too many places ({', '.join(place.name for place in refdPlaces)}) were referenced in your message.")

        elif len(refdPlaces) == 0:
            print("no places referenced")
            if doCheckOut:

                sendQr = None

                if len(refdPeople) == 0:
                    refdPeople.add(user)

                for person in refdPeople:
                    checkIns = CheckIn.objects.filter(person = person)
                    for checkin in checkIns:
                        qr = checkout(checkin, user, person, allowFuture=False)
                        if qr is not None:
                            sendQr = qr

                    sendForPerson(user, person, quick_replies=sendQr)

                if qr is None:
                    user.send("💡 To delete someone's planned check in, specify the place they're no longer going to.", quick_replies=sendQr)

            elif len(refdPeople) != 0:
                for person in refdPeople:
                    sendForPerson(user, person)

            else:
                if bestNLPtype is None:
                    sendIncomprehension(user, inMsg)

        elif len(refdPlaces) == 1:
            print("exactly one place referenced")
            place = next(iter(refdPlaces))

            if len(refdPeople) == 0:
                refdPeople.add(user)

            if doCheckOut:

                sendQr = None

                print("checking out")
                for person in refdPeople:
                    checkIns = CheckIn.objects.filter(person = person, place = place)

                    for checkin in checkIns:
                        qr = checkout(checkin, user, person, allowFuture=True)
                        if qr is not None:
                            sendQr = qr

                    sendForPerson(user, person, quick_replies=sendQr)

            else:
                entityType, entity = getBestEntityFromSubset(nlp["entities"], ["datetime", "duration"])

                if len(refdPeople) == 1 and user in refdPeople:
                    qrs = [QuickReply("I'm leaving",
                        payload=f"{user} leaving {place}")]
                elif len(refdPeople) > 1 and user in refdPeople:
                    qrs = [QuickReply("We're leaving",
                        payload=f"{' '.join((person.name for person in refdPeople))} leaving {place}")]
                elif len(refdPeople) == 1 and user not in refdPeople:
                    refdPerson = next(iter(refdPeople))
                    qrs = [QuickReply(f"{refdPerson} left",
                        payload=f"{refdPerson} leaving {place}",
                        img=refdPerson.facebook_photo)]
                elif len(refdPeople) > 1 and user not in refdPeople:
                    qrs = [QuickReply("They're leaving",
                        payload=f"{' '.join((person.name for person in refdPeople))} leaving {place}")]

                if entityType is not None:
                    print("dt detected. checking in")
                    start_time, end_time = nlpParseTime(user, entityType, entity)

                    for person in refdPeople:
                        makeNewCheckIn(user, person, place, start_time, end_time)

                    if len(refdPeople) > 1:
                        qrs += [QuickReply(f"{person} left",
                            payload=f"{person} leaving {place}",
                            img = person.facebook_photo) for person in refdPeople]

                else:
                    if all((
                        len(refdPeople) == 1,
                        user in refdPeople,
                        not personGiven
                    )):
                        if not isSubstringFor(msg, TRIGGERS["location_query"]):
                            user.send(f"💡 To check in, specify at least a place and a person (ex. 'I'm in Cam') or a place and a time (ex. 'Cam till 5').")
                        qrs = [f"I'm in {place}"]
                    else:
                        start_time = timezone.now()
                        end_time = two_hrs_later()
                        round_time = next_rounded_time()
                        for person in refdPeople:
                            for checkin in CheckIn.objects.filter(person = person, place = place):
                                if checkin.is_fresh():
                                    user.send(f"{person} is already checked in: {checkin.prettyNoName()}.")
                                    user.send("You can specify a new end time to extend the check in.")
                                    break
                            else:
                                makeNewCheckIn(user, person, place, start_time, end_time)

                        qrs += [
                            QuickReply(
                                f"Until {(timezone.localtime(round_time + timezone.timedelta(minutes = mins))).strftime('%H:%M')}",
                                payload=f"{' '.join((person.name for person in refdPeople))} in {place} until {(timezone.localtime(start_time + timezone.timedelta(minutes = mins))).strftime('%H:%M')}"
                            )
                            for mins in range(0, 181, 30)
                        ]

                sendForPlace(user, place,
                    quick_replies=QuickReplyArray(qrs))

        if bestNLPtype == "bye" or bestNLPtype == "thanks":
            user.send(random.choice(DIALOG[bestNLPtype]))

    else:
        user.send(random.choice(DIALOG["long_msg"]))


def getProfileFromPSID(psid):
    endpoint = f"https://graph.facebook.com/{psid}?fields=first_name,name,profile_pic&access_token={FB_ACCESS_TOKEN}"
    r = requests.get(endpoint)
    response = json.loads(r.text)
    print(response)
    return response
