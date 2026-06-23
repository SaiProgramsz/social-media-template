from django.urls import path

from . import views

app_name = "rooms"

urlpatterns = [
    path("", views.room_list, name="list"),
    path("new/", views.create_room, name="new"),
    path("<int:room_id>/", views.room_detail, name="detail"),
    path("<int:room_id>/join/", views.join_room, name="join"),
    path("<int:room_id>/message/", views.send_message, name="message"),
    path("<int:room_id>/pomodoro/start/", views.start_pomodoro, name="pomodoro_start"),
    path("<int:room_id>/pomodoro/<int:session_id>/end/", views.end_pomodoro, name="pomodoro_end"),
    path("<int:room_id>/delete/", views.delete_room, name="delete"),
]
