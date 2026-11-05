"""Page : profils de ponctualité des liaisons TGV."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from railinsight.backend.profils_ponctualite import (
    ResultatClustering,
    charger_indicateurs,
    clusteriser,
)
from railinsight.exceptions import RailInsightError
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.method_box import method_box
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.tokens import CLUSTER_COLORS
from railinsight.utils.formatting import fmt_number, fmt_pct

logger = logging.getLogger(__name__)

_CLE_RESULTATS = "ponctualite__resultats"

_NOMS_EXCLUSION = {
    "none": "Tous les mois",
    "known": "Sans grèves et Covid (recommandé)",
}

_LABELS_INDICATEURS = {
    "cancellation_rate": "Taux d'annulation",
    "late15_rate": "Retards > 15 min",
    "severe_share": "Part des retards sévères (> 30 min)",
    "extreme_share": "Part des retards extrêmes (> 60 min)",
    "volatility_cv": "Irrégularité mensuelle",
}


@st.cache_data(show_spinner="Calcul des indicateurs…")
def _charger(exclusion: str, min_mois: int) -> pd.DataFrame:
    return charger_indicateurs(exclusion=exclusion, min_mois=min_mois)


class PageProfilsPonctualite(BasePage):
    """Regroupe les liaisons TGV par profil de ponctualité via K-means."""

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._etat = PageState(page_key="ponctualite")

    @property
    def question_number(self) -> int:
        return 3

    @property
    def question_title(self) -> str:
        return "Profils de ponctualité des liaisons TGV"

    @property
    def author(self) -> str:
        return "Bachelard"

    def _render_key_figures(self) -> None:
        st.write(
            "Peut-on regrouper les liaisons TGV selon leur comportement ? "
            "Le clustering identifie des profils — des groupes de liaisons "
            "qui se ressemblent en termes de ponctualité."
        )
        resultats: ResultatClustering | None = st.session_state.get(_CLE_RESULTATS)
        liaisons_col, profils_col, coherence_col = st.columns(3)
        if resultats is None:
            liaisons_col.metric("Liaisons analysées", "—")
            profils_col.metric("Profils trouvés", "—")
            coherence_col.metric("Score de cohérence", "—")
            return
        liaisons_col.metric("Liaisons analysées", fmt_number(len(resultats.etiquettes)))
        profils_col.metric("Profils trouvés", str(resultats.k))
        coherence_col.metric(
            "Score de cohérence",
            f"{resultats.silhouette:.2f}",
            help=(
                "Entre 0 et 1. Au-dessus de 0,20, les groupes sont distincts. "
                "Plus c'est élevé, mieux les liaisons similaires sont regroupées."
            ),
        )

    def _render_controls(self) -> None:
        with st.form(key="ponctualite_form"):
            col_excl, col_k = st.columns(2)
            exclusion = col_excl.radio(
                "Périodes à inclure",
                options=list(_NOMS_EXCLUSION.keys()),
                format_func=_NOMS_EXCLUSION.__getitem__,
                index=1,
                key=self._etat.widget_key("exclusion"),
                help=(
                    "Les grèves de 2018-2019 et le Covid 2020-2021 "
                    "ont fortement perturbé les données."
                ),
            )
            k_mode = col_k.radio(
                "Nombre de profils",
                options=["auto", "manuel"],
                format_func=lambda x: "Automatique" if x == "auto" else "Je choisis",
                index=0,
                horizontal=True,
                key=self._etat.widget_key("k_mode"),
            )
            k_manuel = col_k.slider(
                "Nombre de profils souhaité",
                min_value=2,
                max_value=5,
                value=3,
                key=self._etat.widget_key("k_manuel"),
                disabled=(k_mode == "auto"),
            )
            soumis = st.form_submit_button(
                "Calculer les profils", type="primary", use_container_width=True
            )

        if soumis:
            with st.spinner("Calcul en cours…"):
                try:
                    indicateurs = _charger(exclusion, min_mois=24)
                    k = None if k_mode == "auto" else k_manuel
                    resultats = clusteriser(indicateurs, k=k)
                    st.session_state[_CLE_RESULTATS] = resultats
                    logger.info(
                        "Profils ponctualité : k=%d sil=%.3f",
                        resultats.k,
                        resultats.silhouette,
                    )
                    st.rerun()
                except RailInsightError as exc:
                    st.warning(str(exc))
                except Exception:
                    logger.exception("Erreur inattendue profils ponctualité")
                    st.error("Le calcul a échoué. Essayez avec d'autres paramètres.")

    def _render_body(self) -> None:
        resultats: ResultatClustering | None = st.session_state.get(_CLE_RESULTATS)
        if resultats is None:
            st.info(
                "Configurez les paramètres ci-dessus et cliquez **Calculer les profils**."
            )
            return

        onglet_profils, onglet_liaison = st.tabs(["Les profils", "Ma liaison"])
        with onglet_profils:
            self._afficher_profils(resultats)
        with onglet_liaison:
            self._trouver_liaison(resultats)

    def _afficher_profils(self, resultats: ResultatClustering) -> None:
        """Cartes descriptives + nuage de points PCA."""
        colonnes = st.columns(min(resultats.k, 2))
        for c in range(resultats.k):
            with colonnes[c % 2]:
                self._carte_profil(c, resultats)

        st.divider()

        mapping_cluster = dict(
            zip(resultats.indicateurs.index, resultats.etiquettes, strict=True)
        )
        df_pca = pd.DataFrame(
            {
                "Dimension 1": resultats.pca_coordonnees[:, 0],
                "Dimension 2": resultats.pca_coordonnees[:, 1],
                "Profil": [
                    resultats.noms_clusters.get(int(lbl), f"Profil {int(lbl) + 1}")
                    for lbl in resultats.etiquettes
                ],
                "Liaison": list(resultats.indicateurs.index),
            }
        )
        carte_couleurs = {
            resultats.noms_clusters.get(c, f"Profil {c + 1}"): CLUSTER_COLORS[
                c % len(CLUSTER_COLORS)
            ]
            for c in range(resultats.k)
        }
        fig = px.scatter(
            df_pca,
            x="Dimension 1",
            y="Dimension 2",
            color="Profil",
            hover_name="Liaison",
            color_discrete_map=carte_couleurs,
        )
        fig.update_traces(marker={"size": 8, "opacity": 0.8})
        fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
        chart_container(
            fig,
            title="Position des liaisons dans l'espace des profils",
            how_to_read=(
                "Chaque point est une liaison TGV. Les points proches se ressemblent "
                "en termes de ponctualité. La position n'est pas géographique."
            ),
        )
        # mapping_cluster utilisé uniquement pour construire df_pca
        _ = mapping_cluster

    def _carte_profil(self, cluster_idx: int, resultats: ResultatClustering) -> None:
        """Affiche un résumé chiffré d'un profil."""
        masque = resultats.etiquettes == cluster_idx
        nom = resultats.noms_clusters.get(cluster_idx, f"Profil {cluster_idx + 1}")
        couleur = CLUSTER_COLORS[cluster_idx % len(CLUSTER_COLORS)]
        n = int(masque.sum())

        indicateurs_cluster = resultats.indicateurs[masque]
        lignes = []
        for col, label in _LABELS_INDICATEURS.items():
            if col in indicateurs_cluster.columns:
                val = float(indicateurs_cluster[col].mean())
                if not np.isnan(val):
                    lignes.append(f"- {label} : **{fmt_pct(val)}**")

        contenu = f"{n} liaison{'s' if n > 1 else ''}\n\n" + "\n".join(lignes)
        st.markdown(
            f'<div style="border-left:4px solid {couleur};padding:12px 16px;'
            f"background:#F5F7FA;border-radius:4px;margin-bottom:8px;\">"
            f'<strong style="color:{couleur};">{nom}</strong><br>'
            f'<span style="font-size:0.85em;">{contenu}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    def _trouver_liaison(self, resultats: ResultatClustering) -> None:
        """Permet à l'utilisateur de trouver le profil d'une liaison spécifique."""
        st.write(
            "Choisissez une liaison pour découvrir à quel profil elle appartient "
            "et voir ses indicateurs de ponctualité."
        )
        mapping = dict(
            zip(resultats.indicateurs.index, resultats.etiquettes, strict=True)
        )
        liaisons = sorted(resultats.indicateurs.index)
        choisie = st.selectbox(
            "Liaison",
            options=liaisons,
            key=self._etat.widget_key("liaison_choisie"),
        )

        cluster = int(mapping[choisie])
        nom_cluster = resultats.noms_clusters.get(cluster, f"Profil {cluster + 1}")
        couleur = CLUSTER_COLORS[cluster % len(CLUSTER_COLORS)]

        st.markdown(
            f'<div style="border-left:4px solid {couleur};padding:12px 16px;'
            f"background:#F5F7FA;border-radius:4px;margin-bottom:16px;\">"
            f'<strong style="color:{couleur};">Profil : {nom_cluster}</strong>'
            f"</div>",
            unsafe_allow_html=True,
        )

        ligne = resultats.indicateurs.loc[choisie]
        metriques = {
            label: fmt_pct(float(ligne[col]))
            for col, label in _LABELS_INDICATEURS.items()
            if col in ligne.index and not np.isnan(float(ligne[col]))
        }
        cols = st.columns(len(metriques))
        for col_ui, (label, val) in zip(cols, metriques.items(), strict=False):
            col_ui.metric(label, val)

    def _render_method_box(self) -> None:
        method_box(
            "**Méthode.** Les liaisons sont décrites par 5 indicateurs de ponctualité "
            "(taux d'annulation, retards > 15 min, part des retards sévères, "
            "part des retards extrêmes, irrégularité mensuelle). "
            "Un algorithme K-means regroupe les liaisons similaires. "
            "Les mois de grèves et de Covid peuvent être exclus "
            "pour ne pas biaiser les résultats.\n\n"
            "**Limites.** Les groupes ne sont pas rigides : certaines liaisons "
            "sont à la frontière entre deux profils. "
            "Le nombre de profils est un choix d'analyse, pas une vérité absolue."
        )


PageProfilsPonctualite(get_provider()).render()
