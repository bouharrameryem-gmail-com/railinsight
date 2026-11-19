"""Tests de la page d'accueil via Streamlit AppTest."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.exceptions import DonneesInvalides


APP = Path(__file__).parents[3] / "app.py"


@pytest.fixture
def accueil(monkeypatch, brut_reseau, coordonnees_reseau):
    """Affiche l'application avec des données locales contrôlées."""
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.accueil.charger_donnees", lambda: brut_reseau
    )
    monkeypatch.setattr(
        "railinsight.backend.accueil.charger_coordonnees", lambda: coordonnees_reseau
    )
    monkeypatch.setattr("railinsight.backend.accueil.charger_reseau_lgv", lambda: None)
    yield AppTest.from_file(str(APP), default_timeout=30)
    st.cache_data.clear()


def _espaces(texte):
    """Remplace les espaces insécables par des espaces simples."""
    return texte.replace("\u00a0", " ")


def _texte(page, morceau):
    return any(morceau in _espaces(bloc.value) for bloc in page.markdown)


def test_accueil_raconte_le_reseau(accueil):
    accueil.run()

    assert not accueil.exception
    assert not accueil.error
    assert _texte(accueil, "Pourquoi votre TGV arrive-t-il en retard ?")
    # 3 328 retards pour 21 480 trains en 2024 : 1 TGV sur 6.
    assert _texte(accueil, "1 TGV sur 6</strong>")
    assert _texte(accueil, "liaison par liaison, depuis janvier 2023.")
    assert _texte(
        accueil,
        "La gare la plus touchée : Lyon Part Dieu, où 1 TGV sur 5 arrive en retard.",
    )
    assert [_espaces(titre.value) for titre in accueil.subheader] == [
        "Le mois le plus difficile : juillet 2024, avec 1 TGV sur 5 en retard",
        "Une question par page, à lire dans l'ordre ou séparément",
    ]
    assert len(accueil.get("plotly_chart")) == 2


def test_chiffres_et_evolution(accueil):
    accueil.run()

    assert _texte(accueil, ">1 sur 6<")
    assert _texte(accueil, ">1 sur 180<")
    assert _texte(accueil, "En hausse de 7,7 point sur un an")
    assert _texte(accueil, "Stable sur un an")
    assert any("2 gares placées sur 3" in legende.value for legende in accueil.caption)


def test_sommaire_en_quatre_chapitres(accueil):
    accueil.run()

    for numero, role, auteur in (
        ("01", "Constat", "Michelle"),
        ("02", "Causes", "Éric"),
        ("03", "Profils", "Bachelard"),
        ("04", "Verdict", "Meryem"),
    ):
        assert _texte(accueil, f">{numero}</p>")
        assert _texte(accueil, f">{role}</span>")
        assert _texte(accueil, f"· par {auteur}")
    assert any(volet.label == "Méthode et sources" for volet in accueil.expander)


def test_commencer_ouvre_le_premier_chapitre(accueil, caplog):
    accueil.run()

    accueil.button(key="accueil_commencer").click().run()

    assert not accueil.exception
    assert not _texte(accueil, "Pourquoi votre TGV arrive-t-il en retard ?")
    assert "commence l'enquête" in caplog.text


def test_donnees_indisponibles(accueil, monkeypatch):
    def echouer():
        raise DonneesInvalides("Fichier invalide.")

    monkeypatch.setattr("railinsight.backend.accueil.charger_donnees", echouer)

    accueil.run()

    assert not accueil.exception
    assert accueil.info[0].value == (
        "Les chiffres du réseau sont momentanément indisponibles."
    )
    # La question et le sommaire restent accessibles.
    assert _texte(accueil, "Pourquoi votre TGV arrive-t-il en retard ?")
    assert _texte(accueil, ">Constat</span>")
    assert not accueil.get("plotly_chart")


def test_erreur_inattendue_journalisee(accueil, monkeypatch, caplog):
    def planter():
        raise RuntimeError("panne de test")

    monkeypatch.setattr("railinsight.backend.accueil.charger_donnees", planter)

    accueil.run()

    assert not accueil.exception
    assert "panne de test" in caplog.text