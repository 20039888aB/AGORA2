from django.urls import path
from content.views import (
    team_add, team_assign, team_performance, 
    team_schedule, team_communication
)

urlpatterns = [
    path('add/', team_add, name='team_add'),
    path('assign/', team_assign, name='team_assign'),
    path('performance/', team_performance, name='team_performance'),
    path('schedule/', team_schedule, name='team_schedule'),
    path('communication/', team_communication, name='team_communication'),
]
