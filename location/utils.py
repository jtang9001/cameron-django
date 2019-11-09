
from django.utils import timezone

def two_hrs_later():
    return timezone.now() + timezone.timedelta(hours = 2)

