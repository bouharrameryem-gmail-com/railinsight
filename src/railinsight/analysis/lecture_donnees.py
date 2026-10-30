"""Lecture du CSV SNCF : la frontière du programme.

Tout ce qui entre est contrôlé ici, une fois : encodage, colonnes, types, noms.
Le reste du code peut ensuite faire confiance au DataFrame renvoyé, dont les
colonnes portent des noms propres et stables (voir SCHEMA).
"""

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
    """Compare les en-têtes réels du fichier au SCHEMA (reconnaissance tolérante).
 
    Utile pour découvrir un nouvel export ou compléter le schéma.
 
    Returns:
        (hors_schema, manquantes) : colonnes du fichier que le schéma ignore, puis
        colonnes du schéma (nom CSV) absentes du fichier.
    """
    en_tetes = list(_lire_csv(chemin).columns)
    vus = {normaliser(nom) for nom in en_tetes}
    connus = {normaliser(c.source) for c in SCHEMA}
    hors_schema = [nom for nom in en_tetes if normaliser(nom) not in connus]
    manquantes = [c.source for c in SCHEMA if normaliser(c.source) not in vus]
    return hors_schema, manquantes


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, ponctuation et espaces réduits à un espace.
 
    Sert à reconnaître un en-tête malgré des différences de casse, d'accents,
    d'espaces ou d'apostrophe : « Gare d'arrivée » == « GARE D’ARRIVEE ».
    """
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sans_accents).strip()


def lire_donnees(chemin: str | Path) -> pd.DataFrame:
    """Lit le CSV, contrôle son schéma et renvoie un DataFrame typé.

    Args:
        chemin: chemin du CSV (en général cfg.chemins.donnees).

    Returns:
        Un DataFrame qui contient exactement les colonnes de SCHEMA, dans cet
        ordre, sous leur nom propre (`Colonne.nom`). Colonnes « texte » : chaînes
        sans espaces en bordure. Colonnes « nombre » : float, avec NaN quand la
        valeur n'est pas un nombre.

    Raises:
        FileNotFoundError: le fichier n'existe pas.
        DonneesInvalides: fichier vide, illisible, ou colonnes manquantes.
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
    """Lit tout en texte (aucune devinette de types) et traduit les erreurs."""
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
    """Convertit en nombres ; signale les valeurs transformées en NaN."""
    convertie = pd.to_numeric(serie.str.strip(), errors="coerce").astype("float64")
    perdues = int(serie.notna().sum() - convertie.notna().sum())
    if perdues:
        logger.warning(
            "colonne %r : %d valeur(s) non numérique(s) remplacée(s) par NaN",
            nom,
            perdues,
        )
    return convertie
