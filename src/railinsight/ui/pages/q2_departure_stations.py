"""Page Q2 : gares de départ à l'origine ou victimes des retards."""

import streamlit as st

from railinsight.analysis.causes_retards import (
    DELAY_COLUMNS,
    croiser_classements,
    filtrer_gares_significatives,
    rank_stations,
)
from railinsight.viz.retards_gares import (
    COULEURS_CATEGORIES,
    LIBELLES_CATEGORIES,
    PARTS_CATEGORIES,
    figure_classement_gares,
    figure_evolution_gare,
    figure_repartition_causes,
)
from railinsight.ui.components.chart_container import chart_container
from railinsight.backend.retards_gares import RetardsParGare, charger_retards_par_gare
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.utils.formatting import fmt_number, fmt_pct

EXCLURE_2020_PAR_DEFAUT = True
NOMBRE_PAR_DEFAUT = 10
SEUIL_PAR_DEFAUT = 1000


@st.cache_data(show_spinner="Calcul des retards par gare…")
def _retards(exclure_2020: bool) -> RetardsParGare:
    """Met en cache les tables de retards selon l'exclusion de 2020."""
    return charger_retards_par_gare(exclure_2020)


def _formater_part(valeur: float, total: float) -> str:
    """Affiche une part en pourcentage, ou un tiret si le total est nul."""
    return fmt_pct(valeur / total) if total > 0 else "—"


