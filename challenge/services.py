"""
Logique métier du challenge : attribution des points, classements,
conditions d'éligibilité et récompense spéciale.

Toutes les fonctions sont volontairement "pures" (elles ne font
qu'interroger la base et retourner des structures Python), afin de
pouvoir être appelées aussi bien depuis les vues que depuis les
commandes de management ou des tests.
"""

from collections import defaultdict

from .models import (
    BAREME_POINTS,
    BONUS_MALUS_ARC,
    POINTS_PARTICIPATION,
    Archer,
    Manche,
    Resultat,
)


def points_pour_rang(rang):
    return BAREME_POINTS.get(rang, POINTS_PARTICIPATION)


def calculer_classement_manche(manche):
    """
    Calcule le rang et les points de chaque résultat d'une manche,
    par catégorie (âge / sexe / type d'arc), et met à jour les
    résultats en base (Article 5).
    """
    resultats = manche.resultats.filter(disqualifie=False).select_related("archer")

    par_categorie = defaultdict(list)
    for resultat in resultats:
        cle = resultat.archer.cle_categorie(manche.saison)
        par_categorie[cle].append(resultat)

    for cle, groupe in par_categorie.items():
        groupe.sort(key=lambda r: r.score, reverse=True)
        rang = 1
        for i, resultat in enumerate(groupe):
            # Égalité de score sur une manche => même rang, pas de saut de rang
            if i > 0 and groupe[i - 1].score == resultat.score:
                rang_effectif = groupe[i - 1].rang_categorie
            else:
                rang_effectif = i + 1
            resultat.rang_categorie = rang_effectif
            resultat.points_classement = points_pour_rang(rang_effectif)
            resultat.save(update_fields=["rang_categorie", "points_classement"])

    return par_categorie


def manches_retenues(saison, validees_seulement=True):
    qs = Manche.objects.filter(saison=saison)
    if validees_seulement:
        qs = qs.filter(validee=True)
    return list(qs)


def resultats_archer(archer, saison, validees_seulement=True):
    qs = Resultat.objects.filter(
        archer=archer, manche__saison=saison, disqualifie=False
    )
    if validees_seulement:
        qs = qs.filter(manche__validee=True)
    return list(qs.select_related("manche"))


def est_eligible(archer, saison, validees_seulement=True):
    """
    Article 6 : conditions pour être classé et récompensé.
      1. Avoir participé à au moins 50% des manches (arrondi à l'entier inférieur)
      2. Être classé dans une catégorie comprenant au moins un autre archer
         remplissant également cette condition.
    Cette fonction ne vérifie que la condition 1 (individuelle) ;
    la condition 2 est appliquée globalement dans classement_individuel().
    """
    seuil = Manche.seuil_participation(saison, validees_seulement)
    nb_participations = len(resultats_archer(archer, saison, validees_seulement))
    return nb_participations >= seuil


def moyenne_3_meilleurs(resultats):
    """Moyenne des 3 meilleurs scores (Article 5 et 7). Si moins de 3
    résultats, la moyenne est calculée sur les résultats disponibles."""
    scores = sorted((r.score for r in resultats), reverse=True)[:3]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _departage(archer, resultats, saison):
    """
    Critères d'égalité (Article 7), dans l'ordre :
      1. Le plus grand nombre de victoires (rang == 1) sur les manches
      2. Le meilleur score réalisé sur une manche
      3. Le plus grand nombre de participations
    Retourne un tuple utilisable comme clé de tri (plus grand = mieux classé).
    """
    victoires = sum(1 for r in resultats if r.rang_categorie == 1)
    meilleur_score = max((r.score for r in resultats), default=0)
    nb_participations = len(resultats)
    return (victoires, meilleur_score, nb_participations)


