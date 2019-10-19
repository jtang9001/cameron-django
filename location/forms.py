from django.forms import ModelForm, SplitDateTimeWidget, SplitDateTimeField, ValidationError
from django.utils import timezone
from .models import CheckIn, two_hrs_later

def is_later_than_now(val):
    if timezone.now() - val > timezone.timedelta(minutes=30):
        raise ValidationError("Date/time is too far in the past")

class CheckInForm(ModelForm):
    start_time = SplitDateTimeField(
        widget = SplitDateTimeWidget(
            time_attrs={"class": "timepicker"},
            date_attrs={"class": "datepicker"},
            time_format='%H:%M'
        ),
        initial=timezone.now,
        validators=[is_later_than_now]
    )
    end_time = SplitDateTimeField(
        widget = SplitDateTimeWidget(
            time_attrs={"class": "timepicker"},
            date_attrs={"class": "datepicker"},
            time_format='%H:%M'
        ),
        #initial=two_hrs_later,
        validators=[is_later_than_now],
        required=False
    )

    class Meta:
        model = CheckIn
        fields = ["person", "place", "start_time", "end_time"]

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError("End time must be after start time.")
            elif end_time - start_time > timezone.timedelta(hours=12):
                raise ValidationError("You are spending too long in one place!")
            elif start_time - timezone.now() > timezone.timedelta(hours=12):
                raise ValidationError("You are planning too far ahead!")