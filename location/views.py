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


def index(request):
    if request.method == "POST":
        form = CheckInForm(request.POST)
        if form.is_valid():
            print(form.cleaned_data)
            newCheckIn, created = CheckIn.objects.update_or_create(
                person = form.cleaned_data["person"],
                defaults = form.cleaned_data
            )
            newCheckIn.scratched = False
            newCheckIn.time = timezone.now()
            newCheckIn.save()
            request.session["person"] = form.cleaned_data["person"]
            request.session["place"] = form.cleaned_data["place"].name
            return HttpResponseRedirect("/")

    else:
        timediff = timezone.now() - timezone.timedelta(hours = 2)
        freshCheckIns = CheckIn.objects.filter(time__gte = timediff)
        places = {checkin.place.name: [] for checkin in freshCheckIns}
        
        for checkin in freshCheckIns:
            places[checkin.place.name].append(checkin)

        form = CheckInForm(initial={
            "person": request.session.get("person"),
            "place": getPlaceFromSession(request)
        })

        context = {"places": places, "form": form}

        return render(request, "location/index.html", context)

def scratchCheckIn(request, name):
    checkin = get_object_or_404(CheckIn, person = name)
    checkin.scratched = True
    checkin.save()
    print(checkin)
    return HttpResponseRedirect("/")
 