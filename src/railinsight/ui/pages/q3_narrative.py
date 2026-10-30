"""Q3 — Profils de ponctualité (page grand public).
 
Présente les deux profils de liaisons TGV obtenus par clustering K-means
avec les paramètres issus du notebook v3 (jeu v3, Yeo-Johnson, exclusion
des mois connus, ajustement durée, k automatique).
 
Script entry point — executed by Streamlit when this file is a st.Page target.
"""
 
from __future__ import annotations
 
import logging
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
 
from railinsight.analysis.clustering import (
    GRAINE,
    MIN_LIAISONS_CLUSTERING,
    auto_select_k,
    fit_clustering,
    scale_features,
)
from railinsight.analysis.indicateurs_liaisons import (
    FEATURE_SETS,
    adjust_for_duration,
    build_q3_features,
)
from railinsight.exceptions import InsufficientDataError, RailInsightError
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.insight_box import insight_box
from railinsight.ui.components.kpi_card import kpi_row
from railinsight.ui.components.method_box import method_box
from railinsight.ui.components.pca_panel import pca_panel
from railinsight.ui.components.route_card import route_card
from railinsight.ui.donnees_regularite import charger_table_regularite
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.tokens import CLUSTER_COLORS
from railinsight.utils.formatting import fmt_number, fmt_pct
 
logger = logging.getLogger(__name__)
 
# ---------------------------------------------------------------------------
# Module-level cache: analysis runs once per server process per data snapshot
# ---------------------------------------------------------------------------
 
_CANONICAL_FEATURE_SET = "v3"
_CANONICAL_EXCLUSION = "known"
_CANONICAL_MIN_MONTHS = 24
_CANONICAL_SCALER = "power"
 
 
@st.cache_data(show_spinner="Calcul des profils de ponctualité…")
def _run_canonical_q3(table: pd.DataFrame) -> dict:
    """Lance l'analyse Q3 fixe (paramètres du notebook v3).
 
    Mise en cache selon le contenu du tableau : elle ne se relance que si les
    données changent.
 
    Args:
        table: Résultat de `nettoyer_regularite`, filtré sur un service.
 
    Returns:
        Un dict avec les résultats : indicateurs, étiquettes, ACP, centroïdes, etc.
    """
    features = build_q3_features(
        table,
        exclusion=_CANONICAL_EXCLUSION,
        min_months=_CANONICAL_MIN_MONTHS,
    )
    features, _ = adjust_for_duration(features, FEATURE_SETS[_CANONICAL_FEATURE_SET])
 
    # Use adjusted columns when available, otherwise original
    display_cols = FEATURE_SETS[_CANONICAL_FEATURE_SET]
    input_cols = [
        f"{c}_adj" if f"{c}_adj" in features.columns else c for c in display_cols
    ]
 
    x_df = features[input_cols].dropna()  # noqa: N806
    if len(x_df) < MIN_LIAISONS_CLUSTERING:
        raise InsufficientDataError("Pas assez de liaisons pour le clustering.")
 
    x_scaled, scaler = scale_features(x_df, _CANONICAL_SCALER)  # noqa: N806
    k = auto_select_k(x_scaled, "kmeans")
    labels = fit_clustering(x_scaled, "kmeans", k)
    sil = float(silhouette_score(x_scaled, labels))
 
    pca_model = PCA(n_components=2, random_state=GRAINE).fit(x_scaled)
    x_pca = pca_model.transform(x_scaled)  # noqa: N806
 
    centroids_scaled = np.array([x_scaled[labels == c].mean(axis=0) for c in range(k)])
    try:
        centroids_original = scaler.inverse_transform(centroids_scaled)
    except Exception:
        centroids_original = centroids_scaled
 
    # Assign cluster names based on late15_rate centroid
    late15_col = (
        "late15_rate_adj" if "late15_rate_adj" in features.columns else "late15_rate"
    )
    if late15_col in features.columns:
        # `labels` ne couvre que les liaisons sans valeur manquante (x_df après
        # dropna) : on aligne `features` sur ces mêmes liaisons, dans le même ordre.
        cluster_means = (
            features.loc[x_df.index].assign(_lbl=labels).groupby("_lbl")[late15_col].mean()
        )
        high_freq = int(cluster_means.idxmax())
    else:
        high_freq = 0
 
    cluster_names: dict[int, str] = {}
    for c in range(k):
        if k == 2:  # noqa: PLR2004
            cluster_names[c] = (
                "Fréquents & courts" if c == high_freq else "Rares & longs"
            )
        else:
            cluster_names[c] = f"Profil {c + 1}"
 
    return {
        "features": features,
        "routes": x_df.index.tolist(),
        "labels": labels,
        "k": k,
        "silhouette": sil,
        "pca": pca_model,
        "X_pca": x_pca,
        "X_scaled": x_scaled,
        "centroids_original": centroids_original,
        "input_cols": input_cols,
        "display_cols": display_cols,
        "cluster_names": cluster_names,
        "scaler": scaler,
    }
 
 
