"""Tests de la page Q2 : récit, réglages, texte dynamique et journalisation."""

import logging
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.exceptions import DonneesInvalides

PAGE = (
    Path(__file__).parents[4]
    / "src"
    / "railinsight"
    / "ui"
    / "pages"
    / "q2_departure_stations.py"
)


@pytest.fixture
def page_q2(monkeypatch, raw):
    """Affiche la page avec des données locales contrôlées."""
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.retards_gares.charger_donnees", lambda: raw
    )
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def _texte(page, morceau):
    """Renvoie le premier texte Markdown de la page qui contient `morceau`."""
    return next(texte.value for texte in page.markdown if morceau in texte.value)


def _total_retards(page):
    """Renvoie la légende qui donne le nombre de trains arrivés en retard."""
    return next(
        legende.value
        for legende in page.caption
        if "trains arrivés en retard" in legende.value
    )


def test_page_deroule_les_cinq_sections(page_q2):
    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert not page_q2.warning
    assert [titre.value for titre in page_q2.subheader] == [
        "Un retard peut naître sur place, être importé, ou venir de l'extérieur",
        "PARIS est en tête des deux côtés : elle fabrique et encaisse le plus "
        "de retards",
        "Aucune gare n'atteint le seuil choisi",
        "2 gares fabriquent et encaissent à la fois",
        "Choisissez une gare : la page vous la raconte",
    ]
    assert len(page_q2.get("plotly_chart")) == 6
    assert "160 trains arrivés en retard" in _total_retards(page_q2).replace(
        "\u202f", " "
    )
    volets = [volet.label for volet in page_q2.expander]
    assert "Méthode et limites" in volets
    assert "Voir le détail des rangs" in volets


def test_question_en_grand_et_chiffres_cles(page_q2):
    page_q2.run()

    assert any(texte.value.startswith("## Quand votre TGV") for texte in page_q2.markdown)
    assert len(page_q2.metric) == 4
    assert page_q2.metric[0].value == "2"


def test_portrait_de_la_gare_par_defaut(page_q2):
    page_q2.run()

    portrait = _texte(page_q2, "des retards sont importés")
    assert "font-size:1.3rem" in portrait
    assert "proche de la moyenne des gares" in portrait
    assert "la 1re gare sur 2" in portrait
    # PARIS n'a que 150 retards, sous le seuil par défaut de 1 000.
    assert "à lire avec prudence" in portrait


def test_vue_par_mois_nomme_le_mois_le_plus_charge(page_q2):
    page_q2.run()

    page_q2.radio[0].set_value("Par mois").run()

    assert not page_q2.exception
    assert not page_q2.error
    assert "Son mois le plus chargé est janvier 2024" in _texte(
        page_q2, "des retards sont importés"
    )
    assert len(page_q2.get("plotly_chart")) == 6


def test_exclure_2020_change_les_chiffres(page_q2):
    page_q2.run()
    avant = _total_retards(page_q2)

    page_q2.toggle[0].set_value(False).run()

    assert not page_q2.exception
    assert not page_q2.error
    assert _total_retards(page_q2) != avant


def test_seuil_a_zero_affiche_les_classements_en_parts(page_q2):
    page_q2.run()

    page_q2.slider[0].set_value(0).run()

    assert not page_q2.exception
    assert not any("Aucune gare n'atteint" in info.value for info in page_q2.info)
    assert len(page_q2.get("plotly_chart")) == 8
    assert page_q2.subheader[2].value.startswith(
        "Rapportée à son trafic, PARIS est la plus exposée"
    )
    assert "à lire avec prudence" not in _texte(page_q2, "des retards sont importés")


def test_reglage_journalise(page_q2, caplog):
    page_q2.run()

    with caplog.at_level(logging.INFO, logger="railinsight"):
        page_q2.toggle[0].set_value(False).run()

    assert "exclure_2020 = False" in caplog.text


def test_donnees_invalides_affichent_un_avertissement(page_q2, monkeypatch):
    def echouer():
        raise DonneesInvalides("Fichier invalide.")

    monkeypatch.setattr("railinsight.backend.retards_gares.charger_donnees", echouer)

    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert page_q2.warning[0].value == "Fichier invalide."