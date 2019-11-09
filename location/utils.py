from django.core.exceptions import ValidationError
from django.utils import timezone

def two_hrs_later(start = timezone.now()):
    return start + timezone.timedelta(hours = 2)

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

