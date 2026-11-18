"""En-tête de section numérotée.

Usage:
    section_header(1, "La grille de lecture", "Un retard peut naître sur place")
"""

import html

import streamlit as st

from railinsight.ui.theme.tokens import SNCF_RED


def section_header(
    numero: int, etiquette: str, titre: str, couleur: str = SNCF_RED
) -> None:
    """Affiche une étiquette numérotée en petites capitales, puis le titre.

    L'étiquette situe la section dans le récit ; le titre énonce son constat.

    Args:
        numero: Numéro de la section dans la page.
        etiquette: Nom court de la section, par exemple « À trafic égal ».
        titre: Phrase qui énonce ce que montre la section.
        couleur: Couleur de l'étiquette, en général celle de la question.
    """
    st.markdown(
        f'<div style="margin:40px 0 2px;font-size:0.72rem;font-weight:700;'
        f'color:{couleur};text-transform:uppercase;letter-spacing:0.1em;">'
        f"{numero} · {html.escape(etiquette)}</div>",
        unsafe_allow_html=True,
    )
    st.subheader(titre, anchor=False)