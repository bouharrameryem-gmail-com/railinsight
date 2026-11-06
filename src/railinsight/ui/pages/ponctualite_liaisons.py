"""Page : profils de ponctualité des liaisons TGV."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from railinsight.analysis.indicateurs_liaisons import FEATURE_SETS
from railinsight.backend.profils_ponctualite import (
    ResultatClustering,
    charger_donnees_clean,
    clusteriser,
    construire_indicateurs,
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

_JEU_PAR_DEFAUT = "v3"

_NOMS_EXCLUSION = {
    "none": "Tous les mois",
    "known": "Sans grèves et Covid (recommandé)",
}

_LABELS_JEU = {
    "v3": "Retards et irrégularité (recommandé)",
    "fixed": "Fréquence & chronicité",
    "composite": "Arrivée & délai moyen",
}

_LABELS_COLONNES: dict[str, str] = {
    "cancellation_rate": "Taux d'annulation",
    "late15_rate": "Retards > 15 min",
    "severe_share": "Part retards sévères (> 30 min)",
    "extreme_share": "Part retards extrêmes (> 60 min)",
    "volatility_cv": "Irrégularité mensuelle (CV)",
    "volatility": "Irrégularité mensuelle",
    "chronicity": "Chronicité",
    "late_arrival_rate": "Taux de retard à l'arrivée",
    "mean_delay_when_late": "Délai moyen quand retard",
    "severe_ratio": "Ratio retards sévères",
    "irregularity": "Irrégularité",
}


@st.cache_data(show_spinner=False)
def _donnees_brutes() -> pd.DataFrame:
    return charger_donnees_clean()


@st.cache_data(show_spinner=False)
def _mois_disponibles() -> list[str]:
    return sorted(_donnees_brutes()["mois"].unique().tolist())


@st.cache_data(show_spinner="Calcul des profils…")
def _analyser(
    debut: str | None, fin: str | None, exclusion: str, k: int | None, jeu: str
) -> ResultatClustering:
    donnees = _donnees_brutes()
    indicateurs = construire_indicateurs(donnees, debut=debut, fin=fin, exclusion=exclusion)
    return clusteriser(indicateurs, k=k, jeu_variables=jeu)


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

    def _render_controls(self) -> None:
        mois = _mois_disponibles()
        debut_opts = [None] + mois
        fin_opts = [None] + mois

        col_periode, col_excl, col_k = st.columns(3)

        col_periode.selectbox(
            "Période — début",
            options=debut_opts,
            format_func=lambda x: "Depuis le début" if x is None else x,
            key=self._etat.widget_key("debut"),
        )
        col_periode.selectbox(
            "Période — fin",
            options=fin_opts,
            format_func=lambda x: "Jusqu'à la fin" if x is None else x,
            index=len(fin_opts) - 1,
            key=self._etat.widget_key("fin"),
        )

        col_excl.radio(
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

        k_mode_key = self._etat.widget_key("k_mode")
        col_k.radio(
            "Nombre de profils",
            options=["auto", "manuel"],
            format_func=lambda x: "Automatique" if x == "auto" else "Je choisis",
            index=0,
            key=k_mode_key,
        )
        k_mode_actuel = st.session_state.get(k_mode_key, "auto")
        col_k.slider(
            "Nombre de profils souhaité",
            min_value=2,
            max_value=5,
            value=3,
            key=self._etat.widget_key("k_manuel"),
            disabled=(k_mode_actuel == "auto"),
        )

        jeu_key = self._etat.widget_key("jeu")
        st.radio(
            "Critères de classification",
            options=list(_LABELS_JEU.keys()),
            format_func=_LABELS_JEU.__getitem__,
            index=0,
            horizontal=True,
            key=jeu_key,
        )
        jeu_actuel = st.session_state.get(jeu_key, _JEU_PAR_DEFAUT)
        colonnes_jeu = FEATURE_SETS.get(jeu_actuel, FEATURE_SETS[_JEU_PAR_DEFAUT])
        labels_jeu = [_LABELS_COLONNES.get(c, c) for c in colonnes_jeu]
        st.caption("Critères utilisés : " + " · ".join(labels_jeu))

    def _render_body(self) -> None:
        debut = st.session_state.get(self._etat.widget_key("debut"))
        fin = st.session_state.get(self._etat.widget_key("fin"))
        exclusion = st.session_state.get(self._etat.widget_key("exclusion"), "known")
        k_mode = st.session_state.get(self._etat.widget_key("k_mode"), "auto")
        k_manuel = st.session_state.get(self._etat.widget_key("k_manuel"), 3)
        jeu = st.session_state.get(self._etat.widget_key("jeu"), _JEU_PAR_DEFAUT)

        k = None if k_mode == "auto" else k_manuel

        try:
            resultats = _analyser(debut, fin, exclusion, k, jeu)
        except RailInsightError as exc:
            st.warning(str(exc))
            return
        except Exception:
            logger.exception("Erreur inattendue profils ponctualité")
            st.error("Le calcul a échoué. Essayez avec d'autres paramètres.")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Liaisons analysées", fmt_number(len(resultats.etiquettes)))
        c2.metric("Profils trouvés", str(resultats.k))
        c3.metric(
            "Score de cohérence",
            f"{resultats.silhouette:.2f}",
            help=(
                "Entre 0 et 1. Au-dessus de 0,20, les groupes sont distincts. "
                "Plus c'est élevé, mieux les liaisons similaires sont regroupées."
            ),
        )

        if resultats.redondances:
            with st.expander("Corrélations élevées entre critères", expanded=True):
                for col_a, col_b, rho in resultats.redondances:
                    label_a = _LABELS_COLONNES.get(col_a, col_a)
                    label_b = _LABELS_COLONNES.get(col_b, col_b)
                    st.warning(
                        f"**{label_a}** et **{label_b}** sont très corrélés "
                        f"(ρ = {rho:.2f}). Ces deux critères apportent une "
                        "information similaire — le profil peut en être biaisé."
                    )

        onglet_profils, onglet_liaison = st.tabs(["Les profils", "Ma liaison"])
        with onglet_profils:
            self._afficher_profils(resultats, jeu)
        with onglet_liaison:
            self._trouver_liaison(resultats, jeu)

    def _afficher_profils(self, resultats: ResultatClustering, jeu: str) -> None:
        """Cartes descriptives + nuage de points PCA."""
        colonnes = st.columns(min(resultats.k, 2))
        for c in range(resultats.k):
            with colonnes[c % 2]:
                self._carte_profil(c, resultats, jeu)

        st.divider()

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

    def _carte_profil(
        self, cluster_idx: int, resultats: ResultatClustering, jeu: str
    ) -> None:
        """Affiche un résumé chiffré d'un profil."""
        masque = resultats.etiquettes == cluster_idx
        nom = resultats.noms_clusters.get(cluster_idx, f"Profil {cluster_idx + 1}")
        couleur = CLUSTER_COLORS[cluster_idx % len(CLUSTER_COLORS)]
        n = int(masque.sum())

        indicateurs_cluster = resultats.indicateurs[masque]
        colonnes_jeu = FEATURE_SETS.get(jeu, FEATURE_SETS[_JEU_PAR_DEFAUT])
        lignes = []
        for col in colonnes_jeu:
            label = _LABELS_COLONNES.get(col, col)
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

    def _trouver_liaison(self, resultats: ResultatClustering, jeu: str) -> None:
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
        colonnes_jeu = FEATURE_SETS.get(jeu, FEATURE_SETS[_JEU_PAR_DEFAUT])
        metriques = {
            _LABELS_COLONNES.get(col, col): fmt_pct(float(ligne[col]))
            for col in colonnes_jeu
            if col in ligne.index and not np.isnan(float(ligne[col]))
        }
        if metriques:
            cols = st.columns(len(metriques))
            for col_ui, (label, val) in zip(cols, metriques.items(), strict=False):
                col_ui.metric(label, val)

    def _render_method_box(self) -> None:
        method_box(
            "**Méthode.** Les liaisons sont décrites par des indicateurs de ponctualité "
            "(annulations, retards, irrégularité mensuelle). "
            "Un algorithme K-means regroupe les liaisons similaires. "
            "Les mois de grèves et de Covid peuvent être exclus "
            "pour ne pas biaiser les résultats.\n\n"
            "**Limites.** Les groupes ne sont pas rigides : certaines liaisons "
            "sont à la frontière entre deux profils. "
            "Le nombre de profils est un choix d'analyse, pas une vérité absolue."
        )


PageProfilsPonctualite(get_provider()).render()
