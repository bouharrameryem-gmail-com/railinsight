"""Tests de l'en-tête de section partagé par la page Q2 et l'accueil."""

from streamlit.testing.v1 import AppTest


def _afficher(numero):
    from railinsight.ui.components.section_header import section_header

    section_header(numero, "Une question <b>?", "Le constat", "#123456")


def test_section_numerotee():
    page = AppTest.from_function(_afficher, args=(3,)).run()

    entete = page.markdown[0].value
    assert "03</span>" in entete
    assert "color:#123456" in entete
    assert "Une question &lt;b&gt;?" in entete
    assert page.subheader[0].value == "Le constat"


def test_section_sans_numero():
    page = AppTest.from_function(_afficher, args=(None,)).run()

    assert "tabular-nums" not in page.markdown[0].value