# ---------------------------------------------------------------------------
# Page class
# ---------------------------------------------------------------------------
 
 
class Q3NarrativePage(BasePage):
    """Grand-public page: punctuality profiles of TGV routes.
 
    Args:
        provider: Data provider satisfying the DataProvider protocol.
    """
 
    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._state = PageState(page_key="q3_narrative")
 
    @property
    def question_number(self) -> int:
        return 3
 
    @property
    def question_title(self) -> str:
        return "Profils de ponctualité des TGV"
 
    @property
    def author(self) -> str:
        return "Bachelard"
 
    @staticmethod
    def _resultats() -> dict:
        """Résultats de l'analyse fixe (calculée une fois, mise en cache)."""
        return _run_canonical_q3(charger_table_regularite())
 
    # --- Template method sections ---
 
    def _render_key_figures(self) -> None:
        results = self._resultats()
        labels = results["labels"]
        sil = results["silhouette"]
        unique, counts = np.unique(labels, return_counts=True)
 
        cards = [
            {"label": "Liaisons analysées", "value": fmt_number(len(labels))},
            {
                "label": "Score de cohérence",
                "value": f"{sil:.2f} / 1",
                "help": (
                    "Silhouette moyen : 0 = groupes qui se chevauchent, "
                    "1 = groupes parfaitement séparés. "
                    "Valeur > 0,20 indique une structure réelle mais peu marquée."
                ),
            },
        ]
        cluster_names = results["cluster_names"]
        for c, n in zip(unique, counts, strict=False):
            cards.append(
                {
                    "label": cluster_names.get(int(c), f"Profil {c + 1}"),
                    "value": f"{n} liaisons",
                }
            )
        kpi_row(cards)
 
    def _render_controls(self) -> None:
        adjusted = st.toggle(
            "Lecture à durée égale (ajusté)",
            value=True,
            key=self._state.widget_key("adjust_duration"),
            help=(
                "Les longues liaisons ont mécaniquement plus de retards. "
                "Ce mode retire cet effet pour comparer les profils équitablement."
            ),
        )
        if adjusted:
            st.caption(
                "Mode actif : les indicateurs sont corrigés de la durée du trajet. "
                "Les profils reflètent le comportement de la liaison "
                "indépendamment de sa distance."
            )
 
    def _render_body(self) -> None:
        results = self._resultats()
        labels = results["labels"]
        cluster_names = results["cluster_names"]
        k = results["k"]
 
        # --- Key finding ---
        insight_box(
            f"Le réseau TGV se divise en **{k} profils distincts** de ponctualité. "
            "Cette structure est statistiquement réelle (non aléatoire), "
            "mais la frontière entre les profils n'est pas nette : "
            "certaines liaisons « frontières » pourraient appartenir à l'un "
            "ou l'autre.",
        )
 
        # --- Cluster descriptions ---
        if k == 2:  # noqa: PLR2004
            col_a, col_b = st.columns(2)
            with col_a:
                self._render_cluster_card(0, results)
            with col_b:
                self._render_cluster_card(1, results)
 
        st.divider()
 
        # --- PCA ---
        label_names = {
            int(c): cluster_names.get(int(c), f"Profil {c + 1}") for c in range(k)
        }
        pca_panel(
            pca=results["pca"],
            x_pca=results["X_pca"],
            feature_names=[c.replace("_adj", "") for c in results["input_cols"]],
            labels=labels,
            label_names=label_names,
            title="Structure des profils en deux dimensions",
        )
 
        st.divider()
 
        # --- Centroid heatmap ---
        self._render_centroid_heatmap(results)
 
        st.divider()
 
        # --- Route finder ---
        self._render_route_finder(results)
 
    def _render_cluster_card(self, cluster_idx: int, results: dict) -> None:
        """Render a summary card for one cluster."""
        labels = results["labels"]
        routes = results["routes"]
        features = results["features"]
        cluster_names = results["cluster_names"]
        display_cols = results["display_cols"]
 
        mask = labels == cluster_idx
        name = cluster_names.get(cluster_idx, f"Profil {cluster_idx + 1}")
        color = CLUSTER_COLORS[cluster_idx % len(CLUSTER_COLORS)]
        n = int(mask.sum())
 
        route_subset = [r for r, m in zip(routes, mask, strict=False) if m]
        feat_subset = features.loc[route_subset, display_cols].mean()
 
        late15 = feat_subset.get("late15_rate", float("nan"))
        severe = feat_subset.get("severe_share", float("nan"))
 
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:12px 16px;'
            f'background:#F5F7FA;border-radius:4px;">'
            f'<strong style="color:{color};">{name}</strong><br>'
            f'<span style="font-size:0.85em;">'
            f"{n} liaisons · Retards > 15 min : "
            f"{fmt_pct(late15) if not np.isnan(late15) else '—'}"
            f" · Part sévère : {fmt_pct(severe) if not np.isnan(severe) else '—'}"
            f"</span></div>",
            unsafe_allow_html=True,
        )
 
    def _render_centroid_heatmap(self, results: dict) -> None:
        """Render a heatmap of cluster centroids in original scale."""
        k = results["k"]
        cluster_names = results["cluster_names"]
        display_cols = results["display_cols"]
        centroids = results["centroids_original"]
 
        col_labels = [
            c.replace("_", " ").replace(" rate", " (taux)") for c in display_cols
        ]
        row_labels = [cluster_names.get(c, f"Profil {c + 1}") for c in range(k)]
 
        # Format values: rate columns as %, others as raw
        rate_cols = {
            "cancellation_rate",
            "late15_rate",
            "late30_rate",
            "late60_rate",
            "severe_share",
            "extreme_share",
            "late_arrival_rate",
            "severe_ratio",
            "volatility_cv",
            "chronicity",
            "irregularity",
            "volatility",
        }
        text = []
        for row in centroids:
            row_text = []
            for val, col in zip(row, display_cols, strict=False):
                col_base = col.replace("_adj", "")
                if col_base in rate_cols:
                    row_text.append(fmt_pct(float(val)))
                else:
                    row_text.append(f"{val:.1f}")
            text.append(row_text)
 
        fig = go.Figure(
            go.Heatmap(
                z=centroids,
                x=col_labels,
                y=row_labels,
                text=text,
                texttemplate="%{text}",
                colorscale="RdYlGn_r",
                showscale=True,
            )
        )
        fig.update_layout(
            xaxis={"side": "bottom"},
            margin={"l": 140, "r": 20, "t": 30, "b": 60},
        )
        chart_container(
            fig,
            title="Centroïdes des profils — valeurs moyennes par indicateur",
            how_to_read=(
                "Chaque ligne est un profil, chaque colonne un indicateur. "
                "Le rouge indique une valeur élevée (moins bon), "
                "le vert une valeur faible. "
                "Comparez les lignes pour voir ce qui distingue les profils."
            ),
        )
 
    def _render_route_finder(self, results: dict) -> None:
        """Render the 'Find my route' interactive section."""
        st.markdown("#### Trouver le profil d'une liaison")
 
        routes = results["routes"]
        labels = results["labels"]
        features = results["features"]
        cluster_names = results["cluster_names"]
        display_cols = results["display_cols"]
 
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
        for col in display_cols:
            val = feat_row.get(col, float("nan"))
            if isinstance(val, float) and not np.isnan(val):
                col_base = col.replace("_adj", "")
                if col_base in {
                    "cancellation_rate",
                    "late15_rate",
                    "severe_share",
                    "extreme_share",
                    "late_arrival_rate",
                }:
                    indicators[col.replace("_", " ")] = fmt_pct(val)
                else:
                    indicators[col.replace("_", " ")] = f"{val:.3f}"
 
        # La durée peut être manquante (NaN) : on ne l'affiche alors pas.
        duree = feat_row.get("trip_duration_min", float("nan"))
        if not np.isnan(duree):
            dur = int(duree)
            indicators["Durée médiane"] = f"{dur // 60} h {dur % 60:02d}"
        if "n_months" in feat_row.index:
            indicators["Mois observés"] = str(int(feat_row["n_months"]))
 
        route_card(
            route=selected,
            indicators=indicators,
            cluster_name=name,
            color=color,
        )
 
    def _render_method_box(self) -> None:
        method_box(
            content="""
**Méthode :** clustering K-means sur 5 indicateurs agrégés par liaison (jeu v3 du
notebook) : taux d'annulation, taux de retard > 15 min, part sévère (> 30 min parmi
> 15 min), part extrême (> 60 min parmi > 15 min), coefficient de variation mensuel.
Les mois exceptionnels documentés (grèves, Covid) sont exclus. Les indicateurs
corrélés à la durée du trajet sont ajustés par régression OLS en espace log.
La mise à l'échelle utilise la transformation de Yeo-Johnson.
Le nombre de profils *k* est sélectionné automatiquement par score silhouette
(meilleur score parmi *k* = 2 à 8, avec au moins 3 liaisons par groupe).
 
**Limites :**
- Les deux profils forment un continuum, pas deux groupes nets (silhouette ≈ 0,26).
  K-means impose une frontière artificielle.
- L'ajustement de durée repose sur une régression linéaire simple dans l'espace log ;
  il peut laisser une corrélation résiduelle.
- Les liaisons avec moins de 24 mois de données valides sont exclues.
""",
        )
 
 
# Script entry point — executed by Streamlit when this file is a st.Page target.
try:
    Q3NarrativePage(get_provider()).render()
except RailInsightError as exc:
    st.warning(f"⚠️ {exc}")
except Exception:
    logger.exception("Unexpected error in q3_narrative entry point")
    st.error("Une erreur inattendue s'est produite.")