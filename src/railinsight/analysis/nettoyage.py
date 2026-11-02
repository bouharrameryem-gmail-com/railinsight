"""Nettoyage des données de régularité : fonctions pures, idempotentes, vectorisées.

Deux familles de fonctions :

- des outils génériques, utilisables sur n'importe quelle colonne
  (normaliser_nom, convertir_mois, taux, invalider_hors_bornes, retirer_doublons,
  filtrer_periode, retirer_mois) ;
- des règles propres au jeu de données SNCF (filtrer_service, ajouter_liaison,
  ajouter_minutes_retard, retirer_sans_train, nettoyer_regularite).

Chaque fonction ne modifie pas son argument, accepte sa propre sortie
(f(f(x)) == f(x)) et n'utilise aucune boucle Python. Les données arrivent de
railinsight.analysis.lecture_csv.lire_donnees, avec les noms de colonnes du SCHEMA.
"""

import logging
from collections.abc import Iterable

import pandas as pd

from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

ESPACES = "[\\s\u00a0\u202f]+"
COLONNES_REQUISES = (
    "date",
    "gare_depart",
    "gare_arrivee",
    "prevus",
    "annules",
    "retard_moyen_arrivee",
)


def normaliser_nom(serie: pd.Series) -> pd.Series:
    """Normalise les noms en supprimant les espaces superflus et en majuscules."""
    return serie.str.replace(ESPACES, " ", regex=True).str.strip().str.upper()


def convertir_mois(serie: pd.Series) -> pd.Series:
    """Convertit les mois au format AAAA-MM en dates."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    texte = serie.astype("string").str.strip()
    dates = pd.to_datetime(texte, format="%Y-%m", errors="coerce")
    perdues = int(dates.isna().sum() - serie.isna().sum())
    if perdues:
        logger.warning("%d mois illisible(s) remplacé(s) par NaT", perdues)
    return dates


def taux(
    numerateur: pd.Series, denominateur: pd.Series, pour: float = 100.0
) -> pd.Series:
    """Calcule un rapport multiplié par `pour`."""
    return numerateur / denominateur.where(denominateur != 0) * pour


def invalider_hors_bornes(
    serie: pd.Series, minimum: float | None = None, maximum: float | None = None
) -> pd.Series:
    """Remplace par NaN les valeurs hors des bornes définies."""
    hors = pd.Series(False, index=serie.index)
    if minimum is not None:
        hors |= serie < minimum
    if maximum is not None:
        hors |= serie > maximum
    if hors.any():
        logger.warning(
            "colonne %r : %d valeur(s) hors de [%s, %s] remplacée(s) par NaN",
            serie.name,
            int(hors.sum()),
            minimum,
            maximum,
        )
    return serie.mask(hors)


def retirer_doublons(df: pd.DataFrame, cle: list[str]) -> pd.DataFrame:
    """Supprime les doublons en conservant la dernière occurrence."""
    unique = df.drop_duplicates(subset=cle, keep="last").reset_index(drop=True)
    retirees = len(df) - len(unique)
    if retirees:
        logger.warning(
            "%d ligne(s) en double retirée(s) (clé : %s)", retirees, ", ".join(cle)
        )
    return unique


def filtrer_periode(
    df: pd.DataFrame,
    debut: str | None = None,
    fin: str | None = None,
    colonne: str = "mois",
) -> pd.DataFrame:
    """Filtre les lignes selon une période, bornes incluses."""
    garder = pd.Series(True, index=df.index)
    if debut:
        garder &= df[colonne] >= debut
    if fin:
        garder &= df[colonne] <= fin
    return df[garder].reset_index(drop=True)


def retirer_mois(
    df: pd.DataFrame, mois: Iterable[str], colonne: str = "mois"
) -> pd.DataFrame:
    """Retire les lignes correspondant aux mois indiqués."""
    exclus = df[colonne].isin(list(mois))
    if exclus.any():
        logger.info("%d ligne(s) retirée(s) (mois exclus)", int(exclus.sum()))
    return df[~exclus].reset_index(drop=True)


def filtrer_service(df: pd.DataFrame, service: str = "National") -> pd.DataFrame:
    """Conserve les lignes du service demandé.

    Raises:
        DonneesInvalides: si aucune ligne ne correspond au service.
    """
    gardees = df[df["service"] == service]
    if gardees.empty:
        presents = sorted(df["service"].dropna().unique())
        raise DonneesInvalides(
            f"aucune ligne pour le service {service!r}, services présents : {presents}"
        )
    return gardees.reset_index(drop=True)


def ajouter_liaison(
    df: pd.DataFrame, depart: str = "gare_depart", arrivee: str = "gare_arrivee"
) -> pd.DataFrame:
    """Ajoute les gares ordonnées et l'identifiant de liaison."""
    resultat = df.copy()
    a_avant = df[depart] <= df[arrivee]
    resultat["gare_a"] = df[depart].where(a_avant, df[arrivee])
    resultat["gare_b"] = df[arrivee].where(a_avant, df[depart])
    resultat["liaison"] = resultat["gare_a"] + " - " + resultat["gare_b"]
    return resultat


def ajouter_minutes_retard(
    df: pd.DataFrame, retard_moyen: str = "retard_moyen_arrivee"
) -> pd.DataFrame:
    """Ajoute les volumes nécessaires à l'agrégation des retards.

    Les minutes de retard sont calculées en multipliant le retard moyen par
    le nombre de trains circulés. La moyenne agrégée doit ensuite être calculée
    sur les seuls trains dont le retard est connu (`circules_mesures`).
    """
    resultat = df.copy()
    resultat["circules"] = resultat["prevus"] - resultat["annules"]
    resultat["minutes_retard"] = resultat[retard_moyen] * resultat["circules"]
    resultat["circules_mesures"] = resultat["circules"].where(
        resultat["minutes_retard"].notna()
    )
    return resultat


def retirer_sans_train(df: pd.DataFrame, colonne: str = "prevus") -> pd.DataFrame:
    """Retire les lignes sans train prévu."""
    sans_train = ~(df[colonne] > 0)
    if sans_train.any():
        logger.info("%d ligne(s) sans train prévu retirée(s)", int(sans_train.sum()))
    return df[~sans_train].reset_index(drop=True)


def _exiger_colonnes(df: pd.DataFrame, colonnes: tuple[str, ...]) -> None:
    """Vérifie la présence des colonnes requises."""
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise DonneesInvalides(
            "colonnes manquantes pour le nettoyage : " + ", ".join(manquantes)
        )


def nettoyer_regularite(brut: pd.DataFrame) -> pd.DataFrame:
    """Applique les règles de nettoyage sans supprimer de lignes.

    Convertit les dates, normalise les gares, signale les doublons et ajoute
    les indicateurs de liaison et de retard.
    """
    _exiger_colonnes(brut, COLONNES_REQUISES)
    df = brut.copy()
    df["date"] = convertir_mois(df["date"])
    df["mois"] = df["date"].dt.strftime("%Y-%m")
    for colonne in ("gare_depart", "gare_arrivee"):
        df[colonne] = normaliser_nom(df[colonne])

    doublons = int(df.duplicated(subset=["mois", "gare_depart", "gare_arrivee"]).sum())
    if doublons:
        logger.warning(
            "%d ligne(s) en double sur (mois, gare_depart, gare_arrivee), conservées",
            doublons,
        )

    return ajouter_minutes_retard(ajouter_liaison(df))
