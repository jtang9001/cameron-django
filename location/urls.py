from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scratch/<int:checkInPK>', views.scratchCheckIn, name="scratch"),
    path('start/<int:checkInPK>', views.startPlannedCheckIn, name="start"),
    path('restore/<int:checkInPK>', views.restoreCheckIn, name="restore")
]