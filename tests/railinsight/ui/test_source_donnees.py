"""Tests de provenance et de synchronisation des calculs du site."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from railinsight.backend.dataloader import InstantaneAPI
from railinsight.exceptions import DonneesInvalides

SCRIPT = """
import streamlit as st
from railinsight.ui.source_donnees import afficher_source_donnees
if not afficher_source_donnees():
    st.stop()
st.write("Analyses disponibles")
"""


@pytest.fixture
def source(monkeypatch):
    instantane = InstantaneAPI(
        pd.DataFrame({"date": ["2026-09"]}),
        datetime(2026, 11, 18, 12, tzinfo=UTC),
        "2026-09",
    )
    chargeur = MagicMock(return_value=instantane)
    monkeypatch.setattr("railinsight.ui.source_donnees.charger_instantane", chargeur)
    return chargeur


def test_provenance_et_invalidation_uniquement_si_nouvelle_version(source, monkeypatch):
    clear = MagicMock()
    monkeypatch.setattr("streamlit.cache_data.clear", clear)
    at = AppTest.from_string(SCRIPT).run()
    assert not at.exception
    assert "API SNCF" in at.sidebar.caption[0].value
    assert "2026-09" in at.sidebar.caption[0].value
    assert "18/11/2026 12:00" in at.sidebar.caption[0].value
    assert clear.call_count == 1
    at.run()
    assert clear.call_count == 1
    source.return_value = InstantaneAPI(
        pd.DataFrame(), datetime(2026, 11, 18, 13, tzinfo=UTC), "2026-10"
    )
    at.run()
    assert clear.call_count == 2
    assert "2026-10" in at.sidebar.caption[0].value


def test_repli_affiche_avertissement(source):
    ancien = source.return_value
    source.return_value = InstantaneAPI(
        ancien.donnees, ancien.recupere_le, ancien.dernier_mois, "API hors ligne."
    )
    at = AppTest.from_string(SCRIPT).run()
    assert not at.exception
    assert "dernier jeu API valide" in at.warning[0].value
    assert any("Analyses disponibles" in texte.value for texte in at.markdown)


def test_erreur_initiale_arrete_les_analyses(source):
    source.side_effect = DonneesInvalides("API indisponible")
    at = AppTest.from_string(SCRIPT).run()
    assert not at.exception
    assert at.error[0].value == "API indisponible"
    assert not any("Analyses disponibles" in texte.value for texte in at.markdown)
