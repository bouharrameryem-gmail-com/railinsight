"""Page Q1 : liaisons les moins fiables et évolution de leur taux d'incidents."""

import pandas as pd
import streamlit as st

from railinsight.analysis.liaisons_fiabilite import (
    REGLES_TENDANCE,
    AnalyseLiaisonsFiabilite,
)
from railinsight.analysis.prevision_fiabilite import (
    MODELES,
    PrevisionFiabilite,
    prevoir_fiabilite,
)
from railinsight.backend.liaisons_fiabilite import (
    charger_analyse_liaisons_fiabilite,
)
from railinsight.config import charger_config
from railinsight.exceptions import InsufficientDataError
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
from railinsight.viz.prevision_fiabilite import figure_prevision_fiabilite


@st.cache_data(show_spinner="Calcul de la fiabilité des liaisons…")
def _analyse() -> AnalyseLiaisonsFiabilite:
    """Met les résultats Q1 en cache pendant la session Streamlit."""
    return charger_analyse_liaisons_fiabilite()


@st.cache_data(show_spinner="Évaluation de la prévision…", max_entries=32)
def _prevision(mensuel: pd.DataFrame, liaison: str) -> PrevisionFiabilite:
    """Réutilise une prévision déjà calculée pour une liaison et ses données."""
    return prevoir_fiabilite(mensuel, liaison)


def _formater_pente(valeur: float) -> str:
    """Formate une pente annuelle en points de pourcentage."""
    if pd.isna(valeur):
        return "—"
    return f"{valeur:+.2f}".replace(".", ",") + " pt/an"


