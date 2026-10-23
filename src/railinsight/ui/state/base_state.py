"""Base session-state wrapper for per-page state.

Streamlit stores all state in st.session_state, a dict shared across the whole
app. Without a naming convention, two pages using a widget named "period" would
collide and see each other's state.

This class solves it by prefixing every key with the page name:
  home__period, q3_lab__period  — never collide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class PageState:
    """Thin wrapper around st.session_state scoped to one page.

    Args:
        page_key: Short unique identifier for the page (e.g., "q3_lab").
            Used as a prefix for all widget keys on that page.
    """

    page_key: str

    def widget_key(self, name: str) -> str:
        """Return the namespaced widget key for use in st.* widget calls.

        Args:
            name: Logical name of the widget (e.g., "period", "n_clusters").

        Returns:
            A string like "q3_lab__period" safe to pass to key= in Streamlit.
        """
        return f"{self.page_key}__{name}"

    def get(self, attr: str, default: Any = None) -> Any:
        """Read a value stored in session state under this page's namespace.

        Args:
            attr: Attribute name (without prefix).
            default: Value to return if the key is absent.
        """
        return st.session_state.get(self.widget_key(attr), default)

    def set(self, attr: str, value: Any) -> None:
        """Write a value to session state under this page's namespace.

        Args:
            attr: Attribute name (without prefix).
            value: Value to store.
        """
        st.session_state[self.widget_key(attr)] = value
