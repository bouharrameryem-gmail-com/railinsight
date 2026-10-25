"""Accès de l'application aux données SNCF validées."""

import pandas as pd

from railinsight.analysis.donnees import lire_donnees
from railinsight.config import charger_config


def charger_donnees() -> pd.DataFrame:
    """Charge le CSV brut (chemin de la configuration) avec contrôle du schéma.

    Raises:
        ConfigInvalide: configuration invalide.
        FileNotFoundError: le CSV n'existe pas à l'emplacement configuré.
        DonneesInvalides: le CSV est vide, illisible ou incomplet.
    """
    return lire_donnees(charger_config().chemins.donnees)
