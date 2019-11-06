from django.contrib import admin
from .models import Place, CheckIn, Person

admin.site.register(Person)
admin.site.register(Place)
admin.site.register(CheckIn)
