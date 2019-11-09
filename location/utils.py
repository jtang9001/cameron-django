from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

def two_hrs_later(start = None):
    if start == None:
        start = timezone.now()
    return start + timezone.timedelta(hours = 2)

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

def nlpParseTime(datetimeEntity):
    if datetimeEntity["type"] == "value":
        start_time = parse_datetime(datetimeEntity["value"])
        end_time = two_hrs_later(parse_datetime(datetimeEntity["value"]))

    elif datetimeEntity["type"] == "interval":
        start_time = parse_datetime(datetimeEntity["from"]["value"]) if "from" in datetimeEntity else timezone.now()

        if "to" in datetimeEntity:
            if datetimeEntity["to"]["grain"] == "hour" and "from" in datetimeEntity:
                end_time = parse_datetime(datetimeEntity["to"]["value"]) - timezone.timedelta(hours=1)
            else:
                end_time = parse_datetime(datetimeEntity["to"]["value"])
        else:
            end_time = two_hrs_later(start_time)

    return start_time, end_time
