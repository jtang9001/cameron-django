import requests
import json

from .models import Place, CheckIn, Person
from .tokens import FB_ACCESS_TOKEN


def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " :")

class MessengerUser:
    def __init__(self, userID):
        self.userID = userID
        self.state = "init"

    def handleMessage(self, inMsg):
        msg = cleanMsg(inMsg)
        print("IN:", msg)

        if "whos in" in msg or "who is in" in msg:
            location = " ".join(msg.split()[2:])
            place = Place.objects.filter(name__icontains = location).first()

            if matchingPlaces is None:
                self.send("I don't know where you mean :(")

            else:
                print(place)

                checkins = CheckIn.objects.filter(place = place)
                freshCheckIns = [checkin for checkin in checkins if checkin.is_fresh()]
                futureCheckIns = [checkin for checkin in checkins if checkin.is_future_fresh()]

                if len(freshCheckIns) > 0:
                    self.send(f"Here's who's in {place.name}:")
                    self.send("\n".join(checkin.prettyNoPlace() for checkin in freshCheckIns))

                if len(futureCheckIns) > 0:
                    self.send(f"Here's who will be in {place.name}:")
                    self.send("\n".join(checkin.prettyNoPlace() for checkin in futureCheckIns))

                elif len(freshCheckIns) == 0 and len(futureCheckIns) == 0:
                    self.send(f"Nobody's checked into {place.name}.")
                    self.state = "checking_in"

        elif "wheres" in msg or "where is" in msg:
            name = " ".join(msg.split()[2:])
            person = Person.objects.filter(name__iexact = name).first()

            if person is None:
                self.send("I don't know who that is :(")

            else:
                checkins = person.checkin_set.all()
                checkinStrs = [checkin.prettyNoName() for checkin in checkins
                               if checkin.is_fresh() or checkin.is_future_fresh()]

                if len(checkinStrs) > 0:
                    self.send(f"Here's where {person.name} has checked in:")
                    self.send("\n".join(checkinStrs))

                else:
                    self.send(f"{person.name} isn't checked in anywhere :(")


        else:
            self.send(f"You said, '{inMsg}'. I don't understand, sorry!")

    def send(self, outMsg, msgType = "RESPONSE"):
        print("OUT:", outMsg)
        endpoint = f"https://graph.facebook.com/v5.0/me/messages?access_token={FB_ACCESS_TOKEN}"
        response_msg = json.dumps(
            {
                "messaging_type": msgType,
                "recipient": {"id":self.userID},
                "message": {"text":outMsg}
            }
        )
        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg)
        print(status.json())
