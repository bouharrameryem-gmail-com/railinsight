"""Q3 — Laboratoire de clustering (page d'exploration).

Permet de choisir librement l'algorithme, ses hyperparamètres et les paramètres
de prétraitement, puis de visualiser les résultats et leur robustesse.
Supporte un comparateur A/B entre deux configurations.

Script entry point — executed by Streamlit when this file is a st.Page target.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
import plotly.express as px
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
from railinsight.ui.components.kpi_card import kpi_row
from railinsight.ui.components.method_box import method_box
from railinsight.ui.components.pca_panel import pca_panel
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.tokens import CLUSTER_COLORS
from railinsight.utils.formatting import fmt_number

logger = logging.getLogger(__name__)

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
    "v3": "v3 — recommandé (sévérité)",
    "fixed": "fixed v2 (fréquence + volatilité)",
    "composite": "composite v1 (arrivée + retard moyen)",
    "custom": "Sélection libre",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_lab_analysis(
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

    Returns a dict with all results needed to render the lab outputs.
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
    x_df = features[available_cols].dropna()  # noqa: N806

    if len(x_df) < 4:  # noqa: PLR2004
        raise InsufficientDataError("Pas assez de liaisons après filtrage.")

    x_scaled, scaler = scale_features(x_df, scaler_type)  # noqa: N806

    if k_mode == "auto":
        k = auto_select_k(x_scaled, algorithm)
    else:
        k = k_manual

    labels = fit_clustering(
        x_scaled,
        algorithm,
        k,
        n_init=n_init,
        covariance_type=covariance_type,
    )
    sil = float(silhouette_score(x_scaled, labels))

    pca_model = PCA(n_components=2, random_state=42).fit(x_scaled)
    x_pca = pca_model.transform(x_scaled)  # noqa: N806

    centroids_scaled = np.array([x_scaled[labels == c].mean(axis=0) for c in range(k)])
    try:
        centroids_original = scaler.inverse_transform(centroids_scaled)
    except Exception:
        centroids_original = centroids_scaled

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


def _results_key(slot: str) -> str:
    return f"q3_lab__results_{slot}"


# ---------------------------------------------------------------------------
# Page class
# ---------------------------------------------------------------------------


class Q3LabPage(BasePage):
    """Interactive Q3 clustering laboratory.

    Users choose algorithm, hyperparameters and preprocessing options, then
    run the analysis on demand. Supports A/B configuration comparison.

    Args:
        provider: Data provider satisfying the DataProvider protocol.
    """

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._state = PageState(page_key="q3_lab")

    @property
    def question_number(self) -> int:
        return 3

    @property
    def question_title(self) -> str:
        return "Laboratoire Q3 — Profils de ponctualité"

    @property
    def author(self) -> str:
        return "Bachelard"

    # --- Template method sections ---

    def _render_key_figures(self) -> None:
        results = st.session_state.get(_results_key("current"))
        if results is None:
            kpi_row(
                [
                    {"label": "Liaisons analysées", "value": "—"},
                    {"label": "k (profils)", "value": "—"},
                    {"label": "Silhouette", "value": "—"},
                    {"label": "Plus petit groupe", "value": "—"},
                ]
            )
            return

        labels = results["labels"]
        k = results["k"]
        sil = results["silhouette"]
        _, counts = np.unique(labels, return_counts=True)
        kpi_row(
            [
                {"label": "Liaisons analysées", "value": fmt_number(len(labels))},
                {"label": "k (profils)", "value": str(k)},
                {
                    "label": "Silhouette",
                    "value": f"{sil:.3f}",
                    "help": "Entre −1 et 1 ; > 0,2 indique une structure non triviale.",
                },
                {"label": "Plus petit groupe", "value": str(int(counts.min()))},
            ]
        )

    def _render_controls(self) -> None:
        """Render parameter form and trigger analysis on submission."""
        self._sync_params_from_url()

        monthly = self._provider.load_clean_monthly()
        network = self._provider.load_network_monthly()

        with st.form(key="q3_lab_params"):
            st.markdown("##### Données")
            col1, col2 = st.columns(2)
            with col1:
                exclusion = exclusion_filter(key_prefix=self._state.page_key)
                min_months = min_months_filter(key_prefix=self._state.page_key)
            with col2:
                adjust = duration_adjust_toggle(key_prefix=self._state.page_key)

            st.markdown("##### Indicateurs")
            fs_choice = st.radio(
                "Jeu d'indicateurs",
                options=list(_FEATURE_SET_LABELS.keys()),
                format_func=lambda k: _FEATURE_SET_LABELS[k],
                index=0,
                key=self._state.widget_key("feature_set"),
                horizontal=False,
            )
            custom_cols: list[str] = []
            if fs_choice == "custom":
                custom_cols = st.multiselect(
                    "Choisissez les indicateurs",
                    options=ALL_FEATURE_COLS,
                    default=FEATURE_SETS["v3"],
                    key=self._state.widget_key("custom_cols"),
                )

            st.markdown("##### Prétraitement")
            scaler_choice = st.radio(
                "Mise à l'échelle",
                options=list(_SCALER_LABELS.keys()),
                format_func=lambda k: _SCALER_LABELS[k],
                index=0,
                key=self._state.widget_key("scaler"),
                horizontal=True,
            )

            st.markdown("##### Algorithme et hyperparamètres")
            algo = st.radio(
                "Algorithme",
                options=list(_ALGO_LABELS.keys()),
                format_func=lambda k: _ALGO_LABELS[k],
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

            # Algorithm-specific hyperparameters
            n_init = 50
            cov_type: Literal["full", "tied", "diag", "spherical"] = "full"
            if algo == "kmeans":
                n_init = st.slider(
                    "n_init (K-means — initialisations aléatoires)",
                    min_value=10,
                    max_value=100,
                    value=50,
                    step=10,
                    key=self._state.widget_key("n_init"),
                    help=(
                        "K-means relance depuis n_init points de départ aléatoires "
                        "et garde le meilleur résultat. "
                        "Plus élevé = plus stable mais plus lent."
                    ),
                )
            elif algo == "gmm":
                cov_choice = st.selectbox(
                    "Type de covariance (GMM)",
                    options=["full", "tied", "diag", "spherical"],
                    index=0,
                    key=self._state.widget_key("cov_type"),
                    help=(
                        "**full** : chaque composante a sa propre matrice "
                        "de covariance (le plus flexible). "
                        "**tied** : toutes partagent la même. "
                        "**diag** : matrices diagonales "
                        "(pas de corrélation entre variables). "
                        "**spherical** : matrices sphériques "
                        "(variance isotrope par composante)."
                    ),
                )
                cov_type = cov_choice  # type: ignore[assignment]

            submitted = st.form_submit_button(
                "Lancer l'analyse", type="primary", use_container_width=True
            )

        if submitted:
            with st.spinner("Calcul en cours…"):
                try:
                    results = _run_lab_analysis(
                        monthly=monthly,
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
                    st.session_state[_results_key("current")] = results
                    logger.info(
                        "Q3 lab analysis: algo=%s k=%d sil=%.3f",
                        algo,
                        results["k"],
                        results["silhouette"],
                    )
                    self._sync_params_to_url(results["params"])
                except RailInsightError as exc:
                    st.warning(f"⚠️ {exc}")
                except Exception:
                    logger.exception("Q3 lab analysis failed")
                    st.error("L'analyse a échoué. Vérifiez les paramètres.")

    def _render_body(self) -> None:
        results = st.session_state.get(_results_key("current"))
        if results is None:
            st.info(
                "Configurez les paramètres ci-dessus et cliquez **Lancer l'analyse**."
            )
            return

        self._show_redundancy_warnings(results)
        self._render_silhouette_section(results)
        st.divider()
        self._render_pca_section(results)
        st.divider()
        self._render_centroid_heatmap(results)
        st.divider()
        self._render_eta2_section(results)
        st.divider()
        self._render_robustness_section(results)
        st.divider()
        self._render_ab_comparator()

    def _render_method_box(self) -> None:
        results = st.session_state.get(_results_key("current"))
        if results is None:
            return
        params = results["params"]
        method_box(
            content=f"""
