"""Page Q1 : liaisons les moins fiables et évolution de leur taux d'incidents."""

import pandas as pd
import streamlit as st

from railinsight.analysis.liaisons_fiabilite import (
    REGLES_TENDANCE,
    AnalyseLiaisonsFiabilite,
)
from railinsight.backend.liaisons_fiabilite import (
    charger_analyse_liaisons_fiabilite,
)
from railinsight.config import charger_config
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.method_box import method_box
from railinsight.ui.state.base_state import PageState
from railinsight.utils.formatting import fmt_number, fmt_pct
from railinsight.viz.liaisons_fiabilite import (
    figure_classement_duree,
    figure_classement_liaisons,
    figure_comparaison_liaisons,
)


@st.cache_data(show_spinner="Calcul de la fiabilité des liaisons…")
def _analyse() -> AnalyseLiaisonsFiabilite:
    """Met les résultats Q1 en cache pendant la session Streamlit."""
    return charger_analyse_liaisons_fiabilite()


def _formater_pente(valeur: float) -> str:
    """Formate une pente annuelle en points de pourcentage."""
    if pd.isna(valeur):
        return "—"
    return f"{valeur:+.2f}".replace(".", ",") + " pt/an"


class Q1LiaisonsFiabilitePage(BasePage):
    """Répond à la question des liaisons les moins fiables du réseau TGV."""

    def __init__(self) -> None:
        super().__init__()
        self._state = PageState(page_key="q1_liaisons_fiabilite")

    @property
    def question_number(self) -> int:
        return 1

    @property
    def question_title(self) -> str:
        return "Liaisons les moins fiables"

    @property
    def author(self) -> str:
        return "Michelle"

    def _render_key_figures(self) -> None:
        analyse = _analyse()
        moins_fiable = analyse.classement.iloc[0]
        meilleure, pire, periode = st.columns(3)
        meilleure.metric("Liaisons analysées", fmt_number(len(analyse.classement)))
        pire.metric(
            "Taux le plus élevé",
            fmt_pct(moins_fiable["taux_incidents"]),
            help=(
                "Part des trains prévus qui ont été annulés ou retardés de plus "
                "de 15 min."
            ),
        )
        pire.caption(moins_fiable.name)
        periode.metric(
            "Période étudiée",
            f"{analyse.periode_debut} → {analyse.periode_fin}",
        )

    def _render_controls(self) -> None:
        config = charger_config()
        gauche, droite = st.columns(2)
        gauche.number_input(
            "Nombre de liaisons dans les classements",
            min_value=1,
            value=config.liaisons_fiabilite.top_n,
            step=1,
            key=self._state.widget_key("top_n"),
        )
        droite.selectbox(
            "Exclusion utilisée pour calculer la tendance",
            options=list(REGLES_TENDANCE),
            format_func=REGLES_TENDANCE.__getitem__,
            key=self._state.widget_key("regle_tendance"),
            help=(
                "La tendance compare plusieurs traitements des mois de grève "
                "et de confinement."
            ),
        )

    def _render_body(self) -> None:
        analyse = _analyse()
        nombre = int(
            self._state.get("top_n", charger_config().liaisons_fiabilite.top_n)
        )
        regle = self._state.get("regle_tendance", "fenetre_covid")
        classement = analyse.classement.head(nombre)
        classement_tab, evolution_tab, duree_tab = st.tabs(
            ["Classement", "Évolution et tendances", "À durée égale"]
        )
        with classement_tab:
            self._afficher_classement(classement)
        with evolution_tab:
            self._afficher_evolution(analyse, classement, regle, nombre)
        with duree_tab:
            self._afficher_duree(analyse, nombre)

    def _afficher_classement(self, classement: pd.DataFrame) -> None:
        """Affiche le classement brut et les volumes associés."""
        chart_container(
            figure_classement_liaisons(classement),
            title="Liaisons avec le taux d'incidents le plus élevé",
            how_to_read=(
                "Le taux est calculé sur l'ensemble de la période, en divisant "
                "la somme des incidents par la somme des trains prévus."
            ),
            key=self._state.widget_key("classement"),
        )
        tableau = classement.reset_index().rename(
            columns={
                "liaison": "Liaison",
                "prevus": "Trains prévus",
                "incidents": "Incidents",
                "taux_incidents": "Taux d'incidents",
                "duree_mediane": "Durée médiane (min)",
            }
        )
        tableau["Taux d'incidents"] = (tableau["Taux d'incidents"] * 100).round(2)
        st.dataframe(tableau, hide_index=True, width="stretch")

    def _afficher_evolution(
        self,
        analyse: AnalyseLiaisonsFiabilite,
        classement: pd.DataFrame,
        regle: str,
        nombre: int,
    ) -> None:
        """Compare plusieurs liaisons et les règles de tendance."""
        liaisons = classement.index.tolist()
        if not liaisons:
            st.info("Aucune liaison à afficher.")
            return
        liaisons_choisies = st.multiselect(
            "Liaisons à comparer (5 maximum)",
            options=liaisons,
            default=liaisons[: min(2, len(liaisons))],
            max_selections=5,
            key=self._state.widget_key("liaisons_evolution"),
        )
        pas_de_temps = st.segmented_control(
            "Granularité",
            options=["Mensuel", "Annuel"],
            default="Mensuel",
            key=self._state.widget_key("granularite"),
        )
        if not liaisons_choisies:
            st.info("Choisissez au moins une liaison pour afficher la comparaison.")
            return

        reseau = analyse.tendance_reseau.loc["reseau", regle]
        st.metric(
            "Tendance du réseau",
            _formater_pente(reseau),
            help="Même méthode, calculée sur le taux mensuel agrégé du réseau.",
        )
        tendances = analyse.tendances.loc[liaisons_choisies].rename(
            columns=REGLES_TENDANCE
        )
        tendances.insert(0, "Liaison", tendances.index)
        st.dataframe(
            tendances.reset_index(drop=True).round(2),
            hide_index=True,
            width="stretch",
        )
        chart_container(
            figure_comparaison_liaisons(
                analyse.mensuel,
                liaisons_choisies,
                analyse.covid_debut,
                analyse.covid_fin,
                pas_de_temps or "Mensuel",
            ),
            title=f"Évolution {pas_de_temps.lower()} des liaisons sélectionnées",
            how_to_read=(
                "Les taux annuels sont recalculés comme un ratio des sommes, "
                "pas comme une moyenne des taux mensuels. En vue mensuelle, "
                "la zone grisée repère la fenêtre COVID. La règle choisie "
                "détermine les mois exclus de la pente indiquée dans le tableau."
            ),
            key=self._state.widget_key("evolution"),
        )
        donnees = analyse.mensuel.loc[
            analyse.mensuel["liaison"].isin(liaisons_choisies)
        ].copy()
        donnees["taux_incidents"] = (donnees["taux_incidents"] * 100).round(2)
        donnees = donnees.rename(
            columns={
                "liaison": "Liaison",
                "mois": "Mois",
                "prevus": "Trains prévus",
                "incidents": "Incidents",
                "taux_incidents": "Taux d'incidents (%)",
            }
        )
        with st.expander("Données mensuelles des liaisons sélectionnées"):
            st.dataframe(donnees, hide_index=True, width="stretch")
            st.download_button(
                "Télécharger les données (CSV)",
                data=donnees.to_csv(index=False).encode("utf-8-sig"),
                file_name="railinsight_q1_liaisons.csv",
                mime="text/csv",
                key=self._state.widget_key("telecharger_donnees"),
            )

        sensibilite = analyse.tendances.loc[liaisons].rename(columns=REGLES_TENDANCE)
        sensibilite.insert(0, "Liaison", sensibilite.index)
        sensibilite = sensibilite.reset_index(drop=True).head(nombre)
        st.markdown("#### Sensibilité aux mois exceptionnels")
        st.caption("Pentes en points de pourcentage par an.")
        st.dataframe(
            sensibilite.round(2),
            hide_index=True,
            width="stretch",
        )

    def _afficher_duree(self, analyse: AnalyseLiaisonsFiabilite, nombre: int) -> None:
        """Présente le classement ajusté pour comparer des durées différentes."""
        classement = analyse.classement_duree
        avec_duree = classement.dropna(subset=["taux_ajuste"])
        if avec_duree.empty:
            st.info(
                "Les durées de trajet disponibles ne permettent pas cet ajustement."
            )
            return
        st.write(
            "Les trajets longs ont davantage de temps pour accumuler un retard. "
            "Ce classement estime le taux de chaque liaison si sa durée était "
            "égale à la durée moyenne du réseau."
        )
        correlation = analyse.correlation_duree
        if pd.notna(correlation):
            st.caption(
                f"Corrélation de Spearman entre durée et taux brut : {correlation:.2f}."
            )
        chart_container(
            figure_classement_duree(classement.head(nombre)),
            title="Liaisons les moins fiables après correction de la durée",
            how_to_read=(
                "Le taux ajusté retire l'effet linéaire de la durée du trajet "
                "sur le logarithme de la durée. Le taux brut reste visible au survol."
            ),
            key=self._state.widget_key("classement_duree"),
        )
        brutes = set(analyse.classement.head(nombre).index)
        ajustees = set(classement.head(nombre).index)
        st.metric(
            f"Liaisons communes aux deux classements (top {nombre})",
            fmt_number(len(brutes & ajustees)),
        )

    def _render_method_box(self) -> None:
        method_box(
            "**Méthode.** Un incident est un train annulé ou en retard de plus "
            "de 15 minutes à l'arrivée. Le taux est un ratio de sommes, pondéré "
            "par les trains prévus. Les lignes sans train prévu sont retirées ; "
            "les nombres de retards supérieurs aux trains circulés sont invalidés. "
            "La tendance est la pente d'une régression linéaire des taux mensuels, "
            "exprimée en points de pourcentage par an.\n\n"
            "**Limites.**\n"
            "- Le taux combine annulations et retards et ne distingue pas "
            "leurs causes.\n"
            "- Les résultats varient selon le traitement des mois de grève "
            "et de confinement.\n"
            "- La correction de durée est une comparaison statistique, pas "
            "une explication causale.\n"
            "- Les faibles volumes peuvent rendre certains taux instables."
        )


Q1LiaisonsFiabilitePage().render()
