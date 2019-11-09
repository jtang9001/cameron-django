from django.forms import *
from django.utils import timezone
from .models import CheckIn, two_hrs_later, Place


class CheckInForm(ModelForm):
    name = CharField(max_length=25)
    place = ModelChoiceField(
        Place.objects.all(),
        widget = Select(attrs={"class": "browser-default"})
    )
    start_time = SplitDateTimeField(
        widget = SplitDateTimeWidget(
            time_attrs={"class": "timepicker"},
            date_attrs={"class": "datepicker"},
            time_format='%H:%M'
        ),
        initial=timezone.now
    )
    end_time = SplitDateTimeField(
        widget = SplitDateTimeWidget(
            time_attrs={"class": "timepicker"},
            date_attrs={"class": "datepicker"},
            time_format='%H:%M'
        ),
        initial=two_hrs_later
    )

    class Meta:
        model = CheckIn
        fields = ["name", "place", "start_time", "end_time"]