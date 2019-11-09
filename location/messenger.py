import requests
import json

from .models import Place
from .tokens import FB_ACCESS_TOKEN


def cleanMsg(msg):
    return ''.join(char.lower() for char in msg if char.isalnum() or char in ":")

class MessengerUser:
    def __init__(self, userID):
        self.userID = userID
    
    def handleMessage(self, inMsg):
        msg = cleanMsg(inMsg)

        if "whos in" in msg:
            location = " ".join(msg.split()[2:])
            matchingPlaces = Place.objects.filter(name__icontains = location)
            
            if len(matchingPlaces) == 0:
                self.send("I don't know where you mean :(")
                return
            elif len(matchingPlaces) > 1:
                self.send("More than one place was found!")
            
            for place in matchingPlaces:
                self.send(f"Here's who's in {place.name}:")
                checkins = place.checkin_set.all().order_by("end_time")
                self.send(
                    "\n".join(
                        checkin.pretty() for checkin in checkins
                    )
                )

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