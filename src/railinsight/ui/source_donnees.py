"""Affichage de la provenance du CSV local utilisé par le site."""

import logging

import streamlit as st

from railinsight.backend.dataloader import charger_donnees_nettoyees
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)


def afficher_source_donnees() -> bool:
    """Affiche la période du jeu local et signale les erreurs de chargement."""
    try:
        donnees = charger_donnees_nettoyees()
    except DonneesInvalides as exc:
        logger.warning("Chargement initial du site impossible : %s", exc)
        st.error(str(exc))
        return False
    st.sidebar.caption(
        "Source : SNCF Open Data · CSV local\n\n"
        f"Dernier mois : {donnees['mois'].max()}\n\n"
        "Mise à jour manuelle du jeu de données."
    )
    return True
