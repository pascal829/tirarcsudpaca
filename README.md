# Challenge Arc et Nature Sud PACA — Application Django

Application de gestion du **Challenge Arc et Nature Sud PACA** :
inscription des clubs, des archers, des manches (compétitions),
saisie des résultats et calcul automatique des classements,
conformément au règlement officiel v1.0 du 14/06/2025.

## Fonctionnalités

- **Clubs** : gestion des clubs affiliés FFTA.
- **Archers** : licence FFTA, club, date de naissance, sexe, type d'arc.
  La catégorie d'âge (U13/U15/U18/S1/S2/S3) est calculée automatiquement.
- **Manches** : création, validation par le comité, saisie des scores.
- **Calcul automatique** (bouton "action" dans l'admin, sur chaque manche) :
  - Attribution des rangs et des points par catégorie (40/30/20/5 pts — Article 5),
    avec gestion des ex-æquo.
- **Classements** (pages publiques + admin) :
  - Classement individuel par catégorie (âge/sexe/type d'arc), basé sur
    la **moyenne des 3 meilleurs scores** (Article 7).
  - Classement par club (cumul des points, Article 5/7).
  - Classement général (cumul des points sur les manches retenues, Article 7).
  - Récompense spéciale **« Meilleur archer du challenge »** (Article 8) :
    réservée aux archers ayant disputé **toutes** les manches, avec le
    système de bonus/malus par type d'arc (–60 à +60 points/manche).
  - Application des **conditions d'éligibilité** (Article 6 : ≥ 50 % des
    manches, arrondi à l'entier inférieur, et catégorie comptant au moins
    2 archers éligibles) et des **critères de départage** (Article 7 :
    victoires > meilleur score > nombre de participations).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate  # sous Windows : venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Puis ouvrir :
- http://127.0.0.1:8000/ : pages publiques (manches, classements)
- http://127.0.0.1:8000/admin/ : back-office (saisie des clubs, archers,
  manches, résultats)

## Utilisation courante

1. Créer les **clubs** (Article 2) dans l'admin.
2. Créer les **archers** licenciés (Article 3), avec leur type d'arc et
   catégorie déduite automatiquement.
3. Créer une **manche** (Article 4), puis saisir les **résultats** (score
   par archer) directement dans la fiche de la manche.
4. Une fois tous les scores saisis, utiliser l'action
   **« Valider les manches sélectionnées et recalculer le classement »**
   (ou « Recalculer le classement ») dans la liste des manches : cela
   attribue les rangs et les points par catégorie (Article 5).
5. Les classements se mettent à jour automatiquement sur les pages
   publiques (`/classement/individuel/`, `/classement/club/`,
   `/classement/general/`, `/classement/meilleur-archer/`), filtrables
   par saison via `?saison=2025`.

## Points d'attention / à ajuster avec le comité

- Les **bornes d'âge** U13/U15/U18/S1/S2/S3 (`Archer.categorie_age` dans
  `challenge/models.py`) sont des valeurs usuelles FFTA par défaut ; à
  confirmer/ajuster si le comité utilise d'autres bornes.
- Le **nombre de manches officielles** (Article 2, "[nombre à préciser]")
  n'est pas fixé en dur : il correspond simplement au nombre de manches
  créées et validées pour la saison, ce qui rend l'appli flexible.
- Le champ "responsable des réclamations" (Article 11, "……") n'est pas
  encore renseigné dans le règlement fourni ; aucune fonctionnalité de
  réclamation n'a donc été développée, mais elle peut être ajoutée
  facilement si besoin (ex. formulaire de contestation avec délai de 7
  jours).

## Structure du projet

```
arcsudpaca/
├── arcsudpaca/          # configuration du projet Django
├── challenge/
│   ├── models.py        # Club, Archer, Manche, Resultat
│   ├── services.py      # toute la logique métier des classements
│   ├── admin.py         # back-office (saisie + actions de calcul)
│   ├── views.py / urls.py / templates/  # pages publiques
├── requirements.txt
└── manage.py
```

La logique de classement est isolée dans `challenge/services.py` :
chaque règle du règlement (points par rang, moyenne des 3 meilleurs
scores, éligibilité, bonus/malus, départage) y correspond à une
fonction dédiée et commentée, ce qui facilite les ajustements futurs
si le règlement évolue.
