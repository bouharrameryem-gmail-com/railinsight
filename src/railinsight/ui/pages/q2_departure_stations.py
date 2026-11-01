"""Page Q2 : gares de départ à l'origine ou victimes des retards."""

import streamlit as st

from railinsight.backend.retards_gares import RetardsParGare, charger_retards_par_gare


@st.cache_data(show_spinner="Calcul des retards par gare…")
def _retards(exclure_2020: bool) -> RetardsParGare:
    """Met en cache les tables de retards selon l'exclusion de 2020."""
    return charger_retards_par_gare(exclure_2020)