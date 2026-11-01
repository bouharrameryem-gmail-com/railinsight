"""Page Q2 : gares de départ à l'origine ou victimes des retards."""

import streamlit as st

from railinsight.backend.retards_gares import RetardsParGare, charger_retards_par_gare
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState

EXCLURE_2020_PAR_DEFAUT = True


@st.cache_data(show_spinner="Calcul des retards par gare…")
def _retards(exclure_2020: bool) -> RetardsParGare:
    """Met en cache les tables de retards selon l'exclusion de 2020."""
    return charger_retards_par_gare(exclure_2020)


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

    def _render_body(self) -> None:
        st.info("Les classements arrivent dans les prochains commits.")


Q2RetardsGaresPage(get_provider()).render()