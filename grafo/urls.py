"""Indirizzi dell'app grafo (sotto /grafo/)."""
from django.urls import path

from . import views

app_name = "grafo"

urlpatterns = [
    path("mcp/", views.mcp, name="mcp"),
    path("mappe/<int:numero>/", views.mappa, name="mappa"),
    path("collegamento/", views.collegamento, name="collegamento"),
    path("cruscotto/", views.cruscotto, name="cruscotto"),
]
