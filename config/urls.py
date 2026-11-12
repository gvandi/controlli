from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from utenti import views as utenti_views

admin.site.site_header = "Controlli: amministrazione"
admin.site.site_title = "Controlli"
admin.site.index_title = "Utenti, ruoli e tabelle di decodifica"

urlpatterns = [
    path("", utenti_views.home, name="home"),
    path("accesso/", auth_views.LoginView.as_view(), name="login"),
    path("uscita/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
