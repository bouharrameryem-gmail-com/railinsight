"""Chargement et validation de la configuration (config/defaut.yaml).

Les valeurs vivent uniquement dans le YAML. Ce module ne contient que la
structure (dataclasses), les types et les règles de validation.
"""

import os
import re
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

import yaml

from railinsight.exceptions import ConfigInvalide

RACINE = Path(__file__).resolve().parents[2]  # racine du dépôt
DEFAUT = RACINE / "config" / "defaut.yaml"

_PERIODE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


# ---------- outils de validation (à réutiliser dans vos sections) ----------


def verifier_entier(cle: str, valeur: object, minimum: int | None = None) -> None:
    """Exige un entier (booléen exclu), éventuellement >= minimum."""
    if not isinstance(valeur, int) or isinstance(valeur, bool):
        raise ConfigInvalide(f"'{cle}' doit être un entier, reçu : {valeur!r}")
    if minimum is not None and valeur < minimum:
        raise ConfigInvalide(f"'{cle}' doit être >= {minimum}, reçu : {valeur!r}")


def verifier_nombre(
    cle: str,
    valeur: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strict: bool = False,
) -> None:
    """Exige un nombre dans l'intervalle voulu (bornes exclues si strict)."""
    if isinstance(valeur, bool) or not isinstance(valeur, int | float):
        raise ConfigInvalide(f"'{cle}' doit être un nombre, reçu : {valeur!r}")
    bas = minimum is None or (valeur > minimum if strict else valeur >= minimum)
    haut = maximum is None or (valeur < maximum if strict else valeur <= maximum)
    if not (bas and haut):
        signe_bas, signe_haut = (">", "<") if strict else (">=", "<=")
        regles = []
        if minimum is not None:
            regles.append(f"{signe_bas} {minimum}")
        if maximum is not None:
            regles.append(f"{signe_haut} {maximum}")
        raise ConfigInvalide(
            f"'{cle}' doit être {' et '.join(regles)}, reçu : {valeur!r}"
        )


def verifier_periode(cle: str, valeur: object) -> None:
    """Exige null ou une chaîne 'AAAA-MM'."""
    if valeur is not None and not (
        isinstance(valeur, str) and _PERIODE.fullmatch(valeur)
    ):
        raise ConfigInvalide(
            f"'{cle}' doit valoir null ou 'AAAA-MM', reçu : {valeur!r}"
        )


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


# >>> Pour ajouter votre analyse : une dataclass ici (voir le guide d'équipe) <<<


@dataclass(frozen=True)
class Config:
    """Configuration complète : un champ par bloc du YAML."""

    graine: int
    chemins: Chemins
    score_fiabilite: ScoreFiabilite
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
