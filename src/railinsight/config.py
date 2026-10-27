"""Chargement et validation de la configuration (config/defaut.yaml).

Les valeurs vivent uniquement dans le YAML. Ce module ne contient que la
structure (dataclasses), les types et les règles de validation.
"""

import os
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

import yaml

from railinsight.exceptions import ConfigInvalide
from railinsight.utils.validation import (
    verifier_entier,
    verifier_nombre,
    verifier_periode,
)

# The package lives at src/railinsight/, so three .parent calls reach the repo root.
PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

RAW_CSV_PATH = RAW_DATA_DIR / "regularite-mensuelle-tgv-aqst.csv"

CLEAN_MONTHLY_PATH = PROCESSED_DATA_DIR / "clean_monthly.parquet"
ROUTE_FEATURES_PATH = PROCESSED_DATA_DIR / "route_features.parquet"
NETWORK_MONTHLY_PATH = PROCESSED_DATA_DIR / "network_monthly.parquet"
QUALITY_REPORT_PATH = PROCESSED_DATA_DIR / "quality_report.json"
KNOWN_EVENTS_PATH = CONFIG_DIR / "known_events.csv"

DEFAULT_MIN_MONTHS: int = 24
DEFAULT_EXCLUSION: str = "known"
DEFAULT_ADJUST_DURATION: bool = False

RACINE = Path(__file__).resolve().parents[2]  # racine du dépôt
DEFAUT = RACINE / "config" / "defaut.yaml"


# ---------- les sections (une dataclass par bloc du YAML) ----------


@dataclass(frozen=True)
class Chemins:
    """Chemins du projet, convertis en chemins absolus depuis la racine."""

    donnees: Path
    traitees: Path
    modeles: Path

    def __post_init__(self) -> None:
        """Vérifie que chaque chemin est renseigné, puis le rend absolu."""
        for champ in fields(self):
            valeur = getattr(self, champ.name)
            if not isinstance(valeur, str | Path) or not str(valeur).strip():
                raise ConfigInvalide(f"clé absente ou vide : 'chemins.{champ.name}'")
            # frozen=True interdit `self.x = ...` ; object.__setattr__ le contourne
            object.__setattr__(self, champ.name, RACINE / valeur)


@dataclass(frozen=True)
class ScoreFiabilite:
    """Paramètres de l'analyse « score de fiabilité » (notebook de Meryem)."""

    periode_debut: str | None
    periode_fin: str | None
    min_trains: int
    poids: float
    cap_annulation: float
    cap_retard: float
    gare_a_suivre: str | None
    top_n: int

    def __post_init__(self) -> None:
        """Valide chaque paramètre de l'analyse."""
        verifier_periode("score_fiabilite.periode_debut", self.periode_debut)
        verifier_periode("score_fiabilite.periode_fin", self.periode_fin)
        debut, fin = self.periode_debut, self.periode_fin
        if debut and fin and debut > fin:
            raise ConfigInvalide(
                "'score_fiabilite.periode_debut' doit être <= 'periode_fin'"
            )
        verifier_entier("score_fiabilite.min_trains", self.min_trains, minimum=1)
        verifier_nombre("score_fiabilite.poids", self.poids, minimum=0, maximum=1)
        verifier_nombre(
            "score_fiabilite.cap_annulation",
            self.cap_annulation,
            minimum=0,
            strict=True,
        )
        verifier_nombre(
            "score_fiabilite.cap_retard", self.cap_retard, minimum=0, strict=True
        )
        gare = self.gare_a_suivre
        if gare is not None and not (isinstance(gare, str) and gare.strip()):
            raise ConfigInvalide(
                "'score_fiabilite.gare_a_suivre' doit valoir null ou un nom de "
                f"gare, reçu : {gare!r}"
            )
        verifier_entier("score_fiabilite.top_n", self.top_n, minimum=1)


