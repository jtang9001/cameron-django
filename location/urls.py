from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scratch/<str:name>', views.scratchCheckIn, name="scratch"),
    path('start/<str:name>', views.startPlannedCheckIn, name="start"),
    path('restore/<str:name>', views.restoreCheckIn, name="restore")
]