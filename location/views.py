from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import Place, CheckIn
from .forms import CheckInForm

def getPlaceFromSession(request):
    try:
        return Place.objects.get(name=request.session.get("place"))
    except ObjectDoesNotExist:
        return None

def render_for_get(request, form):
    checkIns = CheckIn.objects.all()
    places = {checkin.place.name: [] for checkin in checkIns}
    
    for checkin in checkIns:
        if checkin.is_fresh() or checkin.is_future_fresh():
            places[checkin.place.name].append(checkin)

    for place, checkins in places.items():
        checkins.sort(key = lambda checkin: checkin.start_time)

    context = {"places": places, "form": form}

    return render(request, "location/index.html", context)


def index(request):
    if request.method == "POST":
        form = CheckInForm(request.POST)
        if form.is_valid():
            newCheckIn, created = CheckIn.objects.update_or_create(
                person = form.cleaned_data["person"],
                defaults = form.cleaned_data
            )
            newCheckIn.scratched = False
            newCheckIn.save()
            request.session["person"] = form.cleaned_data["person"]
            request.session["place"] = form.cleaned_data["place"].name
            return HttpResponseRedirect("/")
        else:
            return render_for_get(request, form)

    else:
        form = CheckInForm(initial={
            "person": request.session.get("person"),
            "place": getPlaceFromSession(request)
        })
        return render_for_get(request, form)

def scratchCheckIn(request, name):
    checkin = get_object_or_404(CheckIn, person = name)
    checkin.scratched = True
    checkin.save()
    print(checkin)
    return HttpResponseRedirect("/")
 