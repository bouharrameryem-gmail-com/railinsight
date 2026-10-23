"""Template page — starting point for each team member.

HOW TO USE:
  1. Copy this file to a new file, e.g. pages/q1_unreliable_routes.py
  2. Rename the class (e.g. Q1UnreliableRoutesPage)
  3. Set question_number, question_title, author
  4. Implement _render_key_figures() and _render_body()
  5. Optionally override _render_controls() and _render_method_box()
  6. Register the page in app.py (see the pages list there)

RULES:
  - No business logic here. Call backend functions via self._provider.
  - No direct file reads. Use self._provider methods only.
  - Prefix all widget keys with self._state.widget_key("name").
  - All visible text is in French; code stays in English.
"""

from __future__ import annotations

import streamlit as st

from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState


class TemplatePage(BasePage):
    """Minimal example page illustrating BasePage usage.

    Delete this docstring and replace with a description of your question.
    """

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        # PageState namespaces all your widget keys under "template_page__"
        self._state = PageState(page_key="template_page")

    @property
    def question_number(self) -> int:
        return 0  # replace with your question number

    @property
    def question_title(self) -> str:
        return "Page modèle (à remplacer)"

    @property
    def author(self) -> str:
        return "Votre Nom"

    def _render_key_figures(self) -> None:
        # Replace with real KPIs loaded from self._provider
        c1, c2, c3 = st.columns(3)
        c1.metric("Indicateur 1", "42")
        c2.metric("Indicateur 2", "17,3 %")
        c3.metric("Indicateur 3", "127")

    def _render_controls(self) -> None:
        # Example: a filter widget. Note the key= uses widget_key() to avoid
        # collisions with identically-named widgets on other pages.
        st.selectbox(
            "Exemple de filtre",
            options=["Option A", "Option B"],
            key=self._state.widget_key("example_filter"),
        )

    def _render_body(self) -> None:
        st.markdown(
            "**Corps de l'analyse** — remplacez cette section par vos graphiques, "
            "tableaux et textes narratifs."
        )
        st.info(
            "Utilisez les composants de `railinsight.ui.components` "
            "pour garder la mise en page cohérente avec les autres pages."
        )

    def _render_method_box(self) -> None:
        with st.expander("Méthode et limites", expanded=False):
            st.markdown(
                """
                **Méthode :** décrivez brièvement comment vous avez construit
                vos indicateurs (formule, règle d'exclusion des mois, seuil).

                **Limites :** signalez ce que vos résultats ne peuvent pas
                montrer (biais de sélection, définitions SNCF, mois exceptionnels…).
                """
            )


# Script entry point.
TemplatePage(get_provider()).render()
