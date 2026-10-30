"""Chargement partagé des données de régularité pour les pages Streamlit.

Une seule fonction, mise en cache : toutes les pages qui l'appellent partagent
le même résultat, et le fichier n'est lu et nettoyé qu'une fois par session.
"""

import pandas as pd
import streamlit as st

from railinsight.analysis.nettoyage import filtrer_service, nettoyer_regularite
from railinsight.backend.dataloader import charger_donnees


@st.cache_data(show_spinner="Chargement des données…")
def charger_table_regularite() -> pd.DataFrame:
    """Charge le CSV, applique le nettoyage commun et garde le service national.

    Returns:
        Le résultat de `nettoyer_regularite`, filtré sur un service, avec les
        colonnes du SCHEMA, `mois`, `liaison`, `circules` et `minutes_retard`.

    Raises:
        ConfigInvalide: configuration invalide.
        FileNotFoundError: le CSV n'existe pas à l'emplacement configuré.
        DonneesInvalides: CSV vide, illisible ou incomplet, ou aucun service national.
    """
    return filtrer_service(nettoyer_regularite(charger_donnees()))
