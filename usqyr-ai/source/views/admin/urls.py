from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path("", lambda request: redirect("admin_dashboard"), name="admin_root"),

    path("dashboard/", views.admin_dashboard_view, name="admin_dashboard"),

]
