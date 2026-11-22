from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from oauth2_provider import urls as oauth

from utenti import views as utenti_views
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Controlli: amministrazione")
admin.site.site_title = _("Controlli")
admin.site.index_title = _("Utenti, ruoli e tabelle di decodifica")

# Accesso OAuth 2.0 per la chat. Della libreria si espongono solo gli indirizzi che
# servono: autorizzazione, token, revoca, registrazione dei client e metadati. Restano
# fuori le pagine con cui ogni utente potrebbe creare applicazioni a mano e i flussi
# che non usiamo.
INDIRIZZI_OAUTH = (
    oauth.metadata_urlpatterns
    + [u for u in oauth.base_urlpatterns if u.name in {"authorize", "token", "revoke-token"}]
    + oauth.dcr_urlpatterns
)

urlpatterns = [
    path("", utenti_views.home, name="home"),
    path("accesso/", auth_views.LoginView.as_view(), name="login"),
    path("uscita/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("archivio/", include("archivio.urls")),
    path("elaborazione/", include("elaborazione.urls")),
    path("grafo/", include("grafo.urls")),
    path("o/", include((INDIRIZZI_OAUTH, "oauth2_provider"))),
    # I documenti "well-known" vanno cercati alla radice del sito: è lì che la chat
    # scopre a quale server di autorizzazione rivolgersi (RFC 8414 e RFC 9728).
    path("", include((oauth.metadata_urlpatterns, "oauth2_provider"), namespace="oauth2_metadata")),
]
