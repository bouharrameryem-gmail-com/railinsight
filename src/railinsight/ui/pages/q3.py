"""Q3 — Profils de ponctualité (page unique, exploration complète).

Fusionne l'ancienne page narrative et le laboratoire : paramétrage complet
en haut, résultats organisés en onglets (Vue d'ensemble · Exploration ·
Carte · Robustesse · Comparateur A/B).

Script entry point — executed by Streamlit when this file is a st.Page target.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from railinsight.analysis.q3_clustering import (
    ALL_FEATURE_COLS,
    FEATURE_SETS,
    adjust_for_duration,
    auto_select_k,
    build_q3_features,
    compare_configurations,
    compute_ari_bootstrap,
    compute_ari_seeds,
    compute_eta2,
    compute_ward_linkage,
    detect_redundancy,
    fit_clustering,
    permutation_test,
    scale_features,
    silhouette_curve,
)
from railinsight.exceptions import InsufficientDataError, RailInsightError
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.data_table import data_table
from railinsight.ui.components.filters import (
    duration_adjust_toggle,
    exclusion_filter,
    min_months_filter,
)
from railinsight.ui.components.insight_box import insight_box
from railinsight.ui.components.kpi_card import kpi_row
from railinsight.ui.components.method_box import method_box
from railinsight.ui.components.pca_panel import pca_panel
from railinsight.ui.components.route_card import route_card
from railinsight.ui.components.route_map import route_map
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.css import inject_global_css
from railinsight.ui.theme.tokens import CLUSTER_COLORS
from railinsight.utils.formatting import fmt_number, fmt_pct

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# UI labels — no internal code names exposed to the user
# ---------------------------------------------------------------------------

_ALGO_LABELS: dict[str, str] = {
    "kmeans": "K-means",
    "ward": "Hiérarchique (Ward)",
    "gmm": "Mélange gaussien (GMM)",
}
_SCALER_LABELS: dict[str, str] = {
    "power": "Yeo-Johnson (recommandé)",
    "standard": "Z-score standard",
}
_FEATURE_SET_LABELS: dict[str, str] = {
    "v3": "Sévérité & volatilité (5 indicateurs)",
    "fixed": "Fréquence & chronicité (5 indicateurs)",
    "composite": "Arrivée & délai moyen (5 indicateurs)",
    "custom": "Sélection libre — colonne par colonne",
}

# Columns grouped by family for the custom-selection guide
_COLUMN_FAMILIES: dict[str, list[str]] = {
    "Annulations": ["cancellation_rate"],
    "Retards au départ": ["late15_rate", "late30_rate", "late60_rate"],
    "Sévérité des retards (calculés depuis retards départ)": [
        "severe_share",
        "extreme_share",
    ],
    "Retards à l'arrivée": [
        "late_arrival_rate",
        "mean_delay_when_late",
        "severe_ratio",
    ],
    "Variabilité mensuelle": [
        "volatility",
        "volatility_cv",
        "chronicity",
        "irregularity",
    ],
}

_FR_MONTHS: list[str] = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]

_COLUMN_HELP: dict[str, str] = {
    "cancellation_rate": "Fraction de trains supprimés / total prévu.",
    "late15_rate": "Fraction de trains arrivés avec > 15 min de retard.",
    "late30_rate": "Fraction de trains arrivés avec > 30 min de retard.",
    "late60_rate": "Fraction de trains arrivés avec > 60 min de retard.",
    "severe_share": (
        "Parmi retards >15 min, fraction >30 min. "
        "Dérivé de late15 et late30 — évitez de les combiner."
    ),
    "extreme_share": (
        "Parmi retards >15 min, fraction >60 min. "
        "Dérivé de late15 et late60 — évitez de les combiner."
    ),
    "late_arrival_rate": "Fraction de trains en retard à l'arrivée.",
    "mean_delay_when_late": "Délai moyen (min) pour les trains en retard à l'arrivée.",
    "severe_ratio": (
        "Parmi retards à l'arrivée, fraction avec >30 min au départ. "
        "Dérivé de late30 et late_arrival — évitez de les combiner."
    ),
    "volatility": "Écart-type mensuel du taux de retard >15 min.",
    "volatility_cv": (
        "Coefficient de variation mensuel (volatility / mean). "
        "Normalise par le niveau moyen — à préférer à volatility seule."
    ),
    "chronicity": (
        "Fraction des mois où la liaison dépasse la moyenne réseau. "
        "Mesure une dégradation persistante, pas ponctuelle."
    ),
    "irregularity": "Écart-type mensuel du taux de retard à l'arrivée.",
}


# ---------------------------------------------------------------------------
# Cached analysis
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Calcul des profils de ponctualité…")
def _run_analysis(
    monthly: pd.DataFrame,
    network: pd.DataFrame,
    feature_set: str,
    custom_cols: list[str],
    exclusion: Literal["none", "known", "data"],
    min_months: int,
    adjust_duration: bool,
    scaler_type: Literal["power", "standard"],
    algorithm: Literal["kmeans", "ward", "gmm"],
    k_mode: str,
    k_manual: int,
    n_init: int,
    covariance_type: Literal["full", "tied", "diag", "spherical"],
) -> dict:
    """Run the full Q3 analysis with the given parameters.

    Cached by all arguments — reruns only when data or a parameter changes.
    """
    features = build_q3_features(
        monthly, network, exclusion=exclusion, min_months=min_months
    )
    base_cols: list[str] = (
        custom_cols if feature_set == "custom" else FEATURE_SETS[feature_set]
    )

    if adjust_duration:
        features, _ = adjust_for_duration(features, base_cols)
        input_cols = [
            f"{c}_adj" if f"{c}_adj" in features.columns else c for c in base_cols
        ]
    else:
        input_cols = base_cols

    available_cols = [c for c in input_cols if c in features.columns]
    x_df = features[available_cols].dropna()
    if len(x_df) < 4:  # noqa: PLR2004
        raise InsufficientDataError("Pas assez de liaisons après filtrage.")

    x_scaled, scaler = scale_features(x_df, scaler_type)

    k = auto_select_k(x_scaled, algorithm) if k_mode == "auto" else k_manual
    labels = fit_clustering(
        x_scaled, algorithm, k, n_init=n_init, covariance_type=covariance_type
    )
    sil = float(silhouette_score(x_scaled, labels))

    pca_model = PCA(n_components=2, random_state=42).fit(x_scaled)
    x_pca = pca_model.transform(x_scaled)

    centroids_scaled = np.array([x_scaled[labels == c].mean(axis=0) for c in range(k)])
    try:
        centroids_original = scaler.inverse_transform(centroids_scaled)
    except Exception:
        centroids_original = centroids_scaled

    # Assign descriptive names when k == 2
    late15_col = (
        "late15_rate_adj" if "late15_rate_adj" in features.columns else "late15_rate"
    )
    if late15_col in features.columns:
        cluster_means = features.assign(_lbl=labels).groupby("_lbl")[late15_col].mean()
        high_delay = int(cluster_means.idxmax())
    else:
        high_delay = 0

    cluster_names: dict[int, str] = {}
    for c in range(k):
        if k == 2:  # noqa: PLR2004
            cluster_names[c] = "Peu fiables" if c == high_delay else "Réguliers"
        else:
            cluster_names[c] = f"Profil {c + 1}"

    redundant = detect_redundancy(features, base_cols)

    return {
        "features": features,
        "routes": x_df.index.tolist(),
        "X_scaled": x_scaled,
        "X_pca": x_pca,
        "labels": labels,
        "k": k,
        "silhouette": sil,
        "pca": pca_model,
        "centroids_original": centroids_original,
        "input_cols": input_cols,
        "base_cols": base_cols,
        "scaler": scaler,
        "algorithm": algorithm,
        "redundant": redundant,
        "cluster_names": cluster_names,
        "params": {
            "feature_set": feature_set,
            "exclusion": exclusion,
            "min_months": min_months,
            "adjust_duration": adjust_duration,
            "scaler": scaler_type,
            "algorithm": algorithm,
            "k": k,
        },
    }


def _results_key(slot: str = "current") -> str:
    return f"q3__results_{slot}"


# ---------------------------------------------------------------------------
# Page class
# ---------------------------------------------------------------------------


class Q3Page(BasePage):
    """Interactive Q3 clustering page — parameters, results, and robustness.

    Merges the narrative (key findings, cluster cards, map) and the laboratory
    (silhouette curves, distributions, dendrogram, A/B comparator).

    Args:
        provider: Data provider satisfying the DataProvider protocol.
    """

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._state = PageState(page_key="q3")

    @property
    def question_number(self) -> int:
        return 3

    @property
    def question_title(self) -> str:
        return "Profils de ponctualité des TGV"

    @property
    def author(self) -> str:
        return "Bachelard"

    # --- Template sections ---------------------------------------------------

    def _render_key_figures(self) -> None:
        inject_global_css()
        results = st.session_state.get(_results_key())
        if results is None:
            kpi_row(
                [
                    {"label": "Liaisons analysées", "value": "—"},
                    {"label": "k (profils)", "value": "—"},
                    {"label": "Silhouette", "value": "—"},
                    {"label": "Plus petit profil", "value": "—"},
                ]
            )
            return

        labels = results["labels"]
        k = results["k"]
        sil = results["silhouette"]
        unique, counts = np.unique(labels, return_counts=True)
        cluster_names = results["cluster_names"]

        base_cards = [
            {"label": "Liaisons analysées", "value": fmt_number(len(labels))},
            {"label": "k (profils)", "value": str(k)},
            {
                "label": "Silhouette",
                "value": f"{sil:.3f}",
                "help": ("Entre −1 et 1 ; > 0,2 indique une structure non triviale."),
            },
            {"label": "Plus petit profil", "value": str(int(counts.min()))},
        ]
        kpi_row(base_cards)

        # One KPI per cluster
        cluster_cards = []
        for c, n in zip(unique, counts, strict=False):
            cluster_cards.append(
                {
                    "label": cluster_names.get(int(c), f"Profil {c + 1}"),
                    "value": f"{n} liaisons",
                }
            )
        if cluster_cards:
            kpi_row(cluster_cards)

    def _render_controls(self) -> None:
        self._sync_params_from_url()
        monthly = self._provider.load_clean_monthly()
        network = self._provider.load_network_monthly()

        # Build sorted list of "YYYY-MM" strings from the actual dataset
        _date_col = monthly["date"]
        if isinstance(_date_col.dtype, pd.PeriodDtype):
            _period_strs = _date_col.dropna().astype(str)
        else:
            _period_strs = _date_col.dt.to_period("M").dropna().astype(str)
        months_available = sorted(_period_strs.unique().tolist())

        def _fmt_month(ym: str) -> str:
            """Format 'YYYY-MM' → 'Mois YYYY' in French."""
            try:
                y, m = ym.split("-")
                return f"{_FR_MONTHS[int(m) - 1]} {y}"
            except Exception:
                return ym

        with st.form(key="q3_params"):
            st.markdown("##### Données")
            col1, col2 = st.columns(2)
            with col1:
                exclusion = exclusion_filter(key_prefix=self._state.page_key)
                min_months = min_months_filter(key_prefix=self._state.page_key)
            with col2:
                adjust = duration_adjust_toggle(key_prefix=self._state.page_key)

            if len(months_available) >= 2:
                st.markdown("**Période analysée**")
                col_start, col_end = st.columns(2)
                with col_start:
                    period_start = st.selectbox(
                        "Début",
                        options=months_available,
                        index=0,
                        format_func=_fmt_month,
                        key=self._state.widget_key("period_start"),
                    )
                with col_end:
                    period_end = st.selectbox(
                        "Fin",
                        options=months_available,
                        index=len(months_available) - 1,
                        format_func=_fmt_month,
                        key=self._state.widget_key("period_end"),
                    )
            else:
                period_start = months_available[0] if months_available else "2018-01"
                period_end = months_available[-1] if months_available else "2025-12"

            st.markdown("##### Indicateurs à inclure dans le clustering")
            fs_choice = st.radio(
                "Jeu d'indicateurs",
                options=list(_FEATURE_SET_LABELS.keys()),
                format_func=lambda k_: _FEATURE_SET_LABELS[k_],
                index=0,
                key=self._state.widget_key("feature_set"),
                horizontal=False,
            )
            custom_cols: list[str] = []
            if fs_choice == "custom":
                custom_cols = st.multiselect(
                    "Colonnes à inclure",
                    options=ALL_FEATURE_COLS,
                    default=FEATURE_SETS["v3"],
                    key=self._state.widget_key("custom_cols"),
                )
                with st.expander("Guide des indicateurs et familles", expanded=False):
                    for family, cols in _COLUMN_FAMILIES.items():
                        st.markdown(f"**{family}**")
                        for col in cols:
                            if col in ALL_FEATURE_COLS:
                                help_text = _COLUMN_HELP.get(col, "")
                                st.markdown(f"- `{col}` — {help_text}")
            else:
                # Show which columns are included in the selected preset
                preset_cols = FEATURE_SETS.get(fs_choice, [])
                if preset_cols:
                    st.caption("Colonnes : " + ", ".join(f"`{c}`" for c in preset_cols))

            st.markdown("##### Prétraitement")
            scaler_choice = st.radio(
                "Mise à l'échelle",
                options=list(_SCALER_LABELS.keys()),
                format_func=lambda k_: _SCALER_LABELS[k_],
                index=0,
                key=self._state.widget_key("scaler"),
                horizontal=True,
            )

            st.markdown("##### Algorithme et hyperparamètres")
            algo = st.radio(
                "Algorithme",
                options=list(_ALGO_LABELS.keys()),
                format_func=lambda k_: _ALGO_LABELS[k_],
                index=0,
                key=self._state.widget_key("algorithm"),
                horizontal=True,
            )
            k_mode = st.radio(
                "Nombre de profils k",
                options=["auto", "manuel"],
                format_func=lambda x: "Auto (silhouette)" if x == "auto" else "Manuel",
                index=0,
                key=self._state.widget_key("k_mode"),
                horizontal=True,
            )
            k_manual = st.slider(
                "k manuel",
                min_value=2,
                max_value=10,
                value=2,
                key=self._state.widget_key("k_manual"),
                disabled=(k_mode == "auto"),
            )

            n_init = 50
            cov_type: Literal["full", "tied", "diag", "spherical"] = "full"
            if algo == "kmeans":
                n_init = st.slider(
                    "n_init (initialisations K-means)",
                    min_value=10,
                    max_value=100,
                    value=50,
                    step=10,
                    key=self._state.widget_key("n_init"),
                    help=(
                        "K-means relance depuis n_init points de départ et garde "
                        "le meilleur résultat. Plus élevé = plus stable, plus lent."
                    ),
                )
            elif algo == "gmm":
                cov_choice = st.selectbox(
                    "Type de covariance (GMM)",
                    options=["full", "tied", "diag", "spherical"],
                    index=0,
                    key=self._state.widget_key("cov_type"),
                    help=(
                        "**full** : chaque composante a sa propre matrice. "
                        "**tied** : toutes partagent la même. "
                        "**diag** : matrices diagonales (pas de corrélation). "
                        "**spherical** : variance isotrope."
                    ),
                )
                cov_type = cov_choice  # type: ignore[assignment]

            submitted = st.form_submit_button(
                "Lancer l'analyse", type="primary", use_container_width=True
            )

        if submitted:
            with st.spinner("Calcul en cours…"):
                try:
                    # Swap silently if user put end before start
                    ps = min(period_start, period_end)
                    pe = max(period_start, period_end)
                    _dc = monthly["date"]
                    if isinstance(_dc.dtype, pd.PeriodDtype):
                        month_series = _dc.astype(str)
                    else:
                        month_series = _dc.dt.to_period("M").astype(str)
                    monthly_filtered = monthly[month_series.between(ps, pe)]
                    results = _run_analysis(
                        monthly=monthly_filtered,
                        network=network,
                        feature_set=fs_choice,
                        custom_cols=custom_cols,
                        exclusion=exclusion,
                        min_months=min_months,
                        adjust_duration=adjust,
                        scaler_type=scaler_choice,  # type: ignore[arg-type]
                        algorithm=algo,  # type: ignore[arg-type]
                        k_mode=k_mode,
                        k_manual=k_manual,
                        n_init=n_init,
                        covariance_type=cov_type,
                    )
                    st.session_state[_results_key()] = results
                    self._sync_params_to_url(results["params"])
                    logger.info(
                        "Q3 analysis: algo=%s k=%d sil=%.3f",
                        algo,
                        results["k"],
                        results["silhouette"],
                    )
                    # Rerun so _render_key_figures (called before _render_controls
                    # in BasePage.render) sees the freshly stored results.
                    st.rerun()
                except RailInsightError as exc:
                    st.warning(f"⚠️ {exc}")
                except Exception:
                    logger.exception("Q3 analysis failed")
                    st.error("L'analyse a échoué. Vérifiez les paramètres.")

    def _render_body(self) -> None:
        results = st.session_state.get(_results_key())
        if results is None:
            st.info(
                "Configurez les paramètres ci-dessus et cliquez **Lancer l'analyse**."
            )
            return

        for col_a, col_b, rho in results["redundant"]:
            st.warning(
                f"⚠️ **Redondance** : `{col_a}` et `{col_b}` "
                f"très corrélés (ρ = {rho:+.2f}). "
                "Inclure les deux surpondère cette dimension."
            )

        tab_res, tab_exp, tab_map, tab_rob, tab_ab = st.tabs(
            [
                "Vue d'ensemble",
                "Exploration",
                "Carte",
                "Robustesse",
                "Comparateur A/B",
            ]
        )

        with tab_res:
            self._render_overview_tab(results)

        with tab_exp:
            self._render_exploration_tab(results)

        with tab_map:
            self._render_map_tab(results)

        with tab_rob:
            self._render_robustesse_tab(results)

        with tab_ab:
            self._render_ab_tab()

    def _render_method_box(self) -> None:
        results = st.session_state.get(_results_key())
        params = results["params"] if results else {}
        content = """
