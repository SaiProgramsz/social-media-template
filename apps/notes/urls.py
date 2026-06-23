from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.note_list, name="list"),
    path("new/", views.create_note, name="new"),
    path("<int:note_id>/", views.note_detail, name="detail"),
]

