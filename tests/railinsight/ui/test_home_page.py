"""Tests for the home page via Streamlit AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# st.page_link requires st.navigation context, so tests must run through the
# full app entrypoint (app.py) rather than home.py directly.
_ROOT = Path(__file__).parents[3]


@pytest.fixture(autouse=True)
def source_hors_reseau(monkeypatch):
    """Garde les tests de l'accueil indépendants de la disponibilité de SNCF."""

    def interdire_reseau(*args, **kwargs):
        raise AssertionError("L'accueil ne doit pas télécharger les données.")

    monkeypatch.setattr("requests.get", interdire_reseau)


def test_home_page_renders():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    assert not at.exception
    assert not at.error
    assert "CSV local" in at.sidebar.caption[0].value


def test_home_page_has_content():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    # Hero is rendered as HTML (st.markdown) — page must have markdown content
    assert len(at.markdown) > 0
