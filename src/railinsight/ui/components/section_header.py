"""En-tête de section : petite question en couleur, puis le constat."""

import html

import streamlit as st

from railinsight.ui.theme.tokens import SNCF_RED

COULEUR_FILET = "#E5E7EB"


def section_header(
    numero: int | None, etiquette: str, titre: str, couleur: str = SNCF_RED
) -> None:
    """Affiche un filet, la question de la section en couleur, puis son constat.

    Args:
        numero: Numéro de la section, affiché sur deux chiffres, ou None pour
            une section sans numéro (page d'accueil).
        etiquette: Question courte posée par la section.
        titre: Constat qui répond à la question.
        couleur: Couleur de la question.
    """
    numero_html = (
        ""
        if numero is None
        else '<span style="opacity:0.55;font-variant-numeric:tabular-nums;'
        f'margin-right:0.75rem;">{numero:02d}</span>'
    )
    st.markdown(
        '<div style="margin-top:3rem;padding-top:1.75rem;'
        f'border-top:1px solid {COULEUR_FILET};">'
        f'<p style="margin:0;font-size:1.1rem;font-weight:600;color:{couleur};">'
        f"{numero_html}<span>{html.escape(etiquette, quote=False)}</span></p></div>",
        unsafe_allow_html=True,
    )
    st.subheader(titre, anchor=False)