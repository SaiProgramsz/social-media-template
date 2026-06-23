from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("report/", views.report, name="report"),
    path("block/<str:username>/", views.block_user, name="block"),
    path("reports/", views.reports_dashboard, name="reports"),
]
