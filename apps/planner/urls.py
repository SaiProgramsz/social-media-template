from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.planner_home, name="home"),
    path("api/plan/", views.planner_api, name="api"),
]

