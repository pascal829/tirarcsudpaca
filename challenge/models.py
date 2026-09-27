from datetime import date

from django.core.validators import MinValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# Constantes issues du règlement
# ---------------------------------------------------------------------------

SEXE_CHOICES = [
    ("H", "Homme"),
    ("F", "Femme"),
]

TYPE_ARC_CHOICES = [
    ("AL", "Arc Libre"),
    ("APN", "Arc à Poulies Nu"),
    ("AN", "Arc Nu (Barebow)"),
    ("AD", "Arc Droit"),
    ("AC", "Arc Chasse"),
]

# Bonus/malus par manche pour la récompense spéciale "Meilleur archer du challenge" (Article 8)
BONUS_MALUS_ARC = {
    "AL": -60,   # Arc à Poulies avec viseur (= Arc Libre)
    "APN": -40,  # Arc à Poulies Nu
    "AN": 0,     # Arc Nu (Barebow)
    "AC": 40,    # Arc Chasse
    "AD": 60,    # Arc Droit
}

CATEGORIE_AGE_CHOICES = [
    ("U13", "U13"),
    ("U15", "U15"),
    ("U18", "U18"),
    ("S1", "Senior 1"),
    ("S2", "Senior 2"),
    ("S3", "Senior 3"),
]

# Barème de points par place (Article 5)
BAREME_POINTS = {
    1: 40,
    2: 30,
    3: 20,
}
POINTS_PARTICIPATION = 5  # à partir de la 4e place


class Club(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    ville = models.CharField(max_length=150, blank=True)
    code_club_ffta = models.CharField("Code club FFTA", max_length=20, blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Club"

    def __str__(self):
        return self.nom


class Archer(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    licence_ffta = models.CharField("N° licence FFTA", max_length=20, unique=True)
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="archers")
    date_naissance = models.DateField()
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    type_arc = models.CharField("Type d'arc", max_length=4, choices=TYPE_ARC_CHOICES)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "Archer"

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.club})"

    def age_sportif(self, saison=None):
        """Âge FFTA = âge atteint dans l'année civile de la saison (au 31/12)."""
        saison = saison or date.today().year
        return saison - self.date_naissance.year

    def categorie_age(self, saison=None):
        """
        Détermine la catégorie d'âge simplifiée selon le règlement:
        U13, U15, U18, Senior 1, Senior 2, Senior 3.
        Bornes usuelles FFTA (à ajuster si le comité en précise d'autres):
          U13  : <= 12 ans
          U15  : 13-14 ans
          U18  : 15-17 ans
          S1   : 18-40 ans
          S2   : 41-60 ans
          S3   : 61 ans et plus
        """
        age = self.age_sportif(saison)
        if age <= 12:
            return "U13"
        if age <= 14:
            return "U15"
        if age <= 17:
            return "U18"
        if age <= 40:
            return "S1"
        if age <= 60:
            return "S2"
        return "S3"

    def cle_categorie(self, saison=None):
        """Clé de regroupement pour les classements par catégorie (âge/sexe/arc)."""
        return (self.categorie_age(saison), self.sexe, self.type_arc)

    def libelle_categorie(self, saison=None):
        age_label = dict(CATEGORIE_AGE_CHOICES)[self.categorie_age(saison)]
        sexe_label = dict(SEXE_CHOICES)[self.sexe]
        arc_label = dict(TYPE_ARC_CHOICES)[self.type_arc]
        return f"{age_label} - {sexe_label} - {arc_label}"


def _annee_courante():
    return date.today().year


class Manche(models.Model):
    """Une manche officielle du challenge (une compétition)."""

    numero = models.PositiveIntegerField(unique=True)
    nom = models.CharField(max_length=200)
    club_organisateur = models.ForeignKey(
        Club, on_delete=models.PROTECT, related_name="manches_organisees"
    )
    date = models.DateField()
    saison = models.PositiveIntegerField(default=_annee_courante)
    validee = models.BooleanField(
        "Validée par le comité régional", default=False
    )
    nb_cibles = models.PositiveIntegerField(default=21)

    class Meta:
        ordering = ["numero"]
        verbose_name = "Manche"
        verbose_name_plural = "Manches"

    def __str__(self):
        return f"Manche {self.numero} - {self.nom}"

    @classmethod
    def nb_manches_saison(cls, saison, validees_seulement=True):
        qs = cls.objects.filter(saison=saison)
        if validees_seulement:
            qs = qs.filter(validee=True)
        return qs.count()

    @classmethod
    def seuil_participation(cls, saison, validees_seulement=True):
        """50% des manches, arrondi à l'entier inférieur (Article 6)."""
        import math

        total = cls.nb_manches_saison(saison, validees_seulement)
        return math.floor(total * 0.5)


class Resultat(models.Model):
    """Score d'un archer sur une manche donnée."""

    manche = models.ForeignKey(Manche, on_delete=models.CASCADE, related_name="resultats")
    archer = models.ForeignKey(Archer, on_delete=models.CASCADE, related_name="resultats")
    score = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    disqualifie = models.BooleanField(default=False)

    # Champs calculés et mis en cache lors de la validation du classement de la manche
    rang_categorie = models.PositiveIntegerField(null=True, blank=True)
    points_classement = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("manche", "archer")
        ordering = ["manche", "-score"]
        verbose_name = "Résultat"
        verbose_name_plural = "Résultats"

    def __str__(self):
        return f"{self.archer} - {self.manche} : {self.score} pts"
