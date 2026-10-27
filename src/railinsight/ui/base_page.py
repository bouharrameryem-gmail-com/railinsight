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

from railinsight.exceptions import RailInsightError
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.theme.tokens import QUESTION_COLORS, SNCF_RED

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
        """Render the full page in the standard narrative order.

        Domain errors (RailInsightError subclasses) are shown as st.warning so
        the user gets a readable message. Unexpected errors are logged with full
        traceback and shown as st.error without the technical details.
        """
        try:
            self._render_header()
            self._render_key_figures()
            self._render_controls()
            self._render_body()
            self._render_method_box()
            self._render_sources()
        except RailInsightError as exc:
            st.warning(f"⚠️ {exc}")
            logger.warning("Domain error on page Q%d: %s", self.question_number, exc)
        except Exception:
            st.error(
                "Une erreur inattendue s'est produite. "
                "L’équipe technique a été notifiée."
            )
            logger.exception(
                "Unexpected error on page Q%d (%s)",
                self.question_number,
                self.__class__.__name__,
            )

    # --- Fixed sections (override only _render_sources if really needed) -----

    def _render_header(self) -> None:
        """Render the question header with SNCF-branded accent and author badge."""
        color = QUESTION_COLORS.get(self.question_number, SNCF_RED)
        st.markdown(
            '<div style="display:flex;align-items:flex-start;'
            "justify-content:space-between;"
            'border-bottom:2px solid #E8ECEF;padding-bottom:18px;margin-bottom:8px;">'
            "<div>"
            f'<div style="font-size:0.68rem;font-weight:700;color:{color};'
            "text-transform:uppercase;letter-spacing:0.1em;"
            f'margin-bottom:5px;">Question {self.question_number}</div>'
            '<h2 style="margin:0;font-size:1.45rem;font-weight:800;'
            'color:#1A1A2E;letter-spacing:-0.02em;">'
            f"{self.question_title}</h2>"
            "</div>"
            f'<div style="background:{color};color:white;font-size:0.68rem;'
            "font-weight:700;padding:5px 12px;border-radius:20px;"
            'white-space:nowrap;margin-top:2px;letter-spacing:0.03em;">'
            f"{self.author}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    def _render_sources(self) -> None:
        """Render the mandatory data-source footer."""
        st.markdown(
            '<div style="margin-top:32px;padding-top:16px;'
            'border-top:1px solid #E8ECEF;">'
            '<span style="font-size:0.72rem;color:#9BA3AE;">'
            "Source : SNCF Open Data — Régularité mensuelle TGV (AQST)"
            "</span></div>",
            unsafe_allow_html=True,
        )

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
