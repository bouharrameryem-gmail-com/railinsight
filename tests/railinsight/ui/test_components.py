"""Tests for reusable UI components via AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from railinsight.adapters.fake_data_provider import FakeDataProvider

_PAGES_DIR = Path(__file__).parents[3] / "src" / "railinsight" / "ui" / "pages"

# Shared provider for tests that don't need AppTest
_provider = FakeDataProvider(seed=42)


# ---------------------------------------------------------------------------
# kpi_card / kpi_row
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# insight_box
# ---------------------------------------------------------------------------


class TestInsightBox:
    def test_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.insight_box import insight_box
insight_box("Les liaisons longues concentrent les retards.")
""")
        at.run()
        assert not at.exception

    def test_custom_title(self):
        at = AppTest.from_string("""
from railinsight.ui.components.insight_box import insight_box
insight_box("Result.", title="Résultat principal")
""")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# chart_container
# ---------------------------------------------------------------------------


class TestChartContainer:
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


# ---------------------------------------------------------------------------
# data_table
# ---------------------------------------------------------------------------


class TestDataTable:
    def test_renders_basic(self):
        at = AppTest.from_string("""
import pandas as pd
from railinsight.ui.components.data_table import data_table
df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
data_table(df, title="Table test", key="test_dt")
""")
        at.run()
        assert not at.exception

    def test_download_button_present(self):
        at = AppTest.from_string("""
import pandas as pd
from railinsight.ui.components.data_table import data_table
df = pd.DataFrame({"x": range(5)})
data_table(df, filename="test.csv", key="test_dl")
""")
        at.run()
        assert not at.exception
        # st.download_button is exposed as at.download_button in AppTest
        assert len(at.download_button) > 0

    def test_max_rows_truncation(self):
        at = AppTest.from_string("""
import pandas as pd
from railinsight.ui.components.data_table import data_table
df = pd.DataFrame({"x": range(20)})
data_table(df, max_rows=3, key="test_trunc")
""")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------


class TestFilters:
    def test_period_filter_renders(self):
        at = AppTest.from_string("""
import pandas as pd
from railinsight.ui.components.filters import period_filter
periods = list(pd.period_range("2020-01", "2022-12", freq="M"))
start, end = period_filter(periods, key_prefix="test")
""")
        at.run()
        assert not at.exception

    def test_exclusion_filter_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.filters import exclusion_filter
result = exclusion_filter(key_prefix="test")
assert result in ("none", "known", "data")
""")
        at.run()
        assert not at.exception

    def test_min_months_filter_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.filters import min_months_filter
result = min_months_filter(key_prefix="test")
assert isinstance(result, int)
""")
        at.run()
        assert not at.exception

    def test_duration_adjust_toggle_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.filters import duration_adjust_toggle
result = duration_adjust_toggle(key_prefix="test")
assert isinstance(result, bool)
""")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# method_box
# ---------------------------------------------------------------------------


class TestMethodBox:
    def test_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.method_box import method_box
method_box("**Méthode :** ratio de sommes.")
""")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# warnings
# ---------------------------------------------------------------------------


class TestWarnings:
    def test_small_sample_above_threshold_shows_nothing(self):
        at = AppTest.from_string("""
from railinsight.ui.components.warnings import small_sample_warning
small_sample_warning(n=20)
""")
        at.run()
        assert not at.exception
        assert len(at.warning) == 0

    def test_small_sample_below_threshold_shows_warning(self):
        at = AppTest.from_string("""
from railinsight.ui.components.warnings import small_sample_warning
small_sample_warning(n=3)
""")
        at.run()
        assert not at.exception
        assert len(at.warning) > 0

    def test_missing_data_zero_shows_nothing(self):
        at = AppTest.from_string("""
from railinsight.ui.components.warnings import missing_data_warning
missing_data_warning(n_missing=0, total=100)
""")
        at.run()
        assert len(at.warning) == 0

    def test_missing_data_nonzero_shows_warning(self):
        at = AppTest.from_string("""
from railinsight.ui.components.warnings import missing_data_warning
missing_data_warning(n_missing=10, total=100, column="late30_rate")
""")
        at.run()
        assert len(at.warning) > 0


# ---------------------------------------------------------------------------
# route_card
# ---------------------------------------------------------------------------


class TestRouteCard:
    def test_renders(self):
        at = AppTest.from_string("""
from railinsight.ui.components.route_card import route_card
route_card(
    route="PARIS LYON → MARSEILLE",
    indicators={"Retards": "25 %"},
    cluster_name="Groupe A",
)
""")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# pca_panel
# ---------------------------------------------------------------------------


class TestPcaPanel:
    def test_renders_without_labels(self):
        at = AppTest.from_string(
            """
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from railinsight.ui.components.pca_panel import pca_panel

rng = np.random.default_rng(0)
X = rng.standard_normal((30, 4))
X_scaled = StandardScaler().fit_transform(X)
fitted = PCA(n_components=2).fit(X_scaled)
x_t = fitted.transform(X_scaled)
pca_panel(fitted, x_t, feature_names=["a", "b", "c", "d"])
""",
            default_timeout=15,
        )
        at.run()
        assert not at.exception

    def test_renders_with_labels(self):
        at = AppTest.from_string(
            """
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from railinsight.ui.components.pca_panel import pca_panel

rng = np.random.default_rng(1)
X_scaled = StandardScaler().fit_transform(rng.standard_normal((20, 3)))
fitted = PCA(n_components=2).fit(X_scaled)
x_t = fitted.transform(X_scaled)
labels = rng.integers(0, 2, size=20)
pca_panel(
    fitted, x_t,
    feature_names=["x1", "x2", "x3"],
    labels=labels,
    label_names={0: "Stable", 1: "Instable"},
)
""",
            default_timeout=15,
        )
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# components_demo page (integration test)
# ---------------------------------------------------------------------------


def test_components_demo_page_renders():
    at = AppTest.from_file(str(_PAGES_DIR / "components_demo.py"), default_timeout=30)
    at.run()
    assert not at.exception