def _archers_eligibles_par_categorie(saison, validees_seulement=True):
    """
    Applique les deux conditions de l'Article 6 et retourne un dict
    {cle_categorie: [(archer, resultats), ...]} ne contenant que les
    catégories et archers réellement éligibles (classement et
    récompense).
    """
    archers = Archer.objects.filter(actif=True).select_related("club")

    par_categorie = defaultdict(list)
    for archer in archers:
        resultats = resultats_archer(archer, saison, validees_seulement)
        if not resultats:
            continue
        cle = archer.cle_categorie(saison)
        par_categorie[cle].append((archer, resultats))

    resultat = {}
    for cle, entries in par_categorie.items():
        # Condition 1 : au moins 50% de participation
        eligibles = [
            (archer, resultats)
            for archer, resultats in entries
            if est_eligible(archer, saison, validees_seulement)
        ]
        # Condition 2 : au moins 2 archers éligibles dans la catégorie
        if len(eligibles) < 2:
            continue
        resultat[cle] = eligibles

    return resultat


def classement_individuel(saison, validees_seulement=True):
    """
    Classement individuel par catégorie (Article 7), basé sur la
    moyenne des 3 meilleurs scores. Seuls les archers éligibles
    (Article 6, conditions 1 et 2) apparaissent dans le résultat.

    Retourne un dict : {cle_categorie: [ (archer, moyenne, resultats), ... ]}
    trié par moyenne décroissante puis critères de départage.
    """
    par_categorie = _archers_eligibles_par_categorie(saison, validees_seulement)

    classement_final = {}
    for cle, eligibles in par_categorie.items():
        classes = []
        for archer, resultats in eligibles:
            moyenne = moyenne_3_meilleurs(resultats)
            depart = _departage(archer, resultats, saison)
            classes.append((archer, moyenne, resultats, depart))

        classes.sort(key=lambda t: (t[1], t[3]), reverse=True)
        classement_final[cle] = [
            (archer, moyenne, resultats) for archer, moyenne, resultats, _ in classes
        ]

    return classement_final


def classement_club(saison, validees_seulement=True):
    """
    Classement par club (Article 5 et 7) : cumul des points de
    classement de tous les archers du club, toutes catégories et
    manches retenues confondues.
    """
    resultats = Resultat.objects.filter(
        manche__saison=saison, disqualifie=False, points_classement__isnull=False
    ).select_related("archer__club", "manche")
    if validees_seulement:
        resultats = resultats.filter(manche__validee=True)

    points_par_club = defaultdict(int)
    for resultat in resultats:
        points_par_club[resultat.archer.club] += resultat.points_classement

    classement = sorted(points_par_club.items(), key=lambda t: t[1], reverse=True)
    return classement


def classement_general(saison, validees_seulement=True):
    """
    Classement général du challenge (Article 7) : cumul des points
    de classement individuels sur les manches retenues, avec
    départage selon les critères de l'Article 7. Seuls les archers
    remplissant les conditions d'éligibilité de l'Article 6
    apparaissent (mêmes conditions que le classement par catégorie).
    """
    par_categorie = _archers_eligibles_par_categorie(saison, validees_seulement)

    classement = []
    for eligibles in par_categorie.values():
        for archer, resultats in eligibles:
            total_points = sum(r.points_classement or 0 for r in resultats)
            depart = _departage(archer, resultats, saison)
            classement.append((archer, total_points, resultats, depart))

    classement.sort(key=lambda t: (t[1], t[3]), reverse=True)
    return [(archer, total, resultats) for archer, total, resultats, _ in classement]


def meilleur_archer_challenge(saison, validees_seulement=True):
    """
    Article 8 - Récompense spéciale "Meilleur archer du challenge".
    Réservé aux archers ayant participé à l'ensemble des manches du
    challenge. Classement = cumul des points obtenus sur toutes les
    manches, ajusté par le bonus/malus lié au type d'arc, appliqué à
    chaque manche.
    """
    total_manches = Manche.nb_manches_saison(saison, validees_seulement)
    if total_manches == 0:
        return []

    archers = Archer.objects.filter(actif=True).select_related("club")
    classement = []
    for archer in archers:
        resultats = resultats_archer(archer, saison, validees_seulement)
        if len(resultats) < total_manches:
            continue  # doit avoir participé à TOUTES les manches

        bonus_malus = BONUS_MALUS_ARC.get(archer.type_arc, 0)
        total_ajuste = sum(
            (r.points_classement or 0) + bonus_malus for r in resultats
        )
        classement.append((archer, total_ajuste, resultats))

    classement.sort(key=lambda t: t[1], reverse=True)
    return classement
