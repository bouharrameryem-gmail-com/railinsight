"""Données de la page d'accueil : chiffres du réseau, calendrier et carte."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from railinsight.analysis.geometrie import Ligne, extraire_lignes
from railinsight.analysis.indicateurs_reseau import (
    Fenetre,
    TauxReseau,
    fenetres_annuelles,
    placer_gares,
    preparer_donnees,
    taux_par_gare,
    taux_par_mois,
    taux_sur_fenetre,
)
from railinsight.analysis.nettoyage import filtrer_service, nettoyer_regularite
from railinsight.backend.dataloader import charger_donnees
from railinsight.config import DATA_DIR
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

REFERENCE_DIR = DATA_DIR / "reference"
COORDONNEES_PATH = REFERENCE_DIR / "gares_coordonnees.csv"
RESEAU_LGV_PATH = REFERENCE_DIR / "reseau_lgv.geojson"
COLONNES_COORDONNEES = ("gare", "latitude", "longitude")


@dataclass(frozen=True, eq=False)
class DonneesAccueil:
    """Tout ce qu'affiche la page d'accueil, calculé une seule fois.

    `periode` couvre les 12 derniers mois et `courant` en donne les chiffres ;
    `precedent` donne ceux des 12 mois d'avant, ou None s'ils manquent.
    `par_mois` sert au calendrier (`taux_par_mois`), `gares` à la carte
    (`taux_par_gare` et coordonnées), et `gares_absentes` liste les gares
    sans coordonnées. `premier_mois` est le premier mois des données.
    """

    premier_mois: str
    periode: Fenetre
    courant: TauxReseau
    precedent: TauxReseau | None
    par_mois: pd.DataFrame
    gares: pd.DataFrame
    gares_absentes: tuple[str, ...]


def calculer_donnees_accueil(
    brut: pd.DataFrame, coordonnees: pd.DataFrame
) -> DonneesAccueil:
    """Calcule les chiffres, le calendrier et les gares de la page d'accueil.

    Args:
        brut: Résultat de `lire_donnees`.
        coordonnees: Résultat de `charger_coordonnees`.
    """
    donnees = preparer_donnees(filtrer_service(nettoyer_regularite(brut)))
    periode, precedente = fenetres_annuelles(donnees["mois"])
    gares, absentes = placer_gares(taux_par_gare(donnees, periode), coordonnees)
    if absentes:
        logger.warning(
            "%d gare(s) sans coordonnées, absentes de la carte : %s",
            len(absentes),
            ", ".join(absentes),
        )
    return DonneesAccueil(
        premier_mois=str(donnees["mois"].min()),
        periode=periode,
        courant=taux_sur_fenetre(donnees, periode),
        precedent=None if precedente is None else taux_sur_fenetre(donnees, precedente),
        par_mois=taux_par_mois(donnees),
        gares=gares,
        gares_absentes=absentes,
    )


def charger_coordonnees(chemin: Path = COORDONNEES_PATH) -> pd.DataFrame:
    """Lit la table des coordonnées des gares.

    Raises:
        DonneesInvalides: Si le fichier manque ou n'a pas les bonnes colonnes.
    """
    try:
        table = pd.read_csv(chemin, sep=";", encoding="utf-8")
    except FileNotFoundError as exc:
        raise DonneesInvalides(
            f"coordonnées des gares introuvables : {chemin}"
        ) from exc
    manquantes = [c for c in COLONNES_COORDONNEES if c not in table.columns]
    if manquantes:
        raise DonneesInvalides(
            "colonnes manquantes dans les coordonnées : " + ", ".join(manquantes)
        )
    table["gare"] = table["gare"].str.strip().str.upper()
    return table[list(COLONNES_COORDONNEES)]


def charger_donnees_accueil() -> DonneesAccueil:
    """Charge les données SNCF et calcule la page d'accueil."""
    return calculer_donnees_accueil(charger_donnees(), charger_coordonnees())


def charger_reseau_lgv(chemin: Path = RESEAU_LGV_PATH) -> list[Ligne] | None:
    """Lit le tracé simplifié des LGV, ou None s'il n'a pas été téléchargé.

    Le fichier est produit par `scripts/telecharger_reseau_lgv.py`.

    Raises:
        DonneesInvalides: Si le fichier existe mais n'est pas un GeoJSON valide.
    """
    if not chemin.exists():
        logger.warning("tracé des LGV absent (%s) : carte sans réseau", chemin)
        return None
    try:
        collection = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DonneesInvalides(f"tracé des LGV illisible : {chemin}") from exc
    return extraire_lignes(collection)
