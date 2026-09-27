from django.contrib import admin, messages

from .models import Archer, Club, Manche, Resultat
from .services import calculer_classement_manche


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville", "code_club_ffta")
    search_fields = ("nom", "ville", "code_club_ffta")


@admin.register(Archer)
class ArcherAdmin(admin.ModelAdmin):
    list_display = (
        "nom", "prenom", "licence_ffta", "club", "sexe", "type_arc",
        "categorie_age_display", "actif",
    )
    list_filter = ("club", "sexe", "type_arc", "actif")
    search_fields = ("nom", "prenom", "licence_ffta")

    @admin.display(description="Catégorie d'âge")
    def categorie_age_display(self, obj):
        return obj.categorie_age()


class ResultatInline(admin.TabularInline):
    model = Resultat
    extra = 1
    fields = ("archer", "score", "disqualifie", "rang_categorie", "points_classement")
    readonly_fields = ("rang_categorie", "points_classement")
    autocomplete_fields = ("archer",)


@admin.register(Manche)
class MancheAdmin(admin.ModelAdmin):
    list_display = ("numero", "nom", "club_organisateur", "date", "saison", "validee")
    list_filter = ("saison", "validee", "club_organisateur")
    search_fields = ("nom", "numero")
    inlines = [ResultatInline]
    actions = ["valider_manches"]

    def save_formset(self, request, form, formset, change):
        """
        Recalcule automatiquement les rangs et points (Article 5) dès
        que les résultats d'une manche sont enregistrés, ajoutés,
        modifiés ou supprimés depuis la fiche de la manche — plus
        besoin de lancer une action manuelle.
        """
        super().save_formset(request, form, formset, change)
        if formset.model is Resultat:
            calculer_classement_manche(form.instance)

    @admin.action(description="Valider les manches sélectionnées et recalculer le classement")
    def valider_manches(self, request, queryset):
        for manche in queryset:
            manche.validee = True
            manche.save(update_fields=["validee"])
            calculer_classement_manche(manche)
        self.message_user(
            request,
            f"{queryset.count()} manche(s) validée(s) et classement recalculé.",
            messages.SUCCESS,
        )


@admin.register(Resultat)
class ResultatAdmin(admin.ModelAdmin):
    list_display = (
        "manche", "archer", "score", "rang_categorie", "points_classement", "disqualifie",
    )
    list_filter = ("manche", "disqualifie")
    search_fields = ("archer__nom", "archer__prenom", "archer__licence_ffta")
    autocomplete_fields = ("archer", "manche")

    def save_model(self, request, obj, form, change):
        """Recalcule le classement de la manche dès qu'un résultat est ajouté/modifié ici."""
        super().save_model(request, obj, form, change)
        calculer_classement_manche(obj.manche)

    def delete_model(self, request, obj):
        manche = obj.manche
        super().delete_model(request, obj)
        calculer_classement_manche(manche)

    def delete_queryset(self, request, queryset):
        manches = {r.manche for r in queryset}
        super().delete_queryset(request, queryset)
        for manche in manches:
            calculer_classement_manche(manche)
