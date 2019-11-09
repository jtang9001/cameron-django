import requests
import json

from .models import Place, CheckIn
from .tokens import FB_ACCESS_TOKEN


def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in " :")

class MessengerUser:
    def __init__(self, userID):
        self.userID = userID
        self.state = "init"

    def handleMessage(self, inMsg):
        msg = cleanMsg(inMsg)
        print(msg)

        if "whos in" in msg:
            print("in who's in branch")
            location = " ".join(msg.split()[2:])
            matchingPlaces = Place.objects.filter(name__icontains = location)

            if len(matchingPlaces) == 0:
                self.send("I don't know where you mean :(")

            elif len(matchingPlaces) > 1:
                self.send("More than one matching place was found!")

            for place in matchingPlaces:
                print(place)

                checkins = CheckIn.objects.filter(place = place)
                print(checkins)
                freshCheckInStrs = [checkin.pretty() for checkin in checkins if checkin.is_fresh()]
                print(len(freshCheckInStrs))
                futureCheckInStrs = [checkin.pretty() for checkin in checkins if checkin.is_future_fresh()]
                print(len(futureCheckInStrs))

                if len(freshCheckInStrs) > 0:
                    self.send(f"Here's who's in {place.name}:")
                    self.send("\n".join(freshCheckInStrs))

                if len(futureCheckInStrs) > 0:
                    self.send(f"Here's who will be in {place.name}:")
                    self.send("\n".join(futureCheckInStrs))

                elif len(freshCheckInStrs) == 0 and len(futureCheckInStrs) == 0:
                    self.send(f"Nobody's checked into {place.name}. Would you like to?")
                    self.state = "checking_in"

        else:
            self.send(f"You said, '{inMsg}'. I don't understand, sorry!")

    def send(self, outMsg, msgType = "RESPONSE"):
        print(outMsg)
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
