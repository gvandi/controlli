from django.urls import path

from . import views

app_name = "indici"

urlpatterns = [
    path("spazio/", views.spazio, name="spazio"),
]