class Q1LiaisonsFiabilitePage(BasePage):
    """Répond à la question des liaisons les moins fiables du réseau TGV."""

    def __init__(self) -> None:
        """Initialise l'état des contrôles de la page Q1."""
        super().__init__()
        self._state = PageState(page_key="q1_liaisons_fiabilite")

    @property
    def question_number(self) -> int:
        """Renvoie le numéro de la question."""
        return 1

    @property
    def question_title(self) -> str:
        """Renvoie le titre affiché pour Q1."""
        return "Liaisons les moins fiables"

    @property
    def author(self) -> str:
        """Renvoie le nom de la responsable de Q1."""
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
        analyse = _analyse()
        st.markdown("### Explorer une liaison")
        st.selectbox(
            "Votre liaison",
            options=sorted(analyse.classement.index),
            key=self._state.widget_key("liaison_principale"),
            on_change=self._reinitialiser_comparaison,
            help="Cette sélection accompagne votre exploration et votre prévision.",
        )

    def _reinitialiser_comparaison(self) -> None:
        """Replace la nouvelle liaison au centre de la comparaison."""
        st.session_state.pop(self._state.widget_key("liaisons_evolution"), None)

    def _render_body(self) -> None:
        analyse = _analyse()
        liaison = self._state.get("liaison_principale")
        observation = analyse.classement.loc[liaison]
        with st.container(border=True):
            st.caption(f"Votre liaison : {liaison} · ensemble de la période étudiée")
            fiabilite, volume = st.columns(2)
            fiabilite.metric(
                "Fiabilité observée",
                fmt_pct(1 - observation["taux_incidents"]),
                help="Part des trains prévus ni annulés ni retardés de plus de 15 min.",
            )
            volume.metric("Trains prévus observés", fmt_number(observation["prevus"]))
        classement_tab, evolution_tab, duree_tab, prevision_tab = st.tabs(
            [
                "Classement",
                "Évolution et tendances",
                "À durée égale",
                "Prévision à 3 mois",
            ],
            key=self._state.widget_key("onglet"),
            on_change="rerun",
        )
        if classement_tab.open:
            with classement_tab:
                nombre = self._nombre_liaisons(analyse)
                self._afficher_classement(analyse.classement.head(nombre))
        if evolution_tab.open:
            with evolution_tab:
                regle = st.selectbox(
                    "Mois exclus du calcul de tendance",
                    options=list(REGLES_TENDANCE),
                    format_func=REGLES_TENDANCE.__getitem__,
                    key=self._state.widget_key("regle_tendance"),
                    help="Ce choix ne filtre ni les observations ni les prévisions.",
                )
                self._afficher_evolution(
                    analyse, analyse.classement, regle, len(analyse.classement)
                )
        if duree_tab.open:
            with duree_tab:
                self._afficher_duree(analyse, self._nombre_liaisons(analyse))
        if prevision_tab.open:
            with prevision_tab:
                self._afficher_prevision(analyse, liaison)

    def _nombre_liaisons(self, analyse: AnalyseLiaisonsFiabilite) -> int:
        """Limite le contrôle de classement aux liaisons disponibles."""
        return int(
            st.number_input(
                "Nombre de liaisons dans les classements",
                min_value=1,
                max_value=len(analyse.classement),
                value=min(
                    charger_config().liaisons_fiabilite.top_n, len(analyse.classement)
                ),
                step=1,
                key=self._state.widget_key("top_n"),
            )
        )

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
            default=[self._state.get("liaison_principale")],
            max_selections=5,
            key=self._state.widget_key("liaisons_evolution"),
        )
        periode = st.segmented_control(
            "Historique affiché",
            options=["12 mois", "24 mois", "Tout"],
            default="24 mois",
            selection_mode="single",
            required=True,
            key=self._state.widget_key("periode_evolution"),
        )
        pas_de_temps = st.segmented_control(
            "Granularité",
            options=["Mensuel", "Annuel"],
            default="Mensuel",
            required=True,
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
        donnees_graphique = analyse.mensuel
        if periode != "Tout":
            mois = 12 if periode == "12 mois" else 24
            debut = donnees_graphique["mois"].max() - pd.DateOffset(months=mois - 1)
            donnees_graphique = donnees_graphique.loc[
                donnees_graphique["mois"].ge(debut)
            ]
        absentes = set(liaisons_choisies) - set(donnees_graphique["liaison"])
        if absentes:
            st.info(
                "Aucune observation dans la fenêtre affichée pour : "
                + ", ".join(sorted(absentes))
                + ". Essayez « Tout » pour retrouver l'historique disponible."
            )
        figure = figure_comparaison_liaisons(
            donnees_graphique,
            liaisons_choisies,
            analyse.covid_debut,
            analyse.covid_fin,
            pas_de_temps or "Mensuel",
        )
        if periode != "Tout":
            debut_affichage = donnees_graphique["mois"].min()
            if pas_de_temps == "Annuel":
                debut_affichage = debut_affichage.replace(month=1)
            figure.update_xaxes(
                range=[
                    debut_affichage,
                    donnees_graphique["mois"].max() + pd.DateOffset(months=1),
                ]
            )
        chart_container(
            figure,
            title=(
                f"Évolution {'annuelle' if pas_de_temps == 'Annuel' else 'mensuelle'}"
                " des liaisons sélectionnées"
            ),
            how_to_read=(
                "Les taux annuels sont recalculés comme un ratio des sommes, "
                "pas comme une moyenne des taux mensuels. En vue mensuelle, "
                "la zone grisée repère la fenêtre COVID. La règle choisie "
                "détermine les mois exclus de la pente indiquée dans le tableau."
                " La fenêtre affichée ne modifie pas les pentes calculées sur "
                "l'ensemble de la période ; une année peut être partielle."
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
        with st.expander("Comparer les tendances et les mois exceptionnels"):
            st.caption(
                "Pentes en points de pourcentage par an, sur toute la période. "
                "Une pente positive indique davantage d'incidents."
            )
            st.dataframe(
                tendances.reset_index(drop=True).round(2),
                hide_index=True,
                width="stretch",
            )
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
            "- Les faibles volumes peuvent rendre certains taux instables.\n"
            "- La prévision mensuelle est évaluée chronologiquement, sans "
            "garantie sur un train ou un jour. Elle ne prédit pas les grèves."
        )

    def _afficher_prevision(
        self, analyse: AnalyseLiaisonsFiabilite, liaison: str
    ) -> None:
        """Présente prévisions, référence et test indépendant pour une liaison."""
        st.markdown("### Prévisions mensuelles de fiabilité")
        st.caption(
            "Fiabilité = part des trains prévus ni annulés ni retardés de plus "
            "de 15 minutes. Prévision mensuelle, pas journalière."
        )
        try:
            resultat = _prevision(analyse.mensuel, liaison)
        except InsufficientDataError as exc:
            st.info(str(exc))
            st.caption("Choisissez une autre liaison en haut de la page.")
            return
        st.caption(
            f"Dernier mois observé : {analyse.periode_fin}. Les trois mois prévus "
            "suivent cette date, pas la date du jour. "
        )
        cartes = st.columns(3)
        for carte, ligne in zip(
            cartes, resultat.previsions.itertuples(index=False), strict=True
        ):
            carte.metric(
                pd.Timestamp(ligne.mois).strftime("%m/%Y"),
                fmt_pct(ligne.fiabilite),
                delta=f"{(ligne.fiabilite - ligne.reference) * 100:+.1f} pt",
                delta_color="off",
                border=True,
                help="Écart à la référence : même mois de l'année précédente.",
            )
        st.caption(
            "Écarts par rapport au même mois de l'année précédente, "
            "pas des intervalles de confiance."
        )
        st.warning(
            "Prévision exploratoire : les grèves, la météo et les ruptures "
            "de service ne sont pas anticipées. Aucun intervalle de prédiction "
            "calibré n'est disponible ; ces valeurs ne sont pas des garanties."
        )
        if resultat.mae_test > resultat.mae_reference:
            st.warning(
                "Sur les trois mois de test, le modèle retenu fait moins bien "
                "que la référence saisonnière. Interprétez la prévision "
                "avec une prudence accrue."
            )
        periode = st.segmented_control(
            "Historique de la prévision",
            options=["12 mois", "24 mois", "Tout"],
            default="24 mois",
            required=True,
            key=self._state.widget_key("periode_prevision"),
        )
        afficher_reference = st.toggle(
            "Afficher la référence saisonnière",
            value=True,
            key=self._state.widget_key("reference_prevision"),
        )
        figure = figure_prevision_fiabilite(resultat)
        longueur = {"12 mois": 12, "24 mois": 24, "Tout": 48}[periode]
        historique = resultat.historique.tail(longueur)
        figure.data[0].x = historique["mois"]
        figure.data[0].y = historique["fiabilite"] * 100
        figure.data[2].visible = afficher_reference
        chart_container(
            figure,
            title=f"Fiabilité mensuelle prévue — {liaison}",
            how_to_read=(
                "Trait plein : observations ; pointillés : prévisions. "
                "La référence reprend le même mois de l'année précédente."
            ),
            key=self._state.widget_key("graphique_prevision"),
        )
        tableau = resultat.previsions.copy()
        tableau["mois"] = tableau["mois"].dt.strftime("%Y-%m")
        tableau[["fiabilite", "reference"]] *= 100
        tableau = tableau.rename(
            columns={
                "mois": "Mois",
                "fiabilite": "Fiabilité prévue (%)",
                "reference": "Référence saisonnière (%)",
            }
        ).round(2)
        st.download_button(
            "Télécharger la prévision (CSV)",
            data=tableau.assign(Liaison=liaison)
            .to_csv(index=False)
            .encode("utf-8-sig"),
            file_name="railinsight_q1_prevision.csv",
            mime="text/csv",
            key=self._state.widget_key("telecharger_prevision"),
        )
        st.markdown("#### Quelle précision sur les mois déjà connus ?")
        st.write(
            f"Sur les trois mois de test, l'écart moyen entre prévision et "
            f"réalité est de **{resultat.mae_test:.2f} points**, contre "
            f"**{resultat.mae_reference:.2f} points** pour la référence. "
            "Ce test court ne garantit pas la précision future."
        )
        with st.expander("Voir les valeurs et le test historique"):
            st.dataframe(tableau, hide_index=True, width="stretch")
            test = resultat.test.copy()
            test["mois"] = test["mois"].dt.strftime("%Y-%m")
            test[["fiabilite", "prevision", "reference"]] *= 100
            st.dataframe(
                test.rename(
                    columns={
                        "mois": "Mois de test",
                        "fiabilite": "Fiabilité observée (%)",
                        "prevision": "Fiabilité prévue (%)",
                        "reference": "Référence (%)",
                    }
                ).round(2),
                hide_index=True,
                width="stretch",
            )
        with st.expander("Comprendre la méthode de prévision"):
            self._afficher_methode_prevision(resultat)

    def _afficher_methode_prevision(self, resultat: PrevisionFiabilite) -> None:
        """Garde la méthode et les scores disponibles sans alourdir la lecture."""
        st.caption(f"Modèle retenu : {MODELES[resultat.modele]}.")
        st.caption(
            "48 mois récents consécutifs requis, sans imputation. Choix du modèle "
            "sur 12 mois en quatre blocs de 3 mois, puis test indépendant sur "
            "les 3 derniers mois. Ridge utilise au plus 36 mois, avec tendance "
            "et saisonnalité, pondérés par les trains prévus. La MAE mesure "
            "l'écart absolu moyen en points, sans pondération des mois. "
            "Les prévisions Ridge sont bornées entre 0 et 100 %. Tous les mois "
            "exceptionnels restent inclus ; le filtre de tendance ne s'applique "
            "pas ici. Le modèle est réentraîné après le test."
        )
        scores = resultat.scores_validation.rename(index=MODELES).rename(
            columns={"mae_points": "MAE de validation (points)"}
        )
        st.dataframe(scores.round(2), width="stretch")


Q1LiaisonsFiabilitePage().render()
