
from django.utils import timezone

def two_hrs_later(start = timezone.now()):
    return start + timezone.timedelta(hours = 2)

