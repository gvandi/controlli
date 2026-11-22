"""Indirizzi dell'elaborazione (sotto /elaborazione/)."""
from django.urls import path

from . import views

app_name = "elaborazione"

urlpatterns = [
    path("file/<int:numero>/", views.file, name="file"),
    path("soggetto/<int:numero>/", views.soggetto, name="soggetto"),
    path("fuori-catalogo/", views.fuori_catalogo, name="fuori_catalogo"),
]
