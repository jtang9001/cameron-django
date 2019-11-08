import json
import requests

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from .models import Place, CheckIn, Person, overlaps
from .forms import CheckInForm
from .tokens import *

def getPlaceFromSession(request):
    try:
        return Place.objects.get(name=request.session.get("place"))
    except ObjectDoesNotExist:
        return None

def getPersonFromSession(request):
    try:
        return Person.objects.get(name=request.session.get("person"))
    except ObjectDoesNotExist:
        return None

def render_for_get(request, form):
    people = Person.objects.all()
    people = sorted(people, key=lambda person: person.getScore(), reverse=True)
    allCheckIns = CheckIn.objects.filter(scratched = False)
    #allCheckIns = CheckIn.objects.all()
    freshCheckIns = [checkin for checkin in allCheckIns if checkin.is_fresh() or checkin.is_future_fresh()]
    places = {checkin.place: [] for checkin in freshCheckIns}
    
    for checkin in freshCheckIns:
        places[checkin.place].append(checkin)

    for place, checkins in places.items():
        checkins.sort(key = lambda checkin: checkin.start_time)

    context = {"places": places, "form": form, "people": people}

    return render(request, "location/index.html", context)


def index(request):
    if request.method == "POST":
        form = CheckInForm(request.POST)
        if form.is_valid():
            user, userCreated = Person.objects.get_or_create(name=form.cleaned_data["name"])

            formDataCopy = form.cleaned_data.copy()
            del formDataCopy["name"]

            newCheckIn = CheckIn(
                person = user,
                **formDataCopy,
                scratched = False
            )
            newCheckIn.save()

            for checkIn in user.checkin_set.all():
                if checkIn == newCheckIn:
                    continue
                if overlaps(checkIn, newCheckIn):
                    checkIn.end_time = timezone.now()
                    checkIn.scratched = True
                    checkIn.save()

            request.session["person"] = form.cleaned_data["name"]
            request.session["place"] = form.cleaned_data["place"].name
            return HttpResponseRedirect("/")
        else:
            return render_for_get(request, form)

    else:
        try: 
            name = request.session["person"]
        except KeyError:
            name = None
        form = CheckInForm(initial={
            "name": name,
            "place": getPlaceFromSession(request)
        })
        return render_for_get(request, form)

def scratchCheckIn(request, checkInPK):
    checkin = get_object_or_404(CheckIn, pk = checkInPK)
    checkin.end_time = timezone.now()
    checkin.scratched = True
    checkin.save()
    print(checkin)
    return HttpResponseRedirect("/")

def startPlannedCheckIn(request, checkInPK):
    checkin = get_object_or_404(CheckIn, pk = checkInPK)
    user = checkin.person
    checkin.start_time = timezone.now()
    checkin.scratched = False
    checkin.save()
    for oldCheckIn in user.checkin_set.all():
        if oldCheckIn == checkin:
            continue
        if overlaps(oldCheckIn, checkin):
            oldCheckIn.end_time = timezone.now()
            oldCheckIn.scratched = True
            oldCheckIn.save()
    print(checkin)
    return HttpResponseRedirect("/")

def restoreCheckIn(request, checkInPK):
    checkin = get_object_or_404(CheckIn, pk = checkInPK)
    checkin.scratched = False
    checkin.save()
    print(checkin)
    return HttpResponseRedirect("/")

@csrf_exempt
def messenger(request):
    if request.method == "GET":
        print(request.GET)
        if request.GET["hub.verify_token"] == FB_VERIFY_TOKEN:
            return HttpResponse(request.GET['hub.challenge'])
        else:
            return HttpResponse("Invalid token", status=403)
    elif request.method == "POST":
        print(request.POST)
        return HttpResponse("Webhook OK", status=200)

def sendToMessenger(userID, msg, msgType = "RESPONSE"):
    endpoint = f"https://graph.facebook.com/v5.0/me/messages?access_token={FB_ACCESS_TOKEN}"
    response_msg = json.dumps(
        {
            "messaging_type": msgType,
            "recipient": {"id":userID}, 
            "message": {"text":msg}
        }
    )
    status = requests.post(
        endpoint, 
        headers={"Content-Type": "application/json"},
        data=response_msg)
    print(status.json())