@dataclass(frozen=True)
class Q3Config:
    """Canonical parameters for the Q3 punctuality profiling analysis."""

    feature_set: str
    exclusion: str
    min_months: int
    scaler: str

    def __post_init__(self) -> None:
        """Validate Q3 analysis parameters."""
        valid_feature_sets = {"v3", "fixed", "composite"}
        if self.feature_set not in valid_feature_sets:
            raise ConfigInvalide(
                f"'q3.feature_set' doit être l'un de {valid_feature_sets}, "
                f"reçu : {self.feature_set!r}"
            )
        valid_exclusions = {"none", "known", "data"}
        if self.exclusion not in valid_exclusions:
            raise ConfigInvalide(
                f"'q3.exclusion' doit être l'un de {valid_exclusions}, "
                f"reçu : {self.exclusion!r}"
            )
        verifier_entier("q3.min_months", self.min_months, minimum=1)
        valid_scalers = {"power", "standard"}
        if self.scaler not in valid_scalers:
            raise ConfigInvalide(
                f"'q3.scaler' doit être l'un de {valid_scalers}, "
                f"reçu : {self.scaler!r}"
            )


# >>> Pour ajouter votre analyse : une dataclass ici <<<


@dataclass(frozen=True)
class Config:
    """Configuration complète : un champ par bloc du YAML."""

    graine: int
    chemins: Chemins
    score_fiabilite: ScoreFiabilite
    q3: Q3Config
    # >>> et un champ ici, avec le même nom que la section du YAML <<<


# ---------- lecture, fusion, validation ----------


def _lire(chemin: Path) -> dict:
    """Lit un fichier YAML ; toute erreur devient une ConfigInvalide."""
    try:
        with open(chemin, encoding="utf-8") as f:
            contenu = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigInvalide(
            f"fichier de configuration introuvable : {chemin}"
        ) from None
    except yaml.YAMLError as erreur:
        raise ConfigInvalide(f"YAML invalide dans {chemin} : {erreur}") from None
    except (UnicodeDecodeError, OSError) as erreur:
        raise ConfigInvalide(
            f"fichier de configuration illisible ({chemin}) : {erreur}"
        ) from erreur

    if contenu is None:
        return {}
    if not isinstance(contenu, dict):
        raise ConfigInvalide(f"{chemin} : la racine doit être un dictionnaire")
    return contenu


def _fusion(base: dict, surcharge: dict) -> dict:
    """Fusionne récursivement ; la surcharge l'emporte, le reste est conservé."""
    resultat = dict(base)
    for cle, valeur in surcharge.items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = _fusion(resultat[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


def _construire(classe: type, nom: str, brut: object) -> object:
    """Construit une section : refuse les clés inconnues et les clés absentes."""
    if not isinstance(brut, dict):
        raise ConfigInvalide(f"section '{nom}' absente ou invalide")
    attendues = [champ.name for champ in fields(classe)]
    for cle in brut:
        if cle not in attendues:
            raise ConfigInvalide(f"clé inconnue : '{nom}.{cle}'")
    for cle in attendues:
        if cle not in brut:
            raise ConfigInvalide(f"clé absente : '{nom}.{cle}'")
    return classe(**brut)


def valider(brut: dict) -> Config:
    """Valide le dictionnaire fusionné et construit la Config."""
    types = get_type_hints(Config)
    for cle in brut:
        if cle not in types:
            raise ConfigInvalide(f"clé inconnue : '{cle}'")

    graine = brut.get("graine")
    if not isinstance(graine, int) or isinstance(graine, bool):
        raise ConfigInvalide(f"'graine' doit être un entier, reçu : {graine!r}")

    sections = {
        nom: _construire(classe, nom, brut.get(nom))
        for nom, classe in types.items()
        if is_dataclass(classe)
    }
    return Config(graine=graine, **sections)


def charger_config(chemin=None, environ=None) -> Config:
    """Charge defaut.yaml, le surcharge avec un fichier optionnel, puis valide.

    Args:
        chemin: YAML de surcharge, relatif à la racine du projet. Il ne contient
            que les clés à modifier. Par défaut : variable RAILINSIGHT_CONFIG.
        environ: variables d'environnement (os.environ par défaut ; utile en test).

    Raises:
        ConfigInvalide: fichier introuvable, clé inconnue ou valeur invalide.
    """
    environ = os.environ if environ is None else environ
    chemin = chemin or environ.get("RAILINSIGHT_CONFIG")

    brut = _lire(DEFAUT)
    if chemin:
        brut = _fusion(brut, _lire(RACINE / chemin))
    return valider(brut)
