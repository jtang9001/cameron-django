import requests
import json

from .models import Place
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
            location = " ".join(msg.split()[2:])
            matchingPlaces = Place.objects.filter(name__icontains = location)

            if len(matchingPlaces) == 0:
                self.send("I don't know where you mean :(")

            elif len(matchingPlaces) > 1:
                self.send("More than one matching place was found!")

            for place in matchingPlaces:

                checkins = place.checkin_set.all().order_by("end_time")
                freshCheckIns = (checkin for checkin in checkins if checkin.is_fresh())
                futureCheckIns = (checkin for checkin in checkins if checkin.is_future_fresh())

                if len(freshCheckIns) > 0:
                    self.send(f"Here's who's in {place.name}:")

                    self.send(
                        "\n".join(
                            checkin.pretty() for checkin in freshCheckIns
                        )
                    )

                if len(futureCheckIns) > 0:
                    self.send(f"Here's who will be in {place.name}:")
                    self.send(
                        "\n".join(
                            checkin.pretty() for checkin in futureCheckIns
                        )
                    )

                elif len(freshCheckIns) == 0 and len(futureCheckIns) == 0:
                    self.send(f"Nobody's checked into {place.name}. Would you like to?")
                    self.state = "checking_in"

        else:
            self.send(f"You said, '{inMsg}'. I don't understand, sorry!")

    def send(self, outMsg, msgType = "RESPONSE"):
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