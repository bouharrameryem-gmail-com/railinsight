"""Lecture et validation du fichier CSV SNCF."""

import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from railinsight.analysis.shema import SCHEMA
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

TEXTE = "texte"
NOMBRE = "nombre"
SEPARATEUR = ";"


def comparer_colonnes(chemin: str | Path) -> tuple[list[str], list[str]]:
    """Compare les colonnes du CSV à celles définies dans le schéma."""
    en_tetes = list(_lire_csv(chemin).columns)
    vus = {normaliser(nom) for nom in en_tetes}
    connus = {normaliser(c.source) for c in SCHEMA}
    hors_schema = [nom for nom in en_tetes if normaliser(nom) not in connus]
    manquantes = [c.source for c in SCHEMA if normaliser(c.source) not in vus]
    return hors_schema, manquantes


def normaliser(texte: str) -> str:
    """Normalise un texte pour faciliter la comparaison des noms de colonnes."""
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sans_accents).strip()


def lire_donnees(chemin: str | Path) -> pd.DataFrame:
    """Lit le CSV, vérifie son schéma et convertit les colonnes.

    Les colonnes renvoyées portent les noms et types définis dans SCHEMA.
    Les valeurs numériques invalides sont remplacées par NaN.
    """
    brut = _lire_csv(chemin)
    en_tetes = {normaliser(nom): nom for nom in brut.columns}

    manquantes = [c.source for c in SCHEMA if normaliser(c.source) not in en_tetes]
    if manquantes:
        raise DonneesInvalides("colonnes manquantes : " + ", ".join(manquantes))

    colonnes = {}
    for colonne in SCHEMA:
        serie = brut[en_tetes[normaliser(colonne.source)]]
        if colonne.genre == NOMBRE:
            colonnes[colonne.nom] = _en_nombre(serie, colonne.nom)
        else:
            colonnes[colonne.nom] = serie.str.strip()
    return pd.DataFrame(colonnes)


def _lire_csv(chemin: str | Path) -> pd.DataFrame:
    """Lit le CSV en texte et traduit les erreurs de lecture."""
    try:
        return pd.read_csv(
            chemin,
            sep=SEPARATEUR,
            dtype=str,
            encoding="utf-8-sig",
            engine="python",
        )
    except pd.errors.EmptyDataError as exc:
        raise DonneesInvalides(f"fichier vide : {chemin}") from exc
    except pd.errors.ParserError as exc:
        raise DonneesInvalides(f"CSV illisible ({chemin}) : {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DonneesInvalides(f"encodage non UTF-8 ({chemin}) : {exc}") from exc


def _en_nombre(serie: pd.Series, nom: str) -> pd.Series:
    """Convertit une série en nombres et signale les valeurs invalides."""
    convertie = pd.to_numeric(serie.str.strip(), errors="coerce").astype("float64")
    perdues = int(serie.notna().sum() - convertie.notna().sum())
    if perdues:
        logger.warning(
            "colonne %r : %d valeur(s) non numérique(s) remplacée(s) par NaN",
            nom,
            perdues,
        )
    return convertie
