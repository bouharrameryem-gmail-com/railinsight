"""Components demo page — internal showcase for team members.

This page demonstrates every reusable component in railinsight.ui.components.
Use it as a reference when building your own page.

Not listed in the main navigation by default; uncomment in app.py to activate.
"""

from __future__ import annotations

import numpy as np
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.data_table import data_table
from railinsight.ui.components.filters import (
    duration_adjust_toggle,
    exclusion_filter,
    min_months_filter,
    period_filter,
    route_filter,
)
from railinsight.ui.components.insight_box import insight_box
from railinsight.ui.components.kpi_card import kpi_row
from railinsight.ui.components.method_box import method_box
from railinsight.ui.components.pca_panel import pca_panel
from railinsight.ui.components.route_card import route_card
from railinsight.ui.components.warnings import (
    missing_data_warning,
    small_sample_warning,
)
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.tokens import CLUSTER_COLORS


def render() -> None:
    """Render the components demo page."""
    st.title("Vitrine des composants")
    st.markdown(
        "Cette page illustre tous les composants disponibles dans "
        "`railinsight.ui.components`. Chaque section montre le rendu "
        "et l'appel correspondant."
    )
    st.divider()

    provider = get_provider()
    state = PageState(page_key="components_demo")

    _section_kpi_cards()
    _section_insight_box()
    _section_chart_container(provider)
    _section_data_table(provider)
    _section_filters(provider, state)
    _section_method_box()
    _section_warnings()
    _section_route_card()
    _section_pca_panel(provider)


def _section_kpi_cards() -> None:
    st.markdown("## `kpi_card` et `kpi_row`")
    st.caption("Affiche 2–4 chiffres clés dans une rangée de colonnes.")

    kpi_row(
        [
            {"label": "Liaisons analysées", "value": "20"},
            {
                "label": "Retards > 15 min",
                "value": "27,3 %",
                "delta": "-1,2 pt",
                "help": "Moyenne pondérée sur les 12 derniers mois.",
            },
            {"label": "Annulations", "value": "4,1 %"},
            {"label": "Durée médiane", "value": "2 h 18"},
        ]
    )
    st.divider()


def _section_insight_box() -> None:
    st.markdown("## `insight_box`")
    st.caption("Encadré court pour un résultat clé.")

    insight_box(
        "Les 3 liaisons Paris–Méditerranée concentrent 40 % des retards sévères "
        "du réseau, malgré des volumes de trafic comparables aux autres axes."
    )
    st.divider()


def _section_chart_container(provider) -> None:
    st.markdown("## `chart_container`")
    st.caption("Encapsule un graphique Plotly avec titre, guide de lecture et légende.")

    import plotly.express as px  # noqa: PLC0415

    network = provider.load_network_monthly()
    network["month"] = network["date"].astype(str)
    fig = px.line(
        network,
        x="month",
        y="late15_rate",
        title="",
        labels={"late15_rate": "Taux de retard > 15 min", "month": "Mois"},
    )
    chart_container(
        fig,
        title="Le taux de retard fluctue fortement pendant les grèves et le Covid",
        how_to_read=(
            "Chaque point représente le taux mensuel de retard > 15 min "
            "sur l'ensemble du réseau (moyenne pondérée par le trafic). "
            "Les pics correspondent aux mois exceptionnels (grèves, Covid)."
        ),
        caption="Source : SNCF Open Data — données synthétiques pour la démo.",
    )
    st.divider()


def _section_data_table(provider) -> None:
    st.markdown("## `data_table`")
    st.caption("Tableau interactif avec bouton de téléchargement CSV.")

    features = provider.compute_route_features(
        provider.load_clean_monthly(),
        min_months=1,
    )
    display_cols = ["route", "late15_rate", "severe_share", "n_months"]
    data_table(
        features[display_cols].round(3),
        title="Indicateurs par liaison",
        filename="route_features.csv",
        max_rows=5,
        key="components_demo__data_table",
    )
    st.divider()


def _section_filters(provider, state: PageState) -> None:
    st.markdown("## `filters`")
    st.caption("Filtres standardisés — chaque valeur est retournée par la fonction.")

    monthly = provider.load_clean_monthly()
    periods = sorted(monthly["date"].unique())
    routes = sorted(monthly["route"].unique())

    with st.expander("Afficher les filtres", expanded=True):
        start, end = period_filter(periods, key_prefix=state.page_key)
        route = route_filter(routes, key_prefix=state.page_key)
        exclusion = exclusion_filter(key_prefix=state.page_key)
        min_months = min_months_filter(key_prefix=state.page_key)
        adjusted = duration_adjust_toggle(key_prefix=state.page_key)

    st.json(
        {
            "start": str(start),
            "end": str(end),
            "route": route,
            "exclusion": exclusion,
            "min_months": min_months,
            "adjust_duration": adjusted,
        }
    )
    st.divider()


def _section_method_box() -> None:
    st.markdown("## `method_box`")
    st.caption("Encadré méthodologique replié par défaut.")

    method_box(
        content="""
**Méthode :** indicateurs calculés par ratio de sommes sur les mois valides (WIKI §5.2).
Mois exceptionnels exclus selon la liste documentée (`known_events.csv`).

**Limites :** liaisons avec moins de 24 mois de données exclues.
La corrélation avec la durée du trajet n'est pas corrigée dans la lecture brute.
        """,
        expanded=True,
    )
    st.divider()


def _section_warnings() -> None:
    st.markdown("## `warnings`")
    st.caption("Bandeaux d'avertissement à afficher près des graphiques concernés.")

    small_sample_warning(n=3, entity="liaisons")
    missing_data_warning(n_missing=42, total=300, column="late30_rate")
    st.divider()


def _section_route_card() -> None:
    st.markdown("## `route_card`")
    st.caption("Fiche résumée d'une liaison.")

    route_card(
        route="PARIS GARE DE LYON → MARSEILLE ST CHARLES",
        indicators={
            "Retards > 15 min": "31,4 %",
            "Sévérité": "Élevée",
            "Durée": "3 h 20",
            "Mois observés": "72",
        },
        cluster_name="Liaisons longues — retards chroniques",
        color=CLUSTER_COLORS[0],
    )
    st.divider()


def _section_pca_panel(provider) -> None:
    st.markdown("## `pca_panel`")
    st.caption(
        "Toujours deux graphiques : nuage des individus + cercle des corrélations."
    )

    features = provider.compute_route_features(
        provider.load_clean_monthly(),
        min_months=1,
    )
    indicator_cols = [
        "late15_rate",
        "severe_share",
        "volatility_cv",
        "cancellation_rate",
    ]
    df_pca = features[indicator_cols].dropna()
    if len(df_pca) < 4:  # noqa: PLR2004
        st.warning("Pas assez de données pour la démonstration de l'ACP.")
        return

    x_scaled = StandardScaler().fit_transform(df_pca.values)  # noqa: N806 (matrix)
    fitted_pca = PCA(n_components=2, random_state=42).fit(x_scaled)
    x_transformed = fitted_pca.transform(x_scaled)

    rng = np.random.default_rng(0)
    fake_labels = rng.integers(0, 3, size=len(df_pca))

    pca_panel(
        pca=fitted_pca,
        x_pca=x_transformed,
        feature_names=indicator_cols,
        labels=fake_labels,
        label_names={0: "Stable", 1: "Modéré", 2: "Chronique"},
    )


# Script entry point.
render()
