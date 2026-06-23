from django.urls import path

from . import views

app_name = "feed"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("new/", views.create_post, name="new"),
    path("<int:post_id>/delete/", views.delete_post, name="delete"),
]
