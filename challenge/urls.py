from django.urls import path

from . import views

app_name = "challenge"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("reglement/", views.reglement, name="reglement"),
    path("manche/<int:numero>/", views.manche_detail, name="manche_detail"),
    path("classement/individuel/", views.classement_individuel_vue, name="classement_individuel"),
    path("classement/club/", views.classement_club_vue, name="classement_club"),
    path("classement/general/", views.classement_general_vue, name="classement_general"),
    path("classement/meilleur-archer/", views.meilleur_archer_vue, name="meilleur_archer"),
]
