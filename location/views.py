from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from .models import Place, CheckIn
from .forms import CheckInForm


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
            return HttpResponseRedirect("/")

    else:
        timediff = timezone.now() - timezone.timedelta(hours = 2)
        freshCheckIns = CheckIn.objects.filter(time__gte = timediff)
        places = {checkin.place.name: [] for checkin in freshCheckIns}
        
        for checkin in freshCheckIns:
            places[checkin.place.name].append(checkin)

        context = {"places": places, "form": CheckInForm}

        return render(request, "location/index.html", context)

def scratchCheckIn(request, name):
    checkin = get_object_or_404(CheckIn, person = name)
    checkin.scratched = True
    checkin.save()
    print(checkin)
    return HttpResponseRedirect("/")
 