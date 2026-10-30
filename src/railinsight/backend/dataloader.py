"""Accès de l'application aux données SNCF validées."""

import pandas as pd

from railinsight.analysis.lecture_donnees import lire_donnees
from railinsight.config import charger_config


def charger_donnees() -> pd.DataFrame:
    """Charge les données brutes et vérifie leur conformité au schéma."""
    return lire_donnees(charger_config().chemins.donnees)