**Approche :** clustering non supervisé sur des indicateurs agrégés par liaison.
Les mois exceptionnels documentés (grèves, Covid) sont exclus pour ne pas
biaiser les profils. Les indicateurs corrélés à la durée du trajet sont
optionnellement ajustés par régression OLS en espace log.

**Indicateurs disponibles** (groupés par famille) :
- *Annulations* : taux d'annulation mensuel moyen.
- *Retards au départ* : taux de retard >15/30/60 min.
- *Sévérité* : fraction des retards >30 min parmi >15 min (etc.).
- *Arrivée* : taux retard à l'arrivée, délai moyen, ratio sévère.
- *Variabilité mensuelle* : volatilité, CV, chronicité, irrégularité.

**Validation :** silhouette (cohésion), Davies-Bouldin (séparation),
η² (pouvoir discriminant par indicateur), ARI seeds/bootstrap (stabilité),
test de permutation (significativité).

**Limites :**
- K-means impose une frontière artificielle : les groupes peuvent se chevaucher.
- L'ajustement de durée repose sur une régression linéaire simple.
- Les liaisons avec moins du seuil minimum de mois valides sont exclues.
"""
        if params:
            fs_label = _FEATURE_SET_LABELS.get(
                params.get("feature_set", ""), params.get("feature_set", "")
            )
            algo_label = _ALGO_LABELS.get(params.get("algorithm", ""), "")
            content += (
                f"\n**Configuration actuelle :**\n"
                f"Jeu : `{fs_label}` · "
                f"Algorithme : `{algo_label}` · "
                f"k : `{params.get('k', '—')}` · "
                f"Ajustement durée : "
                f"`{'oui' if params.get('adjust_duration') else 'non'}`."
            )
        method_box(content=content)

    # -------------------------------------------------------------------------
    # Tab: Vue d'ensemble
    # -------------------------------------------------------------------------

    def _render_overview_tab(self, results: dict) -> None:
        k = results["k"]
        cluster_names = results["cluster_names"]
        labels = results["labels"]

        insight_box(
            f"Le réseau TGV se divise en **{k} profil{'s' if k > 1 else ''} "
            f"distinct{'s' if k > 1 else ''}** de ponctualité. "
            "Cette structure est statistiquement non aléatoire, "
            "mais la frontière entre les profils n'est pas toujours nette : "
            "certaines liaisons pourraient appartenir à l'un ou l'autre profil."
        )

        if k <= 4:  # noqa: PLR2004
            cols = st.columns(min(k, 2))
            for c in range(k):
                with cols[c % 2]:
                    self._render_cluster_card(c, results)

        st.divider()

        label_names = {
            int(c): cluster_names.get(int(c), f"Profil {c + 1}") for c in range(k)
        }
        pca_panel(
            pca=results["pca"],
            x_pca=results["X_pca"],
            feature_names=[c.replace("_adj", "") for c in results["input_cols"]],
            labels=labels,
            label_names=label_names,
            title="Structure des profils en deux dimensions (PCA)",
        )

        st.divider()
        self._render_centroid_heatmap(results)

        st.divider()
        self._render_route_finder(results)

    def _render_cluster_card(self, cluster_idx: int, results: dict) -> None:
        labels = results["labels"]
        routes = results["routes"]
        features = results["features"]
        cluster_names = results["cluster_names"]
        display_cols = results["base_cols"]

        mask = labels == cluster_idx
        name = cluster_names.get(cluster_idx, f"Profil {cluster_idx + 1}")
        color = CLUSTER_COLORS[cluster_idx % len(CLUSTER_COLORS)]
        n = int(mask.sum())

        route_subset = [r for r, m in zip(routes, mask, strict=False) if m]
        available = [c for c in display_cols if c in features.columns]
        feat_subset = features.loc[route_subset, available].mean() if available else {}

        late15 = feat_subset.get("late15_rate", float("nan"))
        severe = feat_subset.get("severe_share", float("nan"))

        def _fmt(v: float) -> str:
            return fmt_pct(v) if isinstance(v, float) and not np.isnan(v) else "—"

        late15_str = _fmt(late15)
        severe_str = _fmt(severe)

        st.markdown(
            f'<div style="border-left:4px solid {color};padding:12px 16px;'
            f'background:#F5F7FA;border-radius:4px;margin-bottom:8px;">'
            f'<strong style="color:{color};">{name}</strong><br>'
            f'<span style="font-size:0.85em;">'
            f"{n} liaisons · Retards >15 min : {late15_str}"
            f" · Part sévère : {severe_str}"
            f"</span></div>",
            unsafe_allow_html=True,
        )

    def _render_centroid_heatmap(self, results: dict) -> None:
        k = results["k"]
        cluster_names = results["cluster_names"]
        base_cols = results["base_cols"]
        centroids = results["centroids_original"]

        col_labels = [
            c.replace("_", " ").replace(" rate", " (taux)") for c in base_cols
        ]
        row_labels = [cluster_names.get(c, f"Profil {c + 1}") for c in range(k)]

        fig = go.Figure(
            go.Heatmap(
                z=centroids,
                x=col_labels,
                y=row_labels,
                colorscale="RdYlGn_r",
                showscale=True,
                texttemplate="%{z:.3f}",
            )
        )
        fig.update_layout(
            margin={"l": 140, "r": 20, "t": 30, "b": 60},
        )
        chart_container(
            fig,
            title="Centroïdes des profils — valeurs moyennes par indicateur",
            how_to_read=(
                "Chaque ligne est un profil, chaque colonne un indicateur. "
                "Rouge = valeur élevée (moins bon), vert = valeur faible. "
                "Comparez les lignes pour voir ce qui distingue les profils."
            ),
        )

    def _render_route_finder(self, results: dict) -> None:
        st.markdown("#### Trouver le profil d'une liaison")
        routes = results["routes"]
        labels = results["labels"]
        features = results["features"]
        cluster_names = results["cluster_names"]
        base_cols = results["base_cols"]

        selected = st.selectbox(
            "Choisissez une liaison",
            options=routes,
            key=self._state.widget_key("selected_route"),
        )
        if selected not in features.index:
            st.warning("Données insuffisantes pour cette liaison.")
            return

        route_idx = routes.index(selected)
        cluster = int(labels[route_idx])
        name = cluster_names.get(cluster, f"Profil {cluster + 1}")
        color = CLUSTER_COLORS[cluster % len(CLUSTER_COLORS)]

        feat_row = features.loc[selected]
        indicators = {}
        rate_cols = {
            "cancellation_rate",
            "late15_rate",
            "late30_rate",
            "late60_rate",
            "severe_share",
            "extreme_share",
            "late_arrival_rate",
            "severe_ratio",
        }
        for col in base_cols:
            val = feat_row.get(col, float("nan"))
            if isinstance(val, float) and not np.isnan(val):
                col_base = col.replace("_adj", "")
                if col_base in rate_cols:
                    indicators[col.replace("_", " ")] = fmt_pct(val)
                else:
                    indicators[col.replace("_", " ")] = f"{val:.3f}"

        if "trip_duration_min" in feat_row.index:
            dur = int(feat_row["trip_duration_min"])
            indicators["Durée médiane"] = f"{dur // 60} h {dur % 60:02d}"
        if "n_months" in feat_row.index:
            indicators["Mois observés"] = str(int(feat_row["n_months"]))

        route_card(
            route=selected, indicators=indicators, cluster_name=name, color=color
        )

    # -------------------------------------------------------------------------
    # Tab: Exploration
    # -------------------------------------------------------------------------

    def _render_exploration_tab(self, results: dict) -> None:
        self._render_silhouette_section(results)
        st.divider()
        self._render_distributions_section(results)
        st.divider()
        self._render_cluster_routes(results)
        st.divider()
        self._render_correlation_section(results)
        if results["algorithm"] == "ward":
            st.divider()
            self._render_dendrogram_section(results)

    def _render_distributions_section(self, results: dict) -> None:
        st.markdown("#### Distributions par profil")
        features = results["features"]
        labels = results["labels"]
        routes = results["routes"]
        input_cols = results["input_cols"]
        k = results["k"]
        cluster_names = results["cluster_names"]

        valid_cols = [c for c in input_cols if c in features.columns]
        plot_df = features.loc[routes, valid_cols].copy()
        plot_df["_cluster"] = [
            cluster_names.get(int(lbl), f"Profil {int(lbl) + 1}") for lbl in labels
        ]

        chart_type = st.radio(
            "Type de graphique",
            options=["violin", "box"],
            format_func=lambda x: "Violin" if x == "violin" else "Boîte à moustaches",
            horizontal=True,
            key=self._state.widget_key("dist_chart_type"),
        )
        selected_col = st.selectbox(
            "Indicateur à afficher",
            options=valid_cols,
            format_func=lambda c: c.replace("_adj", "").replace("_", " "),
            key=self._state.widget_key("dist_col"),
        )
        col_label = selected_col.replace("_adj", "").replace("_", " ")

        color_map = {
            cluster_names.get(c, f"Profil {c + 1}"): CLUSTER_COLORS[
                c % len(CLUSTER_COLORS)
            ]  # noqa: E501
            for c in range(k)
        }

        if chart_type == "violin":
            fig = px.violin(
                plot_df,
                y=selected_col,
                x="_cluster",
                color="_cluster",
                box=True,
                points="outliers",
                labels={selected_col: col_label, "_cluster": "Profil"},
                color_discrete_map=color_map,
            )
        else:
            fig = px.box(
                plot_df,
                y=selected_col,
                x="_cluster",
                color="_cluster",
                points="outliers",
                labels={selected_col: col_label, "_cluster": "Profil"},
                color_discrete_map=color_map,
            )
        fig.update_layout(showlegend=False)
        chart_container(
            fig,
            title=f"Distribution de « {col_label} » par profil",
            how_to_read=(
                "Chaque boîte montre la médiane, les quartiles et les valeurs extrêmes "
                "pour un profil. Les points isolés sont des liaisons atypiques."
            ),
        )

    def _render_cluster_routes(self, results: dict) -> None:
        st.markdown("#### Liaisons par profil")
        features = results["features"]
        labels = results["labels"]
        routes = results["routes"]
        k = results["k"]
        base_cols = results["base_cols"]
        cluster_names = results["cluster_names"]

        available = [c for c in base_cols if c in features.columns]
        for c in range(k):
            mask = [int(lbl) == c for lbl in labels]
            cluster_routes = [r for r, m in zip(routes, mask, strict=False) if m]
            cluster_label = cluster_names.get(c, f"Profil {c + 1}")
            with st.expander(
                f"{cluster_label} — {len(cluster_routes)} liaisons",
                expanded=(c == 0),
            ):
                if available:
                    df_show = features.loc[cluster_routes, available].copy()
                    df_show.index.name = "Liaison"
                    df_show.columns = [col.replace("_", " ") for col in df_show.columns]
                    df_show = df_show.round(4)
                    st.dataframe(df_show, use_container_width=True)
                else:
                    st.write(cluster_routes)

    def _render_correlation_section(self, results: dict) -> None:
        st.markdown("#### Corrélations entre indicateurs")
        features = results["features"]
        input_cols = results["input_cols"]
        available = [c for c in input_cols if c in features.columns]

        if len(available) < 2:  # noqa: PLR2004
            st.info("Pas assez d'indicateurs pour une heatmap.")
            return

        corr = features[available].corr(method="pearson")
        labels_clean = [c.replace("_adj", "").replace("_", " ") for c in available]

        fig = px.imshow(
            corr.values,
            x=labels_clean,
            y=labels_clean,
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            text_auto=".2f",
            aspect="auto",
        )
        fig.update_layout(
            xaxis={"tickangle": -30},
            coloraxis_colorbar={"title": "ρ"},
        )
        chart_container(
            fig,
            title="Heatmap de corrélation (Pearson)",
            how_to_read=(
                "Rouge foncé = corrélation positive forte, bleu = négative. "
                "|ρ| > 0,8 signale une redondance entre indicateurs."
            ),
        )

    def _render_dendrogram_section(self, results: dict) -> None:
        st.markdown("#### Dendrogramme Ward")
        x_scaled = results["X_scaled"]
        routes = results["routes"]

        with st.spinner("Calcul du dendrogramme…"):
            try:
                linkage_matrix = compute_ward_linkage(x_scaled)
            except Exception:
                logger.exception("Ward linkage failed")
                st.warning("Impossible de calculer le dendrogramme.")
                return

        max_labels = 40
        if len(routes) > max_labels:
            st.caption(
                f"{len(routes)} liaisons — seules les {max_labels} premières "
                "sont affichées pour la lisibilité."
            )
            display_data = x_scaled[:max_labels]
            display_labels = [str(r) for r in routes[:max_labels]]
        else:
            display_data = x_scaled
            display_labels = [str(r) for r in routes]

        fig = ff.create_dendrogram(
            display_data,
            labels=display_labels,
            linkagefun=lambda x: compute_ward_linkage(x),
            color_threshold=0.7 * float(linkage_matrix[:, 2].max()),
        )
        fig.update_layout(
            height=500,
            xaxis={"tickangle": -60, "tickfont": {"size": 8}},
            yaxis={"title": "Distance Ward"},
        )
        chart_container(
            fig,
            title="Dendrogramme (liaison Ward)",
            how_to_read=(
                "Chaque feuille est une liaison. "
                "Plus deux liaisons fusionnent bas, plus elles se ressemblent. "
                "Le nombre naturel de groupes correspond aux branches "
                "qui se rejoignent le plus haut."
            ),
        )

    # -------------------------------------------------------------------------
    # Tab: Carte
    # -------------------------------------------------------------------------

    def _render_map_tab(self, results: dict) -> None:
        routes = results["routes"]
        labels = results["labels"]
        k = results["k"]
        cluster_names = results["cluster_names"]

        label_names = {c: cluster_names.get(c, f"Profil {c + 1}") for c in range(k)}
        route_map(
            routes=routes,
            labels=list(labels),
            k=k,
            label_names=label_names,
            title="Répartition géographique des profils de ponctualité",
        )

    # -------------------------------------------------------------------------
    # Tab: Robustesse
    # -------------------------------------------------------------------------

    def _render_robustesse_tab(self, results: dict) -> None:
        self._render_eta2_section(results)
        st.divider()
        self._render_robustness_section(results)

    def _render_silhouette_section(self, results: dict) -> None:
        st.markdown("#### Courbes de sélection de k")
        with st.spinner("Calcul des scores pour k = 2 à 8…"):
            curve = silhouette_curve(
                results["X_scaled"],
                results["algorithm"],
                k_range=range(2, 9),
            )

        tab_inertia, tab_sil, tab_db, tab_size = st.tabs(
            ["Inertie (coude)", "Silhouette", "Davies-Bouldin", "Taille min. du groupe"]
        )
        with tab_inertia:
            fig = px.line(
                curve,
                x="k",
                y="inertia",
                markers=True,
                labels={"inertia": "Inertie (WCSS)", "k": "Nombre de profils k"},
            )
            fig.add_vline(
                x=results["k"],
                line_dash="dash",
                line_color=CLUSTER_COLORS[0],
                annotation_text=f"k choisi = {results['k']}",
            )
            chart_container(
                fig,
                title="Inertie selon k — méthode du coude",
                how_to_read=(
                    "L'inertie mesure la compacité des groupes "
                    "(somme des distances au centre). "
                    "Elle décroît toujours avec k ; cherchez le 'coude' : "
                    "le point où le gain devient marginal. "
                    "Le k optimal est souvent juste après ce coude."
                ),
            )
        with tab_sil:
            fig = px.line(
                curve,
                x="k",
                y="silhouette",
                markers=True,
                labels={"silhouette": "Score silhouette", "k": "k"},
            )
            fig.add_vline(
                x=results["k"],
                line_dash="dash",
                line_color=CLUSTER_COLORS[0],
                annotation_text=f"k choisi = {results['k']}",
            )
            chart_container(
                fig,
                title="Silhouette selon k",
                how_to_read=(
                    "Le silhouette mesure si chaque liaison est bien dans son groupe. "
                    "Plus c'est haut, mieux c'est."
                ),
            )
        with tab_db:
            fig = px.line(
                curve,
                x="k",
                y="davies_bouldin",
                markers=True,
                labels={"davies_bouldin": "Indice Davies-Bouldin", "k": "k"},
            )
            chart_container(
                fig,
                title="Davies-Bouldin selon k",
                how_to_read="Plus la valeur est basse, mieux les groupes sont séparés.",
            )
        with tab_size:
            fig = px.bar(
                curve,
                x="k",
                y="min_cluster_size",
                labels={
                    "min_cluster_size": "Liaisons dans le plus petit groupe",
                    "k": "k",
                },
            )
            fig.add_hline(y=3, line_dash="dot", annotation_text="seuil min = 3")
            chart_container(
                fig,
                title="Taille du plus petit groupe selon k",
                how_to_read=(
                    "Un groupe trop petit (< 3) est suspect : "
                    "il peut refléter des outliers, pas un profil structuré."
                ),
            )

    def _render_eta2_section(self, results: dict) -> None:
        st.markdown("#### Pouvoir discriminant des indicateurs (η²)")
        features = results["features"]
        labels = results["labels"]
        eval_cols = [c for c in ALL_FEATURE_COLS if c in features.columns]
        eta2 = compute_eta2(features, labels, eval_cols)
        eta2_df = (
            eta2.dropna()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"index": "indicateur", "eta2": "η²"})
        )
        eta2_df["η²"] = eta2_df["η²"].round(3)
        data_table(
            eta2_df,
            title="η² par indicateur",
            filename="eta2_q3.csv",
            key="q3__eta2_table",
        )
        with st.expander("Comment lire η² ?", expanded=False):
            st.markdown(
                "η² mesure quelle fraction de la variance totale d'un indicateur "
                "est expliquée par l'appartenance au groupe. "
                "0 = l'indicateur ne distingue pas les groupes ; "
                "1 = l'indicateur suffit à les séparer parfaitement. "
                "η² > 0,3 est élevé dans ce contexte."
            )

    def _render_robustness_section(self, results: dict) -> None:
        st.markdown("#### Stabilité de la solution")

        col_seeds, col_bootstrap, col_perm = st.columns(3)

        with col_seeds:
            if st.button(
                "Tester (seeds)",
                key=self._state.widget_key("btn_seeds"),
                help="Lance 20 seeds et calcule l'ARI moyen.",
            ):
                with st.spinner("…"):
                    ari_s = compute_ari_seeds(
                        results["X_scaled"], results["algorithm"], results["k"]
                    )
                    st.session_state[self._state.widget_key("ari_seeds")] = ari_s

            ari_s = st.session_state.get(self._state.widget_key("ari_seeds"))
            if ari_s is not None:
                st.metric(
                    "ARI moyen (seeds)",
                    f"{ari_s.mean():.3f}",
                    help="ARI > 0,8 : solution stable.",
                )

        with col_bootstrap:
            if st.button(
                "Tester (bootstrap)",
                key=self._state.widget_key("btn_bootstrap"),
                help="Rééchantillonne 80 % des liaisons 30 fois.",
            ):
                with st.spinner("…"):
                    ari_b = compute_ari_bootstrap(
                        results["X_scaled"], results["algorithm"], results["k"]
                    )
                    st.session_state[self._state.widget_key("ari_bootstrap")] = ari_b

            ari_b = st.session_state.get(self._state.widget_key("ari_bootstrap"))
            if ari_b is not None:
                st.metric(
                    "ARI médian (bootstrap)",
                    f"{ari_b.median():.3f}",
                    delta=f"min {ari_b.min():.3f}",
                )

        with col_perm:
            if st.button(
                "Test de permutation",
                key=self._state.widget_key("btn_perm"),
                help="Génère 30 jeux permutés et compare le silhouette observé.",
            ):
                with st.spinner("…"):
                    perm = permutation_test(
                        results["X_scaled"], results["algorithm"], results["k"]
                    )
                    st.session_state[self._state.widget_key("perm")] = perm

            perm = st.session_state.get(self._state.widget_key("perm"))
            if perm is not None:
                st.metric(
                    "p-valeur (permutation)",
                    f"{perm['p_value']:.2f}",
                    help=(
                        f"Sil. observé : {perm['observed_silhouette']:.3f} — "
                        f"max null : {perm['max_null_silhouette']:.3f}. "
                        "p < 0,05 : structure non aléatoire."
                    ),
                )

    # -------------------------------------------------------------------------
    # Tab: Comparateur A/B
    # -------------------------------------------------------------------------

    def _render_ab_tab(self) -> None:
        st.caption("Sauvegardez deux configurations pour les comparer.")
        results = st.session_state.get(_results_key())

        col_save_a, col_save_b = st.columns(2)
        with col_save_a:
            if st.button(
                "Sauvegarder comme config A",
                disabled=(results is None),
                key=self._state.widget_key("save_a"),
            ):
                st.session_state[_results_key("a")] = results
                st.success("Config A sauvegardée.")
        with col_save_b:
            if st.button(
                "Sauvegarder comme config B",
                disabled=(results is None),
                key=self._state.widget_key("save_b"),
            ):
                st.session_state[_results_key("b")] = results
                st.success("Config B sauvegardée.")

        res_a = st.session_state.get(_results_key("a"))
        res_b = st.session_state.get(_results_key("b"))

        if res_a is None or res_b is None:
            st.info("Sauvegardez deux configurations pour lancer la comparaison.")
            return

        comp = compare_configurations(
            routes_a=pd.Index(res_a["routes"]),
            labels_a=res_a["labels"],
            routes_b=pd.Index(res_b["routes"]),
            labels_b=res_b["labels"],
        )
        st.divider()
        m1, m2, m3 = st.columns(3)
        ari_val = f"{comp['ari']:.3f}" if not np.isnan(comp["ari"]) else "—"
        m1.metric("ARI (accord A↔B)", ari_val)
        m2.metric("Liaisons communes", fmt_number(comp["n_common"]))
        m3.metric("Liaisons qui changent", fmt_number(comp["n_changed"]))

        col_a_col, col_b_col = st.columns(2)
        for col, res, lbl in [
            (col_a_col, res_a, "Config A"),
            (col_b_col, res_b, "Config B"),
        ]:
            with col:
                st.markdown(f"**{lbl}**")
                st.json(res["params"], expanded=False)

        if comp["n_changed"] > 0 and comp["changed_routes"]:
            with st.expander(f"{comp['n_changed']} liaisons qui changent de profil"):
                st.write(comp["changed_routes"])

    # -------------------------------------------------------------------------
    # URL sync helpers
    # -------------------------------------------------------------------------

    def _sync_params_from_url(self) -> None:
        qp = st.query_params
        key_map = {
            "feature_set": self._state.widget_key("feature_set"),
            "exclusion": self._state.widget_key("exclusion"),
            "scaler": self._state.widget_key("scaler"),
            "algorithm": self._state.widget_key("algorithm"),
        }
        for qk, sk in key_map.items():
            if qk in qp and sk not in st.session_state:
                st.session_state[sk] = qp[qk]

    def _sync_params_to_url(self, params: dict) -> None:
        st.query_params.update(
            {
                "feature_set": params["feature_set"],
                "exclusion": params["exclusion"],
                "scaler": params["scaler"],
                "algorithm": params["algorithm"],
                "k": str(params["k"]),
            }
        )


# Script entry point — executed by Streamlit when this file is a st.Page target.
try:
    Q3Page(get_provider()).render()
except RailInsightError as exc:
    st.warning(f"⚠️ {exc}")
except Exception:
    logger.exception("Unexpected error in q3 entry point")
    st.error("Une erreur inattendue s'est produite.")
