"""Chargement local des données, partagé entre les pages Streamlit."""

from pathlib import Path

import pandas as pd
import streamlit as st

from railinsight.analysis import nettoyage
from railinsight.analysis.lecture_donnees import lire_donnees
from railinsight.analysis.nettoyage import filtrer_service, nettoyer_regularite
from railinsight.config import CLEAN_MONTHLY_PATH, RAW_CSV_PATH
from railinsight.exceptions import DonneesInvalides


@st.cache_data(show_spinner=False)
def charger_donnees() -> pd.DataFrame:
    """Lit et valide le CSV une fois, puis fournit une copie à chaque appel."""
    try:
        donnees = lire_donnees(RAW_CSV_PATH)
    except OSError as exc:
        raise DonneesInvalides(f"CSV local inaccessible : {RAW_CSV_PATH}") from exc
    dates = pd.to_datetime(donnees["date"], format="%Y-%m", errors="coerce")
    if donnees.empty or dates.isna().any():
        raise DonneesInvalides("Le CSV local est vide ou contient des dates invalides.")
    return donnees


@st.cache_data(show_spinner=False)
def charger_donnees_nettoyees() -> pd.DataFrame:
    """Réutilise le Parquet préparé, sinon nettoie le CSV une seule fois."""
    try:
        sources = [RAW_CSV_PATH, Path(__file__), Path(nettoyage.__file__)]
        if CLEAN_MONTHLY_PATH.exists() and all(
            CLEAN_MONTHLY_PATH.stat().st_mtime_ns >= source.stat().st_mtime_ns
            for source in sources
        ):
            return pd.read_parquet(CLEAN_MONTHLY_PATH)
    except (OSError, ValueError) as exc:
        raise DonneesInvalides(
            "Données préparées illisibles. Régénérez-les avec "
            "`uv run python -m railinsight.backend.dataloader`."
        ) from exc
    return nettoyer_regularite(charger_donnees())


def charger_donnees_clean() -> pd.DataFrame:
    """Charge les données nettoyées du service national (accueil et Q3)."""
    return filtrer_service(charger_donnees_nettoyees())


if __name__ == "__main__":
    CLEAN_MONTHLY_PATH.parent.mkdir(parents=True, exist_ok=True)
    nettoyer_regularite(charger_donnees()).to_parquet(CLEAN_MONTHLY_PATH, index=False)
    print(f"Données nettoyées enregistrées : {CLEAN_MONTHLY_PATH}")
