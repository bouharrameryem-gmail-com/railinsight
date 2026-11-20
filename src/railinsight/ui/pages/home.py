"""Page d'accueil : la question, le constat, la carte, puis l'enquête en chapitres.

Ce fichier est exécuté comme un script par Streamlit (st.Page dans app.py).
"""

import html
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pandas as pd
import streamlit as st

from railinsight.analysis.geometrie import Ligne
from railinsight.analysis.indicateurs_reseau import (
    ecart_en_points,
    gares_les_plus_touchees,
    mois_le_plus_difficile,
    regrouper_gares_proches,
    un_sur,
)
from railinsight.backend.accueil import (
    DonneesAccueil,
    charger_donnees_accueil,
    charger_reseau_lgv,
)
from railinsight.exceptions import ErreurRailInsight, RailInsightError
from railinsight.ui.components.section_header import COULEUR_FILET, section_header
from railinsight.ui.theme.tokens import GRAY_700, GRAY_900, SNCF_RED
from railinsight.utils.formatting import fmt_month, fmt_number
from railinsight.viz.accueil import figure_calendrier, figure_carte_gares, nom_gare

# Streamlit exécute la page comme un script : __name__ vaudrait "__main__"
# et les messages échapperaient aux fichiers de log du logger "railinsight".
logger = logging.getLogger("railinsight.ui.pages.home")

T = TypeVar("T")

LARGEUR_TEXTE = "46rem"
# En dessous de 0,1 point d'écart sur un an, on parle de stabilité.
ECART_STABLE = 0.1
# Vert d'une baisse des retards, lisible sur fond blanc (contraste d'environ 5:1).
COULEUR_BAISSE = "#2E7D32"
LIEN_DONNEES = (
    "https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/"
)
LIEN_RESEAU = (
    "https://ressources.data.sncf.com/explore/dataset/lignes-lgv-et-par-ecartement/"
)
LIEN_DEPOT = "https://github.com/bouharrameryem-gmail-com/railinsight"


@dataclass(frozen=True)
class Chapitre:
    """Un chapitre de l'enquête, tel que le présente le sommaire."""

    numero: int
    role: str
    question: str
    resume: str
    auteur: str
    page: str


CHAPITRES = (
    Chapitre(
        1,
        "Constat",
        "Quelles liaisons sont le plus souvent en retard, et est-ce que ça empire ?",
        "Le classement des liaisons les moins fiables et leur évolution dans le temps.",
        "Michelle",
        "src/railinsight/ui/pages/q1_liaisons_fiabilite.py",
    ),
    Chapitre(
        2,
        "Causes",
        "Le retard naît-il dans la gare de départ, ou arrive-t-il d'ailleurs ?",
        "Les retards nés sur place, importés ou venus de l'extérieur, gare par gare.",
        "Éric",
        "src/railinsight/ui/pages/q2_departure_stations.py",
    ),
    Chapitre(
        3,
        "Profils",
        "Quelles familles de liaisons se dessinent selon leur régularité ?",
        "Des liaisons regroupées en profils, des plus régulières aux moins fiables.",
        "Bachelard",
        "src/railinsight/ui/pages/ponctualite_liaisons.py",
    ),
    Chapitre(
        4,
        "Verdict",
        "Quelle note de fiabilité mérite chaque liaison ?",
        "Un score qui combine annulations et retards, et sa carte du réseau.",
        "Meryem",
        "src/railinsight/ui/pages/q4_score_fiabilite.py",
    ),
)


@st.cache_data(show_spinner="Chargement des données du réseau…")
def _donnees() -> DonneesAccueil:
    """Met en cache les chiffres de l'accueil."""
    return charger_donnees_accueil()


@st.cache_data(show_spinner=False)
def _reseau() -> list[Ligne] | None:
    """Met en cache le tracé des LGV."""
    return charger_reseau_lgv()


def _html(texte: str) -> str:
    """Échappe un texte avant de l'insérer dans du HTML."""
    return html.escape(texte, quote=False)


def _typo(texte: str) -> str:
    """Espace insécable avant ? : ; ! : la ponctuation ne part pas seule à la ligne."""
    return re.sub(r" ([?:;!])", "\u00a0\\1", texte)


def _lien(adresse: str, texte: str) -> str:
    """Lien discret, souligné, dans la couleur du texte qui l'entoure."""
    return (
        f'<a href="{adresse}" target="_blank" rel="noopener noreferrer" '
        f'style="color:inherit;text-decoration:underline;">{_html(texte)}</a>'
    )


