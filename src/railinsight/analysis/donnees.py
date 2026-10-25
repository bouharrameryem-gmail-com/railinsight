"""Lecture du CSV SNCF : la frontière du programme.

Tout ce qui entre est contrôlé ici, une fois : encodage, colonnes, types, noms.
Le reste du code peut ensuite faire confiance au DataFrame renvoyé, dont les
colonnes portent des noms propres et stables (voir SCHEMA).
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

TEXTE = "texte"
NOMBRE = "nombre"
SEPARATEUR = ";"


@dataclass(frozen=True)
class Colonne:
    """Une colonne attendue : son nom dans le CSV, son nom propre, son type."""

    source: str
    nom: str
    genre: str


# Contrat de schéma : colonnes attendues, dans l'ordre du DataFrame renvoyé.
# `source` = nom dans le CSV de la SNCF ; `nom` = nom utilisé partout dans le code.
# Si la SNCF renomme une colonne, on ne change que `source` : le reste du code
# continue d'utiliser `nom`. Les trois colonnes « Commentaire ... » (texte libre,
# presque vides) sont volontairement absentes. Pour en exposer une, ajoutez-la ici.
SCHEMA: tuple[Colonne, ...] = (
    Colonne("Date", "date", TEXTE),  # format AAAA-MM
    Colonne("Service", "service", TEXTE),
    Colonne("Gare de départ", "gare_depart", TEXTE),
    Colonne("Gare d'arrivée", "gare_arrivee", TEXTE),
    Colonne("Durée moyenne du trajet", "duree_moyenne", NOMBRE),
    Colonne("Nombre de circulations prévues", "prevus", NOMBRE),
    Colonne("Nombre de trains annulés", "annules", NOMBRE),
    Colonne("Nombre de trains en retard au départ", "retards_depart", NOMBRE),
    # « retardes » = moyenne sur les seuls trains en retard ;
    # « retard_moyen_ » sans « retardes » = moyenne sur tous les trains.
    Colonne(
        "Retard moyen des trains en retard au départ",
        "retard_moyen_retardes_depart",
        NOMBRE,
    ),
    Colonne("Retard moyen de tous les trains au départ", "retard_moyen_depart", NOMBRE),
    Colonne("Nombre de trains en retard à l'arrivée", "retards_arrivee", NOMBRE),
    Colonne(
        "Retard moyen des trains en retard à l'arrivée",
        "retard_moyen_retardes_arrivee",
        NOMBRE,
    ),
    Colonne(
        "Retard moyen de tous les trains à l'arrivée", "retard_moyen_arrivee", NOMBRE
    ),
    Colonne("Nombre trains en retard > 15min", "retards_sup_15min", NOMBRE),
    Colonne(
        "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)",
        "retard_moyen_sup_15min_vol",
        NOMBRE,
    ),
    Colonne("Nombre trains en retard > 30min", "retards_sup_30min", NOMBRE),
    Colonne("Nombre trains en retard > 60min", "retards_sup_60min", NOMBRE),
    Colonne("Prct retard pour causes externes", "prct_cause_externe", NOMBRE),
    Colonne(
        "Prct retard pour cause infrastructure", "prct_cause_infrastructure", NOMBRE
    ),
    Colonne("Prct retard pour cause gestion trafic", "prct_cause_trafic", NOMBRE),
    Colonne("Prct retard pour cause matériel roulant", "prct_cause_materiel", NOMBRE),
    Colonne(
        "Prct retard pour cause gestion en gare et réutilisation de matériel",
        "prct_cause_gare",
        NOMBRE,
    ),
    Colonne(
        "Prct retard pour cause prise en compte voyageurs "
        "(affluence, gestions PSH, correspondances)",
        "prct_cause_voyageurs",
        NOMBRE,
    ),
)


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
            dtype=str,  # on convertit nous-mêmes, colonne par colonne
            encoding="utf-8-sig",  # retire le BOM ajouté par Excel
            engine="python",  # tolère les champs multi-lignes (voir DATASHEET)
        )
    except pd.errors.EmptyDataError as exc:
        raise DonneesInvalides(f"fichier vide : {chemin}") from exc
    except pd.errors.ParserError as exc:
        raise DonneesInvalides(f"CSV illisible ({chemin}) : {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DonneesInvalides(f"encodage non UTF-8 ({chemin}) : {exc}") from exc


def _en_nombre(serie: pd.Series, nom: str) -> pd.Series:
    """Convertit en nombres ; signale les valeurs transformées en NaN."""
    # float64 toujours : sans cela, le type varierait (int ou float) selon le contenu
    convertie = pd.to_numeric(serie.str.strip(), errors="coerce").astype("float64")
    perdues = int(serie.notna().sum() - convertie.notna().sum())
    if perdues:
        logger.warning(
            "colonne %r : %d valeur(s) non numérique(s) remplacée(s) par NaN",
            nom,
            perdues,
        )
    return convertie
