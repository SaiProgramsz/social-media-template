from django.urls import path

from . import views

app_name = "qa"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("ask/", views.ask, name="ask"),
    path("<int:question_id>/", views.question_detail, name="detail"),
    path("<int:question_id>/answer/", views.answer, name="answer"),
]

