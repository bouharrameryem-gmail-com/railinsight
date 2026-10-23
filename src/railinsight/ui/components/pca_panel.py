"""PCA panel: always renders the individuals scatter plot AND the correlation circle.

Team rule: every PCA display must include both plots side by side.
Without the correlation circle, we cannot tell which variables drive each axis.

Usage:
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2).fit(X_scaled)
    X_pca = pca.transform(X_scaled)
    pca_panel(pca, X_pca, feature_names=df.columns.tolist(), labels=cluster_labels)
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA

from railinsight.ui.theme.tokens import CLUSTER_COLORS, GRAY_400, GRAY_900


def pca_panel(
    pca: PCA,
    x_pca: np.ndarray,
    feature_names: list[str],
    labels: np.ndarray | None = None,
    label_names: dict[int, str] | None = None,
    title: str = "Analyse en composantes principales",
) -> None:
    """Render the PCA individuals scatter AND the correlation circle side by side.

    This is a team rule: never display one without the other.
    - Left plot: each observation (route) projected on PC1/PC2, colored by cluster.
    - Right plot: correlation circle showing which original variables drive each axis.

    Args:
        pca: A fitted sklearn PCA object (needs .components_ and
            .explained_variance_ratio_).
        x_pca: Projected data, shape (n_samples, n_components). Output of
            pca.transform(X).
        feature_names: Names of the original features (before PCA).
        labels: Optional integer cluster labels (0-indexed) for coloring.
            Length must equal n_samples.
        label_names: Optional dict mapping label int to cluster name string
            (e.g., {0: "Liaisons stables", 1: "Retards chroniques"}).
        title: Section heading displayed above the two plots.
    """
    var1 = pca.explained_variance_ratio_[0] * 100
    var2 = pca.explained_variance_ratio_[1] * 100

    st.markdown(f"**{title}**")
    st.caption(
        f"PC1 explique {var1:.1f} % de la variance, "
        f"PC2 explique {var2:.1f} % "
        f"(total : {var1 + var2:.1f} %)."
    )

    col_scatter, col_circle = st.columns(2)

    with col_scatter:
        st.plotly_chart(
            _individuals_plot(x_pca, labels, label_names, var1, var2),
            use_container_width=True,
        )

    with col_circle:
        st.plotly_chart(
            _correlation_circle(pca, feature_names, var1, var2),
            use_container_width=True,
        )


def _individuals_plot(
    x_pca: np.ndarray,
    labels: np.ndarray | None,
    label_names: dict[int, str] | None,
    var1: float,
    var2: float,
) -> go.Figure:
    """Build the individuals scatter plot."""
    fig = go.Figure()

    if labels is None:
        fig.add_trace(
            go.Scatter(
                x=x_pca[:, 0],
                y=x_pca[:, 1],
                mode="markers",
                marker={"color": GRAY_400, "size": 6, "opacity": 0.7},
                name="Liaisons",
            )
        )
    else:
        unique_labels = sorted(set(int(lb) for lb in labels))
        for i, lab in enumerate(unique_labels):
            mask = labels == lab
            name = (
                label_names.get(lab, f"Groupe {lab}")
                if label_names
                else f"Groupe {lab}"
            )
            fig.add_trace(
                go.Scatter(
                    x=x_pca[mask, 0],
                    y=x_pca[mask, 1],
                    mode="markers",
                    marker={
                        "color": CLUSTER_COLORS[i % len(CLUSTER_COLORS)],
                        "size": 7,
                        "opacity": 0.8,
                    },
                    name=name,
                )
            )

    fig.update_layout(
        title="Nuage des individus",
        xaxis_title=f"PC1 ({var1:.1f} %)",
        yaxis_title=f"PC2 ({var2:.1f} %)",
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.3},
    )
    fig.add_hline(y=0, line_dash="dot", line_color=GRAY_400, line_width=1)
    fig.add_vline(x=0, line_dash="dot", line_color=GRAY_400, line_width=1)

    return fig


def _correlation_circle(
    pca: PCA,
    feature_names: list[str],
    var1: float,
    var2: float,
) -> go.Figure:
    """Build the correlation circle (loadings plot).

    Each arrow points from the origin to (loading_on_PC1, loading_on_PC2)
    for one original variable. Variables close to the circle edge are well
    represented in the PC1/PC2 plane.
    """
    loadings_pc1 = pca.components_[0]
    loadings_pc2 = pca.components_[1]

    fig = go.Figure()

    # Unit circle
    theta = np.linspace(0, 2 * np.pi, 200)
    fig.add_trace(
        go.Scatter(
            x=np.cos(theta),
            y=np.sin(theta),
            mode="lines",
            line={"color": GRAY_400, "width": 1, "dash": "dot"},
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Arrows (one per variable)
    for name, lx, ly in zip(feature_names, loadings_pc1, loadings_pc2, strict=True):
        fig.add_annotation(
            ax=0,
            ay=0,
            x=float(lx),
            y=float(ly),
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor=GRAY_900,
        )
        # Label at the tip of the arrow (slightly offset)
        offset = 0.07
        fig.add_annotation(
            x=float(lx) + offset * np.sign(lx),
            y=float(ly) + offset * np.sign(ly),
            text=name,
            showarrow=False,
            font={"size": 10, "color": GRAY_900},
            xref="x",
            yref="y",
        )

    fig.update_layout(
        title="Cercle des corrélations",
        xaxis={
            "range": [-1.2, 1.2],
            "title": f"PC1 ({var1:.1f} %)",
            "zeroline": True,
            "zerolinecolor": GRAY_400,
        },
        yaxis={
            "range": [-1.2, 1.2],
            "title": f"PC2 ({var2:.1f} %)",
            "zeroline": True,
            "zerolinecolor": GRAY_400,
            "scaleanchor": "x",
        },
    )

    return fig
