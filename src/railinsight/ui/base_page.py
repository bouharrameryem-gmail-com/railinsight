"""Abstract base class for all RailInsight pages.

Design pattern: Template Method.
BasePage.render() defines the fixed narrative order (header → KPIs → controls →
body → method box → sources). Subclasses fill in only their own logic.

Why template method instead of plain functions?
  Each page needs the same error-handling shell and the same footer. Inheritance
  lets us write that shell once and guarantee every page has it, without each
  author having to remember to add it.
"""

from __future__ import annotations

import abc
import logging

import streamlit as st

from railinsight.exceptions import ErreurRailInsight, RailInsightError
from railinsight.interfaces.data_protocols import DataProvider

logger = logging.getLogger(__name__)


class BasePage(abc.ABC):
    """Abstract base for all RailInsight question pages.

    Args:
        provider: Data provider satisfying the DataProvider protocol.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider

    # --- Abstract properties (must be set by each subclass) ------------------

    @property
    @abc.abstractmethod
    def question_number(self) -> int:
        """Question number (1–4)."""

    @property
    @abc.abstractmethod
    def question_title(self) -> str:
        """Short title of the question (used as page header)."""

    @property
    @abc.abstractmethod
    def author(self) -> str:
        """Full name of the team member responsible for this page."""

    # --- Template method (fixed order, do not override) ----------------------

    def render(self) -> None:
        """Affiche les sections de la page dans l'ordre prévu.

        Les deux familles d'erreurs métier donnent un avertissement lisible.
        Les erreurs inattendues sont journalisées et affichées sans détail technique.
        """
        try:
            self._render_header()
            self._render_key_figures()
            self._render_controls()
            self._render_body()
            self._render_method_box()
            self._render_sources()
        except (ErreurRailInsight, RailInsightError) as exc:
            st.warning(str(exc))
            logger.warning(
                "Erreur métier sur la page Q%d : %s", self.question_number, exc
            )
        except Exception:
            st.error(
                "Une erreur inattendue s'est produite. "
                "L’équipe technique a été notifiée."
            )
            logger.exception(
                "Erreur inattendue sur la page Q%d (%s)",
                self.question_number,
                self.__class__.__name__,
            )

    # --- Fixed sections (override only _render_sources if really needed) -----

    def _render_header(self) -> None:
        """Render the question header with number, title and author."""
        col_title, col_author = st.columns([8, 2])
        with col_title:
            st.markdown(f"### Question {self.question_number} — {self.question_title}")
        with col_author:
            st.caption(f"Analyse : {self.author}")
        st.divider()

    def _render_sources(self) -> None:
        """Render the mandatory data-source footer."""
        st.caption("Source : SNCF Open Data — Régularité mensuelle TGV (AQST)")

    # --- Abstract sections (every subclass must implement these two) ---------

    @abc.abstractmethod
    def _render_key_figures(self) -> None:
        """Render the accroche section: 2–4 key figures as st.metric cards."""

    @abc.abstractmethod
    def _render_body(self) -> None:
        """Render the main analysis: charts, tables, narrative text."""

    # --- Optional sections (override to customise) ---------------------------

    def _render_controls(self) -> None:
        """Render filter widgets. Default: no filters. Override if needed."""
        return  # noqa: B027

    def _render_method_box(self) -> None:
        """Render the methodology and limits expander."""
        with st.expander("Méthode et limites", expanded=False):
            st.caption(
                "Note méthodologique non définie. "
                "Implémentez _render_method_box() dans votre sous-classe."
            )