def _paragraphe(texte: str, style: str) -> None:
    """Affiche un paragraphe déjà échappé, avec le style donné."""
    st.markdown(f'<p style="{style}">{_typo(texte)}</p>', unsafe_allow_html=True)


def _evolution(courant: float, precedent: float | None) -> tuple[str, str]:
    """Décrit l'évolution d'un taux sur un an, avec sa couleur.

    Une hausse est en rouge, une baisse en vert : il s'agit de retards et
    d'annulations, donc une hausse est une mauvaise nouvelle.
    """
    if precedent is None:
        return "", GRAY_700
    ecart = ecart_en_points(courant, precedent)
    if abs(ecart) < ECART_STABLE:
        return "Stable sur un an", GRAY_700
    points = fmt_number(abs(ecart), decimals=1)
    if ecart > 0:
        return f"En hausse de {points} point sur un an", SNCF_RED
    return f"En baisse de {points} point sur un an", COULEUR_BAISSE


class PageAccueil:
    """Porte d'entrée de l'application : accroche, carte, repères et sommaire."""

    def render(self) -> None:
        """Affiche la page, bloc par bloc.

        Un bloc dont les données manquent affiche un message à sa place : le
        reste de la page, et surtout le sommaire, reste accessible.
        """
        logger.info("Page d'accueil affichée")
        donnees = self._charger(
            _donnees, "Les chiffres du réseau sont momentanément indisponibles."
        )
        self._ouverture(donnees)
        if donnees is not None:
            self._chiffres(donnees)
            self._calendrier(donnees)
        self._sommaire()
        self._fin(donnees)

    # --- Outils -----------------------------------------------------------------

    @staticmethod
    def _charger(chargeur: Callable[[], T], message: str | None = None) -> T | None:
        """Exécute un chargement ; en cas d'échec, affiche `message` s'il est donné."""
        try:
            return chargeur()
        except (ErreurRailInsight, RailInsightError) as exc:
            logger.warning("Accueil : %s", exc)
        except Exception:
            # L'accueil doit rester affiché : l'erreur part dans le log d'erreurs.
            logger.exception("Accueil : erreur inattendue")
        if message:
            st.info(message)
        return None

    # --- Blocs de la page -----------------------------------------------------

    def _ouverture(self, donnees: DonneesAccueil | None) -> None:
        """Premier écran : la question et l'action à gauche, la carte à droite.

        Sur un écran étroit, Streamlit empile les deux colonnes : le texte
        reste lu en premier, la carte suit.
        """
        if donnees is None:
            self._accroche(None)
            return
        texte, carte = st.columns([5, 7], gap="large", vertical_alignment="center")
        with texte:
            self._accroche(donnees)
        with carte:
            self._carte(donnees)

    def _accroche(self, donnees: DonneesAccueil | None) -> None:
        """La question de l'enquête, le constat qui accroche et l'action."""
        _paragraphe(
            "RailInsight · La régularité des TGV en France",
            f"margin:0 0 0.75rem;font-size:0.95rem;color:{GRAY_700};",
        )
        _paragraphe(
            "Pourquoi votre TGV arrive-t-il en retard ?",
            "margin:0;max-width:50rem;font-size:2.6rem;font-weight:700;"
            f"line-height:1.15;letter-spacing:-0.02em;color:{GRAY_900};",
        )
        if donnees is not None:
            nombre = un_sur(donnees.courant.taux_retard)
            _paragraphe(
                "Sur les 12 derniers mois, "
                f'<strong style="color:{SNCF_RED};">1 TGV sur {nombre}</strong> '
                "est arrivé avec plus d'un quart d'heure de retard.",
                f"margin:1.25rem 0 0;max-width:{LARGEUR_TEXTE};font-size:1.4rem;"
                "line-height:1.5;",
            )
        source = "Les données mensuelles de la SNCF, liaison par liaison"
        if donnees is not None:
            premier = fmt_month(pd.Period(donnees.premier_mois, freq="M"))
            source += f", depuis {premier}"
        _paragraphe(
            f"{source}.",
            f"margin:0.75rem 0 1.25rem;max-width:{LARGEUR_TEXTE};"
            f"font-size:1.05rem;color:{GRAY_700};",
        )
        if st.button("Commencer l'enquête", type="primary", key="accueil_commencer"):
            logger.info("Accueil : l'utilisateur commence l'enquête")
            st.switch_page(CHAPITRES[0].page)
        if donnees is not None:
            debut = fmt_month(pd.Period(donnees.periode.debut, freq="M"))
            fin = fmt_month(pd.Period(donnees.periode.fin, freq="M"))
            st.caption(
                f"Données SNCF jusqu'à {fin}. Les 12 derniers mois vont de "
                f"{debut} à {fin}."
            )

    def _carte(self, donnees: DonneesAccueil) -> None:
        """La carte des gares, son constat en une ligne, puis sa légende."""
        reseau = self._charger(_reseau, "Le tracé des lignes est indisponible.")
        bulles = regrouper_gares_proches(donnees.gares)
        st.plotly_chart(
            figure_carte_gares(bulles, reseau),
            width="stretch",
            config={"scrollZoom": False, "displayModeBar": False},
            key="accueil_carte",
        )
        pires = gares_les_plus_touchees(donnees.gares, 1)
        if not pires.empty:
            _paragraphe(
                f"La gare la plus touchée : {_html(nom_gare(pires.loc[0, 'gare']))}, "
                f"où 1 TGV sur {un_sur(pires.loc[0, 'taux_retard'])} arrive en "
                "retard.",
                f"margin:0.25rem 0 0.25rem;font-weight:600;color:{GRAY_900};",
            )
        legende = (
            "Chaque bulle est une gare de départ : sa taille montre le nombre de "
            "trains, sa couleur la part des TGV arrivés avec plus de 15 minutes "
            "de retard."
        )
        if bulles["membres"].map(len).gt(0).any():
            legende += (
                " Les gares très proches, comme celles de Paris, sont réunies en "
                "une bulle : survolez-la pour le détail."
            )
        if reseau:
            legende += " En fond, les lignes à grande vitesse (SNCF Réseau)."
        if donnees.gares_absentes:
            total = len(donnees.gares) + len(donnees.gares_absentes)
            legende += f" {len(donnees.gares)} gares placées sur {total}."
        st.caption(legende)

    def _chiffres(self, donnees: DonneesAccueil) -> None:
        """Affiche trois repères en très grand, avec leur évolution sur un an."""
        courant, precedent = donnees.courant, donnees.precedent
        st.markdown(
            f'<div style="margin-top:2.5rem;border-top:1px solid {COULEUR_FILET};">'
            "</div>",
            unsafe_allow_html=True,
        )
        retard, annulation, liaisons = st.columns(3)
        with retard:
            self._repere(
                f"1 sur {un_sur(courant.taux_retard)}",
                "TGV arrivés avec plus de 15 minutes de retard",
                *_evolution(
                    courant.taux_retard,
                    None if precedent is None else precedent.taux_retard,
                ),
            )
        with annulation:
            self._repere(
                f"1 sur {un_sur(courant.taux_annulation)}"
                if courant.taux_annulation > 0
                else "Aucun",
                "TGV annulés",
                *_evolution(
                    courant.taux_annulation,
                    None if precedent is None else precedent.taux_annulation,
                ),
            )
        with liaisons:
            self._repere(
                fmt_number(courant.liaisons),
                f"liaisons suivies, pour {fmt_number(courant.trains)} trains",
                "",
                GRAY_700,
            )

    @staticmethod
    def _repere(valeur: str, libelle: str, evolution: str, couleur: str) -> None:
        """Un chiffre en très grand, son libellé, puis son évolution."""
        evolution_html = (
            f'<p style="margin:0.35rem 0 0;font-size:0.95rem;font-weight:600;'
            f'color:{couleur};">{_html(evolution)}</p>'
            if evolution
            else ""
        )
        st.markdown(
            '<div style="margin-top:2.5rem;">'
            f'<p style="margin:0;font-size:3.2rem;font-weight:700;line-height:1;'
            f'letter-spacing:-0.02em;color:{GRAY_900};">{_html(valeur)}</p>'
            f'<p style="margin:0.5rem 0 0;font-size:1rem;color:{GRAY_700};">'
            f"{_html(libelle)}</p>{evolution_html}</div>",
            unsafe_allow_html=True,
        )

    def _calendrier(self, donnees: DonneesAccueil) -> None:
        """Montre tous les mois d'un coup d'œil, et nomme le pire."""
        mois, taux = mois_le_plus_difficile(donnees.par_mois)
        section_header(
            None,
            _typo("Quand les retards s'accumulent-ils ?"),
            _typo(
                f"Le mois le plus difficile : {fmt_month(mois)}, avec 1 TGV sur "
                f"{un_sur(taux)} en retard"
            ),
        )
        st.plotly_chart(
            figure_calendrier(donnees.par_mois),
            width="stretch",
            config={"displayModeBar": False},
            key="accueil_calendrier",
        )
        st.caption(
            "Chaque case est un mois : plus elle est foncée, plus les TGV ont été "
            "en retard. * En 2020, les confinements ont fortement réduit le trafic."
        )

    def _sommaire(self) -> None:
        """Présente l'enquête comme une table des matières, du constat au verdict.

        Une ligne par chapitre, séparées par un filet : toutes ont la même
        structure, donc la même hauteur, ce que des cartes à contenu variable
        ne garantissent pas.
        """
        section_header(
            None,
            _typo("Que trouve-t-on dans chaque page ?"),
            "Une question par page, à lire dans l'ordre ou séparément",
        )
        for chapitre in CHAPITRES:
            self._chapitre(chapitre)
        st.markdown(
            f'<div style="border-top:1px solid {COULEUR_FILET};"></div>',
            unsafe_allow_html=True,
        )

    def _chapitre(self, chapitre: Chapitre) -> None:
        """Une ligne du sommaire : numéro, rôle et auteur, question, résumé, lien."""
        st.markdown(
            f'<div style="border-top:1px solid {COULEUR_FILET};"></div>',
            unsafe_allow_html=True,
        )
        numero, texte, lien = st.columns(
            [1, 8, 2], gap="medium", vertical_alignment="center"
        )
        with numero:
            _paragraphe(
                f"{chapitre.numero:02d}",
                f"margin:0;font-size:2.4rem;font-weight:700;line-height:1;"
                f"font-variant-numeric:tabular-nums;color:{SNCF_RED};",
            )
        with texte:
            _paragraphe(
                f'<span style="font-weight:600;color:{SNCF_RED};">'
                f"{_html(chapitre.role)}</span>"
                f'<span style="color:{GRAY_700};"> · par {_html(chapitre.auteur)}'
                "</span>",
                "margin:0;font-size:0.9rem;",
            )
            _paragraphe(
                _html(chapitre.question),
                "margin:0.25rem 0 0;font-size:1.2rem;font-weight:700;"
                f"line-height:1.35;color:{GRAY_900};",
            )
            _paragraphe(
                _html(chapitre.resume),
                f"margin:0.25rem 0 0.75rem;line-height:1.5;color:{GRAY_700};",
            )
        with lien:
            st.page_link(
                chapitre.page,
                label="Lire le chapitre",
                icon=":material/arrow_forward:",
            )

    def _fin(self, donnees: DonneesAccueil | None) -> None:
        """Méthode, sources et équipe."""
        st.markdown('<div style="margin-top:3rem;"></div>', unsafe_allow_html=True)
        with st.expander("Méthode et sources"):
            periode = ""
            if donnees is not None:
                debut = fmt_month(pd.Period(donnees.premier_mois, freq="M"))
                fin = fmt_month(pd.Period(donnees.periode.fin, freq="M"))
                periode = f" de {debut} à {fin}"
            st.markdown(
                f"- **Données.** Régularité mensuelle des TGV par liaison{periode}, "
                f"publiée par la SNCF ([jeu AQST]({LIEN_DONNEES})). Seul le "
                "service national est retenu, et les lignes en double sont "
                "comptées une seule fois.\n"
                "- **Retard.** Un TGV est compté en retard s'il arrive avec plus "
                "de 15 minutes de retard. Le taux rapporte ces trains aux trains "
                "qui ont effectivement circulé.\n"
                "- **Carte.** Les gares sont placées selon leurs coordonnées GPS. "
                "Le tracé des lignes à grande vitesse vient de SNCF Réseau "
                f"([lignes LGV]({LIEN_RESEAU}), licence ODbL).\n"
                "- **Chapitres.** Chaque page détaille ses propres choix de calcul."
            )
        _paragraphe(
            f"Données {_lien(LIEN_DONNEES, 'SNCF Open Data')} · Réseau "
            f"{_lien(LIEN_RESEAU, 'SNCF Réseau')} · "
            f"{_lien(LIEN_DEPOT, 'Code source sur GitHub')} · "
            "Une enquête de Michelle, Éric, Bachelard et Meryem",
            f"margin:2rem 0 0;font-size:0.85rem;color:{GRAY_700};text-align:center;",
        )


PageAccueil().render()
