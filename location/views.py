from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from .models import Place, CheckIn


def index(request):
    timediff = timezone.now() - timezone.timedelta(hours = 2)
    freshCheckIns = CheckIn.objects.filter(time__gte = timediff)
    places = {checkin.place.name: [] for checkin in freshCheckIns}
    
    for checkin in freshCheckIns:
        places[checkin.place.name].append(checkin.person)

    context = {"places": places}

    return render(request, "location/index.html", context)