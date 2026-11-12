from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Pagina iniziale: mostra le aree disponibili in base ai diritti dell'utente."""
    utente = request.user
    contesto = {
        "ruoli": utente.nomi_ruoli(),
        "puo_gestire_utenti": utente.has_perm("utenti.change_utente"),
        "puo_configurare": utente.has_module_perms("decodifiche"),
        "puo_entrare_in_admin": utente.is_staff,
    }
    return render(request, "home.html", contesto)
