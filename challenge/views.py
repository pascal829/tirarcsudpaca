from django.shortcuts import get_object_or_404, render

from .models import CATEGORIE_AGE_CHOICES, SEXE_CHOICES, TYPE_ARC_CHOICES, Manche, saison_sportive
from .services import (
    classement_club,
    classement_general,
    classement_individuel,
    meilleur_archer_challenge,
)


def _saison_courante(request):
    saison = request.GET.get("saison")
    if saison:
        try:
            return int(saison)
        except ValueError:
            pass
    return saison_sportive()


def _label_categorie(cle):
    age, sexe, arc = cle
    return (
        f"{dict(CATEGORIE_AGE_CHOICES)[age]} - "
        f"{dict(SEXE_CHOICES)[sexe]} - {dict(TYPE_ARC_CHOICES)[arc]}"
    )


def reglement(request):
    return render(request, "challenge/reglement.html")


def accueil(request):
    saison = _saison_courante(request)
    manches = Manche.objects.filter(saison=saison).order_by("numero")
    context = {"saison": saison, "manches": manches}
    return render(request, "challenge/accueil.html", context)


def manche_detail(request, numero):
    manche = get_object_or_404(Manche, numero=numero)
    resultats = manche.resultats.select_related("archer").order_by(
        "-points_classement", "-score"
    )
    return render(
        request,
        "challenge/manche_detail.html",
        {"manche": manche, "resultats": resultats},
    )


def classement_individuel_vue(request):
    saison = _saison_courante(request)
    brut = classement_individuel(saison)
    categories = []
    for cle, entries in brut.items():
        categories.append(
            {
                "label": _label_categorie(cle),
                "entries": [
                    {"archer": a, "moyenne": round(m, 2), "resultats": r}
                    for a, m, r in entries
                ],
            }
        )
    categories.sort(key=lambda c: c["label"])
    return render(
        request,
        "challenge/classement_individuel.html",
        {"saison": saison, "categories": categories},
    )


def classement_club_vue(request):
    saison = _saison_courante(request)
    classement = classement_club(saison)
    return render(
        request,
        "challenge/classement_club.html",
        {"saison": saison, "classement": classement},
    )


def classement_general_vue(request):
    saison = _saison_courante(request)
    brut = classement_general(saison)
    classement = [
        {"archer": a, "total": t, "nb_manches": len(r)} for a, t, r in brut
    ]
    return render(
        request,
        "challenge/classement_general.html",
        {"saison": saison, "classement": classement},
    )


def meilleur_archer_vue(request):
    saison = _saison_courante(request)
    brut = meilleur_archer_challenge(saison)
    classement = [
        {"archer": a, "total": t, "nb_manches": len(r)} for a, t, r in brut
    ]
    return render(
        request,
        "challenge/meilleur_archer.html",
        {"saison": saison, "classement": classement},
    )
