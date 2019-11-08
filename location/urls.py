from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('messenger', views.messenger, name='messenger'),
    path('scratch/<int:checkInPK>', views.scratchCheckIn, name="scratch"),
    path('start/<int:checkInPK>', views.startPlannedCheckIn, name="start"),
    path('restore/<int:checkInPK>', views.restoreCheckIn, name="restore")
]