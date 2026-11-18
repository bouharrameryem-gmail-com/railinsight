"""État de la source API et synchronisation des caches de l'application."""

import logging

import streamlit as st

from railinsight.backend.dataloader import charger_instantane
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)


def afficher_source_donnees() -> bool:
    """Affiche la fraîcheur, invalide les anciens calculs et signale les pannes."""
    try:
        with st.spinner("Connexion aux données SNCF…"):
            instantane = charger_instantane()
    except DonneesInvalides as exc:
        logger.warning("Chargement initial du site impossible : %s", exc)
        st.error(str(exc))
        return False
    version = instantane.recupere_le.isoformat()
    if st.session_state.get("version_donnees_api") != version:
        st.cache_data.clear()
        st.session_state["version_donnees_api"] = version
    st.sidebar.caption(
        "Source : API SNCF Open Data · données mensuelles\n\n"
        f"Dernier mois : {instantane.dernier_mois}\n\n"
        f"Récupération : {instantane.recupere_le:%d/%m/%Y %H:%M} UTC\n\n"
        "Vérification toutes les heures à l'ouverture ou lors d'une interaction."
    )
    if instantane.erreur:
        st.warning(
            f"{instantane.erreur} Le site utilise le dernier jeu API valide, "
            f"récupéré le {instantane.recupere_le:%d/%m/%Y à %H:%M} UTC. "
            "Nouvel essai après cinq minutes, lors d'une interaction."
        )
    return True
