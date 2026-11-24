from django.urls import path

from . import views

app_name = "lavori"

urlpatterns = [
    path("", views.elenco, name="elenco"),
    path("richiedi/", views.richiedi, name="richiedi"),
]
