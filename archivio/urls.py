"""Indirizzi dell'archivio (sotto /archivio/)."""
from django.urls import path

from . import views

app_name = "archivio"

urlpatterns = [
    path("", views.faldoni, name="faldoni"),
    path("faldone/<str:codice>/", views.faldone, name="faldone"),
    path("fascicolo/<int:numero>/", views.fascicolo, name="fascicolo"),
    path("file/<int:numero>/", views.file, name="file"),
    path("file/<int:numero>/scarica/", views.scarica, name="scarica"),
    path("file/<int:numero>/anteprima/", views.anteprima, name="anteprima"),
    path("file/<int:numero>/cancella/", views.cancella_file, name="cancella_file"),
]
