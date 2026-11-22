"""Indirizzi dell'archivio (sotto /archivio/)."""
from django.urls import path

from . import views

app_name = "archivio"

urlpatterns = [
    path("", views.faldoni, name="faldoni"),
    path("faldone/<str:codice>/", views.faldone, name="faldone"),
    path("fascicolo/<int:numero>/", views.fascicolo, name="fascicolo"),
]
