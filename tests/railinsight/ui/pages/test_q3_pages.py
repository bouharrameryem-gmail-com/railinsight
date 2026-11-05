"""Tests de la page profils de ponctualité."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

_PAGES_DIR = Path(__file__).parents[4] / "src" / "railinsight" / "ui" / "pages"


class TestPageProfilsPonctualite:
    def test_rendu_sans_exception(self):
        at = AppTest.from_file(
            str(_PAGES_DIR / "ponctualite_liaisons.py"), default_timeout=60
        )
        at.run()
        assert not at.exception

    def test_etat_initial_affiche_message_info(self):
        at = AppTest.from_file(
            str(_PAGES_DIR / "ponctualite_liaisons.py"), default_timeout=60
        )
        at.run()
        assert not at.exception
        assert len(at.info) > 0 or len(at.markdown) > 0
