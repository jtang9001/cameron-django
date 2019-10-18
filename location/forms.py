from .models import CheckIn
from django.forms import ModelForm

class CheckInForm(ModelForm):
    class Meta:
        model = CheckIn
        fields = ["person", "place", "time"]