**Configuration courante :**
Jeu d'indicateurs : `{params["feature_set"]}` ·
Exclusion mois : `{params["exclusion"]}` ·
Ajustement durée : `{"oui" if params["adjust_duration"] else "non"}` ·
Mise à l'échelle : `{params["scaler"]}` ·
Algorithme : `{params["algorithm"]}` ·
k : `{params["k"]}`.

**Silhouette :** mesure la cohésion des groupes (−1 à 1).
**Davies-Bouldin :** mesure la séparation des groupes (plus bas = mieux).
**ARI :** Adjusted Rand Index, robustesse entre deux solutions
(0 = aléatoire, 1 = identique).
**η² :** fraction de la variance de chaque indicateur
expliquée par l'appartenance au groupe.
""",
        )

    # ---------------------------------------------------------------------------
    # Body sub-sections
    # ---------------------------------------------------------------------------

    def _show_redundancy_warnings(self, results: dict) -> None:
        for col_a, col_b, rho in results["redundant"]:
            st.warning(
                f"⚠️ **Redondance détectée** : `{col_a}` et `{col_b}` "
                f"sont très corrélés (ρ de Spearman = {rho:+.2f}). "
                "Inclure les deux surpondère cette dimension dans le clustering."
            )

    def _render_silhouette_section(self, results: dict) -> None:
        st.markdown("#### Courbes de sélection de k")
        with st.spinner("Calcul des scores pour k = 2 à 8…"):
            curve = silhouette_curve(
                results["X_scaled"],
                results["algorithm"],
                k_range=range(2, 9),
            )

        tab_sil, tab_db, tab_size = st.tabs(
            ["Silhouette", "Davies-Bouldin", "Taille min. du groupe"]
        )
        with tab_sil:
            fig = px.line(
                curve,
                x="k",
                y="silhouette",
                markers=True,
                labels={"silhouette": "Score silhouette", "k": "Nombre de profils k"},
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
                    "Plus c'est haut, mieux c'est. Le pic indique le k optimal."
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
            fig.add_hline(
                y=3,
                line_dash="dot",
                annotation_text="seuil min = 3",
            )
            chart_container(
                fig,
                title="Taille du plus petit groupe selon k",
                how_to_read=(
                    "Un groupe trop petit (< 3) est suspect : "
                    "il peut refléter des outliers, pas un profil structuré."
                ),
            )

    def _render_pca_section(self, results: dict) -> None:
        labels = results["labels"]
        k = results["k"]
        label_names = {c: f"Profil {c + 1}" for c in range(k)}
        pca_panel(
            pca=results["pca"],
            x_pca=results["X_pca"],
            feature_names=[c.replace("_adj", "") for c in results["input_cols"]],
            labels=labels,
            label_names=label_names,
        )

    def _render_centroid_heatmap(self, results: dict) -> None:
        k = results["k"]
        base_cols = results["base_cols"]
        centroids = results["centroids_original"]

        row_labels = [f"Profil {c + 1}" for c in range(k)]
        col_labels = [c.replace("_", " ") for c in base_cols]

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
        chart_container(
            fig,
            title="Centroïdes des profils",
            how_to_read=(
                "Valeurs dans l'espace mis à l'échelle. "
                "Rouge = valeur élevée relative, vert = valeur faible."
            ),
        )

    def _render_eta2_section(self, results: dict) -> None:
        st.markdown("#### Pouvoir discriminant des indicateurs (η²)")
        features = results["features"]
        labels = results["labels"]
        # Evaluate on all available Q3 columns
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
            key="q3_lab__eta2_table",
        )
        with st.expander("Comment lire η² ?", expanded=False):
            st.markdown(
                "η² (eta carré) mesure quelle fraction de la variance totale "
                "d'un indicateur est expliquée par l'appartenance au groupe. "
                "0 = l'indicateur ne distingue pas du tout les groupes ; "
                "1 = l'indicateur suffit à lui seul à séparer les groupes "
                "parfaitement. "
                "Un η² > 0,3 est considéré élevé dans ce contexte."
            )

    def _render_robustness_section(self, results: dict) -> None:
        st.markdown("#### Robustesse de la solution")

        col_seeds, col_bootstrap, col_perm = st.columns(3)

        with col_seeds:
            if st.button(
                "Tester la stabilité (seeds)",
                key=self._state.widget_key("btn_seeds"),
                help=(
                    "Lance le même algorithme avec 20 seeds différentes "
                    "et calcule l'ARI moyen."
                ),
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
                "Tester la stabilité (bootstrap)",
                key=self._state.widget_key("btn_bootstrap"),
                help=(
                    "Rééchantillonne 80 % des liaisons 30 fois et calcule l'ARI médian."
                ),
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
                help=(
                    "Génère 30 jeux de données permutés "
                    "et compare le silhouette observé."
                ),
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
                        f"Silhouette observé : {perm['observed_silhouette']:.3f} — "
                        f"max null : {perm['max_null_silhouette']:.3f}. "
                        "p < 0,05 : la structure dépasse le niveau du hasard."
                    ),
                )

    def _render_ab_comparator(self) -> None:
        st.markdown("#### Comparateur A / B")
        st.caption("Sauvegardez deux configurations pour les comparer côte à côte.")
        results = st.session_state.get(_results_key("current"))

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

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        ari_val = f"{comp['ari']:.3f}" if not np.isnan(comp["ari"]) else "—"
        m1.metric("ARI (accord A↔B)", ari_val)
        m2.metric("Liaisons communes", fmt_number(comp["n_common"]))
        m3.metric("Liaisons qui changent", fmt_number(comp["n_changed"]))

        col_a_col, col_b_col = st.columns(2)
        for col, res, label in [
            (col_a_col, res_a, "Config A"),
            (col_b_col, res_b, "Config B"),
        ]:
            with col:
                params = res["params"]
                st.markdown(f"**{label}**")
                st.json(params, expanded=False)

        if comp["n_changed"] > 0 and comp["changed_routes"]:
            with st.expander(f"{comp['n_changed']} liaisons qui changent de profil"):
                st.write(comp["changed_routes"])

    # ---------------------------------------------------------------------------
    # URL synchronisation helpers
    # ---------------------------------------------------------------------------

    def _sync_params_from_url(self) -> None:
        """Pre-populate session state from query parameters on first load."""
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
        """Write current configuration to query parameters for URL sharing."""
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
    Q3LabPage(get_provider()).render()
except RailInsightError as exc:
    st.warning(f"⚠️ {exc}")
except Exception:
    logger.exception("Unexpected error in q3_lab entry point")
    st.error("Une erreur inattendue s'est produite.")
