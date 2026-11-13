from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from utenti import views as utenti_views
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Controlli: amministrazione")
admin.site.site_title = _("Controlli")
admin.site.index_title = _("Utenti, ruoli e tabelle di decodifica")

urlpatterns = [
    path("", utenti_views.home, name="home"),
    path("accesso/", auth_views.LoginView.as_view(), name="login"),
    path("uscita/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
