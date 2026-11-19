"""Tests de provenance locale et de conservation des caches entre visiteurs."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

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
    chargeur = MagicMock(return_value=pd.DataFrame({"mois": ["2026-08", "2026-09"]}))
    monkeypatch.setattr(
        "railinsight.ui.source_donnees.charger_donnees_nettoyees", chargeur
    )
    return chargeur


def test_provenance_et_nouveaux_visiteurs_ne_vident_pas_les_caches(source, monkeypatch):
    clear = MagicMock()
    monkeypatch.setattr("streamlit.cache_data.clear", clear)
    for _ in range(2):
        at = AppTest.from_string(SCRIPT).run()
        assert not at.exception
        assert "CSV local" in at.sidebar.caption[0].value
        assert "2026-09" in at.sidebar.caption[0].value
        assert "manuelle" in at.sidebar.caption[0].value
        at.run()
    clear.assert_not_called()


def test_erreur_initiale_arrete_les_analyses(source):
    source.side_effect = DonneesInvalides("CSV local inaccessible")
    at = AppTest.from_string(SCRIPT).run()
    assert not at.exception
    assert at.error[0].value == "CSV local inaccessible"
    assert not any("Analyses disponibles" in texte.value for texte in at.markdown)