class Q2RetardsGaresPage(BasePage):
    """Montre quelles gares concentrent les retards et lesquelles les subissent."""

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._state = PageState(page_key="q2_retards_gares")

    @property
    def question_number(self) -> int:
        return 2

    @property
    def question_title(self) -> str:
        return "Gares responsables ou victimes des retards"

    @property
    def author(self) -> str:
        return "Éric"

    def _charger(self) -> RetardsParGare:
        """Charge les tables selon l'exclusion de 2020 choisie par l'utilisateur."""
        return _retards(self._state.get("exclure_2020", EXCLURE_2020_PAR_DEFAUT))

    def _render_key_figures(self) -> None:
        st.write(
            "Quelles gares de départ concentrent le plus de retards qui leur sont "
            "propres, et lesquelles subissent surtout des retards hérités ?"
        )
        overall = self._charger().overall
        totaux = overall[DELAY_COLUMNS].sum()
        total = float(totaux.sum())
        gares, volume, propres, herites = st.columns(4)
        gares.metric("Gares de départ", fmt_number(len(overall)))
        volume.metric(
            "Retards estimés",
            fmt_number(total),
            help="Trains arrivés en retard, toutes causes confondues.",
        )
        propres.metric(
            "Propres à la gare",
            _formater_part(totaux["retard_non_heritees"], total),
            help="Infrastructure, gestion du trafic et matériel roulant.",
        )
        herites.metric(
            "Hérités",
            _formater_part(totaux["retard_heritees"], total),
            help="Gestion en gare, réutilisation du matériel et voyageurs.",
        )

    def _render_controls(self) -> None:
        exclure, nombre, seuil = st.columns(3)
        exclure.toggle(
            "Exclure 2020",
            value=EXCLURE_2020_PAR_DEFAUT,
            key=self._state.widget_key("exclure_2020"),
            help="Les confinements ont réduit le trafic et faussent les volumes.",
        )
        nombre.select_slider(
            "Gares par classement",
            options=[5, 10, 15],
            value=NOMBRE_PAR_DEFAUT,
            key=self._state.widget_key("nombre_gares"),
        )
        seuil.slider(
            "Retards minimum par gare",
            min_value=0,
            max_value=10000,
            value=SEUIL_PAR_DEFAUT,
            step=100,
            key=self._state.widget_key("seuil_retards"),
            help=(
                "Pour les classements en parts : écarte les gares qui ont très "
                "peu de retards, dont la part n'est pas significative."
            ),
        )

    def _render_body(self) -> None:
        retards = self._charger()
        classements, causes, evolution = st.tabs(
            ["Classements", "Causes et croisement", "Évolution"]
        )
        with classements:
            self._afficher_classements(retards)
        with causes:
            self._afficher_causes(retards)
        with evolution:
            self._afficher_evolution(retards)

    def _afficher_classements(self, retards: RetardsParGare) -> None:
        """Classe les gares par retards propres et par retards hérités."""
        mode = st.radio(
            "Afficher",
            options=["Volumes", "Parts"],
            horizontal=True,
            key=self._state.widget_key("mode_classement"),
            help=(
                "Volumes : nombre de trains en retard. Parts : proportion des "
                "retards de la gare, parmi les gares au-dessus du seuil minimal."
            ),
        )
        en_part = mode == "Parts"
        table = retards.overall
        if en_part:
            seuil = self._state.get("seuil_retards", SEUIL_PAR_DEFAUT)
            table = filtrer_gares_significatives(table, seuil)
            st.caption(
                f"Seules les gares avec au moins {fmt_number(seuil)} retards "
                "sont classées."
            )
        if table.empty:
            st.info("Aucune gare n'atteint ce seuil. Baissez le seuil minimal.")
            return

        nombre = self._state.get("nombre_gares", NOMBRE_PAR_DEFAUT)
        gauche, droite = st.columns(2)
        for zone, volume, titre in (
            (gauche, "retard_non_heritees", "Gares à l'origine de leurs retards"),
            (droite, "retard_heritees", "Gares qui subissent des retards"),
        ):
            colonne = PARTS_CATEGORIES[volume] if en_part else volume
            classement = rank_stations(table, colonne, nombre)
            with zone:
                chart_container(
                    figure_classement_gares(
                        classement, colonne, COULEURS_CATEGORIES[volume], en_part
                    ),
                    title=titre,
                    key=self._state.widget_key(f"classement_{colonne}"),
                )
        st.caption(
            "Retards propres : infrastructure, trafic, matériel roulant. "
            "Retards hérités : gestion en gare, réutilisation du matériel, voyageurs."
        )
        
    def _afficher_causes(self, retards: RetardsParGare) -> None:
        """Répartit les retards des principales gares et croise les classements."""
        nombre = self._state.get("nombre_gares", NOMBRE_PAR_DEFAUT)
        table = retards.overall
        total = table[DELAY_COLUMNS].sum(axis=1)
        principales = table.loc[total.nlargest(nombre).index]
        chart_container(
            figure_repartition_causes(principales),
            title=f"Origine des retards des {nombre} gares les plus touchées",
            how_to_read=(
                "Chaque barre représente 100 % des retards d'une gare. Les gares "
                "sont triées par nombre total de retards, la plus touchée en haut."
            ),
            key=self._state.widget_key("repartition_causes"),
        )

        st.markdown("#### Gares présentes dans les deux classements")
        croisees = croiser_classements(
            table, "retard_non_heritees", "retard_heritees", nombre
        )
        if croisees.empty:
            st.info(
                "Aucune gare n'est à la fois parmi les plus responsables et "
                "parmi les plus touchées par des retards hérités."
            )
            return
        st.caption(
            "Ces gares cumulent beaucoup de retards propres et beaucoup de "
            "retards hérités : on ne peut pas les classer d'un seul côté."
        )
        affichage = croisees.rename(
            columns={
                "gare_depart": "Gare",
                "retard_non_heritees": LIBELLES_CATEGORIES["retard_non_heritees"],
                "retard_heritees": LIBELLES_CATEGORIES["retard_heritees"],
                "rang_retard_non_heritees": "Rang (propres)",
                "rang_retard_heritees": "Rang (hérités)",
            }
        ).round(0)
        affichage[["Rang (propres)", "Rang (hérités)"]] = affichage[
            ["Rang (propres)", "Rang (hérités)"]
        ].astype(int)
        st.dataframe(affichage, hide_index=True, width="stretch")


    def _afficher_evolution(self, retards: RetardsParGare) -> None:
        """Suit les retards d'une gare dans le temps."""
        overall = retards.overall
        gares = sorted(overall["gare_depart"])
        total = overall[DELAY_COLUMNS].sum(axis=1)
        plus_touchee = overall.loc[total.idxmax(), "gare_depart"]

        gauche, droite = st.columns(2)
        gare = gauche.selectbox(
            "Gare de départ",
            options=gares,
            index=gares.index(plus_touchee),
            key=self._state.widget_key("gare_evolution"),
        )
        niveau = droite.radio(
            "Période",
            options=["Par année", "Par mois"],
            horizontal=True,
            key=self._state.widget_key("niveau_evolution"),
        )
        par_annee = niveau == "Par année"
        table = retards.by_year if par_annee else retards.by_month
        axe = "annee" if par_annee else "date"
        chart_container(
            figure_evolution_gare(table[table["gare_depart"] == gare], axe),
            title=f"Retards estimés au départ de {gare}",
            how_to_read=(
                "Chaque courbe suit une catégorie de retards au fil du temps. "
                "Une année ou un mois sans retard n'apparaît pas."
            ),
            key=self._state.widget_key("evolution_gare"),
        )


Q2RetardsGaresPage(get_provider()).render()
