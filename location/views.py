import json
import traceback

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from .models import Place, CheckIn, Person
from .forms import CheckInForm
from .tokens import FB_VERIFY_TOKEN
from .messenger import handleMessage, getNameFromPSID

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
        print(request.POST)
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

            user.cleanCheckIns(newCheckIn)

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
    checkin.scratch()
    print(checkin)
    return HttpResponseRedirect("/")

def startPlannedCheckIn(request, checkInPK):
    checkin = get_object_or_404(CheckIn, pk = checkInPK)
    user = checkin.person
    checkin.start_time = timezone.now()
    checkin.scratched = False
    checkin.save()
    user.cleanCheckIns(checkin)
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
        try:
            if request.GET["hub.verify_token"] == FB_VERIFY_TOKEN:
                return HttpResponse(request.GET['hub.challenge'])
            else:
                return HttpResponse("Invalid token", status=403)
        except Exception:
            return HttpResponse("Invalid webhook formatting", status=403)

    elif request.method == "POST":
        incoming_message = json.loads(request.body.decode('utf-8'))
        print("WEBHOOK RECEIVED:")
        for line in json.dumps(incoming_message, sort_keys=True, indent=4).split("\n"):
            print(line)
        #print(incoming_message)
        try:
            for entry in incoming_message['entry']:
                for message in entry['messaging']:
                    userID = message['sender']['id']

                    try:
                        user = Person.objects.get(facebook_id = userID)
                    except ObjectDoesNotExist:
                        personName = getNameFromPSID(userID)
                        user, created = Person.objects.update_or_create(
                            name = personName,
                            defaults = {"facebook_id": userID}
                        )

                    msg = message['message']['text']
                    nlp = message['message']['nlp']
                    print(nlp)

                    handleMessage(user, msg, nlp)
            return HttpResponse("Webhook OK", status=200)
        except Exception:
            traceback.print_exc()
            return HttpResponse("Webhook POST error", status=200)
