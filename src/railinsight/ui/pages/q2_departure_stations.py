"""Page Q2 : gares de départ à l'origine ou victimes des retards."""

import streamlit as st

from railinsight.backend.retards_gares import RetardsParGare, charger_retards_par_gare
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.analysis.causes_retards import  DELAY_COLUMNS
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
        st.info("Les classements arrivent dans les prochains commits.")


Q2RetardsGaresPage(get_provider()).render()