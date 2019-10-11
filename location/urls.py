from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scratch/<str:name>', views.scratchCheckIn, name="scratch")
]