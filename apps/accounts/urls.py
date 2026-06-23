from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("me/edit/", views.profile_edit, name="edit"),
    path("<str:username>/", views.profile_detail, name="profile"),
]

