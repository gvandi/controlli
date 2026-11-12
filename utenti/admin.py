from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utente


@admin.register(Utente)
class UtenteAdmin(UserAdmin):
    list_display = ("username", "last_name", "first_name", "email", "ruoli", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "groups")

    @admin.display(description="Ruoli")
    def ruoli(self, obj):
        return ", ".join(obj.nomi_ruoli()) or "-"
