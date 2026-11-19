"""Tests for reusable UI components via AppTest."""

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from railinsight.ui.components.chart_container import chart_container


class TestKpiCard:
    def test_single_card_renders(self):
        at = AppTest.from_string("""
import streamlit as st
from railinsight.ui.components.kpi_card import kpi_card
kpi_card("Retards", "27,3 %", delta="-1 pt", help="test")
""")
        at.run()
        assert not at.exception

    def test_kpi_row_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.kpi_card import kpi_row
kpi_row([{"label": "A", "value": "1"}, {"label": "B", "value": "2"}])
""")
        at.run()
        assert not at.exception

    def test_kpi_row_empty_list(self):
        at = AppTest.from_string("""
from railinsight.ui.components.kpi_card import kpi_row
kpi_row([])
""")
        at.run()
        assert not at.exception


class TestChartContainer:
    @pytest.mark.parametrize("etirer,largeur", [(True, "stretch"), (False, "content")])
    def test_largeur_et_cle_transmises(self, monkeypatch, etirer, largeur):
        appels = []
        monkeypatch.setattr(
            "railinsight.ui.components.chart_container.st.markdown",
            lambda texte: None,
        )
        monkeypatch.setattr(
            "railinsight.ui.components.chart_container.st.plotly_chart",
            lambda figure, **options: appels.append(options),
        )
        chart_container(
            go.Figure(), "Test", use_container_width=etirer, key="graphique_test"
        )
        assert appels == [{"width": largeur, "key": "graphique_test"}]

    def test_renders_without_optional_args(self):
        at = AppTest.from_string("""
import plotly.graph_objects as go
from railinsight.ui.components.chart_container import chart_container
chart_container(go.Figure(), "Titre du graphique")
""")
        at.run()
        assert not at.exception

    def test_renders_with_how_to_read(self):
        at = AppTest.from_string("""
import plotly.graph_objects as go
from railinsight.ui.components.chart_container import chart_container
chart_container(
    go.Figure(), "Titre", how_to_read="Lire de gauche à droite.", caption="Note."
)
""")
        at.run()
        assert not at.exception


class TestMethodBox:
    def test_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.method_box import method_box
method_box("**Méthode :** ratio de sommes.")
""")
        at.run()
        assert not at.exception
