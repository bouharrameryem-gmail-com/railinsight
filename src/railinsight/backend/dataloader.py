"""Alimentation API du site, indépendante du CSV conservé par les notebooks."""

import logging
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from io import StringIO
from threading import RLock

import pandas as pd
import requests

from railinsight.analysis.lecture_donnees import lire_donnees
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)
URL_API = (
    "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
    "regularite-mensuelle-tgv-aqst/exports/csv"
)
DUREE_CACHE = 3600
DELAI_NOUVEL_ESSAI = 300


@dataclass(frozen=True, eq=False)
class InstantaneAPI:
    """Jeu validé et provenance ; erreur renseignée en cas de repli explicite."""

    donnees: pd.DataFrame
    recupere_le: datetime
    dernier_mois: str
    erreur: str | None = None


def _telecharger() -> InstantaneAPI:
    """Télécharge l'export complet sans pagination et valide son schéma."""
    try:
        with requests.get(
            URL_API,
            params={"lang": "fr", "use_labels": "true", "delimiter": ";"},
            timeout=(10, 60),
        ) as reponse:
            reponse.raise_for_status()
            texte = reponse.content.decode("utf-8-sig")
    except (requests.RequestException, UnicodeDecodeError) as exc:
        raise DonneesInvalides(
            "L'API SNCF est indisponible ou sa réponse est illisible."
        ) from exc
    donnees = lire_donnees(StringIO(texte))
    dates = pd.to_datetime(donnees["date"], format="%Y-%m", errors="coerce")
    if donnees.empty or dates.isna().any():
        raise DonneesInvalides(
            "L'API SNCF a renvoyé un jeu vide ou des dates invalides."
        )
    return InstantaneAPI(
        donnees=donnees,
        recupere_le=datetime.now(UTC),
        dernier_mois=dates.max().strftime("%Y-%m"),
    )


class CacheAPI:
    """Conserve le dernier jeu valide en mémoire, avec rafraîchissement borné."""

    def __init__(self) -> None:
        """Initialise un cache propre au processus serveur."""
        self._verrou = RLock()
        self._instantane: InstantaneAPI | None = None
        self._prochain_essai = 0.0
        self._erreur: str | None = None

    def charger(self) -> InstantaneAPI:
        """Actualise après une heure ou réessaie après cinq minutes d'échec."""
        with self._verrou:
            maintenant = time.monotonic()
            if maintenant >= self._prochain_essai:
                try:
                    nouveau = _telecharger()
                except DonneesInvalides as exc:
                    logger.warning("Actualisation API SNCF impossible : %s", exc)
                    self._erreur = str(exc)
                    self._prochain_essai = time.monotonic() + DELAI_NOUVEL_ESSAI
                else:
                    self._instantane = nouveau
                    self._erreur = None
                    self._prochain_essai = time.monotonic() + DUREE_CACHE
            if self._instantane is None:
                raise DonneesInvalides(
                    f"{self._erreur} Aucun instantané API valide n'est disponible. "
                    "Réessayez dans cinq minutes."
                )
            return replace(
                self._instantane,
                donnees=self._instantane.donnees.copy(deep=True),
                erreur=self._erreur,
            )


_CACHE = CacheAPI()


def charger_instantane() -> InstantaneAPI:
    """Renvoie le jeu API et son état, sans jamais lire le CSV local."""
    return _CACHE.charger()


def charger_donnees() -> pd.DataFrame:
    """Charge les données API validées destinées à l'application."""
    return charger_instantane().donnees
