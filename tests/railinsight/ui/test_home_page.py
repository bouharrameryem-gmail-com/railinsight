"""Tests for the home page via Streamlit AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from railinsight.analysis.lecture_donnees import lire_donnees
from railinsight.config import charger_config

# st.page_link requires st.navigation context, so tests must run through the
# full app entrypoint (app.py) rather than home.py directly.
_ROOT = Path(__file__).parents[3]


@pytest.fixture(autouse=True)
def source_hors_reseau(monkeypatch):
    """Garde les tests de l'accueil indépendants de la disponibilité de SNCF."""
    monkeypatch.setattr(
        "railinsight.ui.source_donnees.afficher_source_donnees", lambda: True
    )
    monkeypatch.setattr(
        "railinsight.backend.profils_ponctualite.charger_donnees",
        lambda: lire_donnees(charger_config().chemins.donnees),
    )


def test_home_page_renders():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    assert not at.exception


def test_home_page_has_content():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    # Hero is rendered as HTML (st.markdown) — page must have markdown content
    assert len(at.markdown) > 0
