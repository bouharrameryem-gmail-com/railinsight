"""Page Q2 : gares de départ qui fabriquent ou encaissent les retards."""

import html
import logging
import re

import pandas as pd
import streamlit as st

from railinsight.analysis.causes_retards import (
    DELAY_COLUMNS,
    ResumeRetardsGares,
    ajouter_parts_retard,
    annees_completes,
    croiser_classements,
    dresser_portrait_gare,
    evolution_part,
    filtrer_gares_significatives,
    parts_reseau,
    rank_stations,
    resumer_retards_gares,
)
from railinsight.analysis.recit_gares import (
    rediger_portrait,
    texte_constat,
    titre_carrefours,
    titre_constat,
    titre_evolution_reseau,
    titre_trafic_egal,
)
from railinsight.backend.retards_gares import RetardsParGare, charger_retards_par_gare
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.method_box import method_box
from railinsight.ui.components.section_header import section_header
from railinsight.ui.state.base_state import PageState
from railinsight.ui.theme.tokens import GRAY_700, QUESTION_COLORS
from railinsight.utils.formatting import fmt_month, fmt_number, fmt_pct
from railinsight.viz.retards_gares import (
    COULEURS_CATEGORIES,
    LIBELLES_CATEGORIES,
    PARTS_CATEGORIES,
    figure_aire_parts,
    figure_classement_gares,
    figure_evolution_gare,
    figure_repartition_causes,
)

# Streamlit exécute la page comme un script : __name__ vaudrait "__main__"
# et les messages échapperaient aux fichiers de log du logger "railinsight".
logger = logging.getLogger("railinsight.ui.pages.q2_departure_stations")

COULEUR_Q2 = QUESTION_COLORS[2]
EXCLURE_2020_PAR_DEFAUT = True
NOMBRE_PAR_DEFAUT = 10
SEUIL_PAR_DEFAUT = 1000
SEUIL_MAXIMUM = 10000
ENSEMBLE = "Ensemble des gares"

# Au-delà d'environ 75 caractères par ligne, la lecture se fatigue.
LARGEUR_TEXTE = "46rem"
POURCENTAGE = re.compile(r"\d+(?:[,.]\d+)?\s?%")

ORDRE_CATEGORIES = ["retard_non_heritees", "retard_heritees", "retard_externes"]
FAMILLES = {
    "retard_non_heritees": "Nés sur place",
    "retard_heritees": "Importés",
    "retard_externes": "Venus de l'extérieur",
}
DEFINITIONS = {
    "retard_non_heritees": (
        "Infrastructure (voies, signalisation, travaux), gestion du trafic, "
        "matériel roulant : le retard naît sur la liaison."
    ),
    "retard_heritees": (
        "Rame réutilisée déjà en retard, gestion en gare, affluence et "
        "correspondances : le retard arrive d'ailleurs."
    ),
    "retard_externes": (
        "Météo, obstacles sur la voie, colis suspects, malveillance : ni la "
        "gare ni l'exploitation n'en sont la cause."
    ),
}


@st.cache_data(show_spinner="Calcul des retards par gare…")
def _retards(exclure_2020: bool) -> RetardsParGare:
    """Met en cache les tables de retards selon l'exclusion de 2020."""
    return charger_retards_par_gare(exclure_2020)


def _texte_html(texte: str) -> str:
    """Échappe un texte avant de l'insérer dans du HTML."""
    return html.escape(texte, quote=False)


def _fiche(titre: str, texte: str, couleur: str) -> None:
    """Affiche le nom d'une famille de causes dans sa couleur, puis sa définition."""
    st.markdown(
        f'<p style="margin:0;font-size:1.15rem;font-weight:700;color:{couleur};">'
        f"{_texte_html(titre)}</p>"
        f'<p style="margin:0.35rem 0 0;color:{GRAY_700};line-height:1.55;">'
        f"{_texte_html(texte)}</p>",
        unsafe_allow_html=True,
    )


def _contexte(texte: str) -> None:
    """Affiche un texte d'explication, en retrait visuel derrière les constats."""
    st.markdown(
        f'<p style="margin:0 0 1rem;max-width:{LARGEUR_TEXTE};color:{GRAY_700};'
        f'line-height:1.6;">{_texte_html(texte)}</p>',
        unsafe_allow_html=True,
    )


def _phrase_cle(texte: str, taille: str = "1.2rem") -> None:
    """Affiche une phrase importante en grand, avec ses pourcentages en gras."""
    contenu = POURCENTAGE.sub(
        lambda trouve: f"<strong>{trouve.group()}</strong>", _texte_html(texte)
    )
    st.markdown(
        f'<p style="margin:0;max-width:{LARGEUR_TEXTE};font-size:{taille};'
        f'line-height:1.6;">{contenu}</p>',
        unsafe_allow_html=True,
    )


class Q2RetardsGaresPage(BasePage):
    """Montre d'où viennent les retards et quelles gares les subissent."""

    def __init__(self) -> None:
        """Initialise l'état propre à la page."""
        super().__init__()
        self._state = PageState(page_key="q2_retards_gares")

    @property
    def question_number(self) -> int:
        """Renvoie le numéro de la question."""
        return 2

    @property
    def question_title(self) -> str:
        """Renvoie le titre de la question."""
        return "Gares responsables ou victimes des retards"

    @property
    def author(self) -> str:
        """Renvoie le nom de l'auteur."""
        return "Éric"

    # --- Réglages et données --------------------------------------------------

    def _exclut_2020(self) -> bool:
        """Indique si l'utilisateur a exclu l'année 2020."""
        return bool(self._state.get("exclure_2020", EXCLURE_2020_PAR_DEFAUT))

    def _seuil(self) -> int:
        """Renvoie le nombre minimal de retards choisi par l'utilisateur."""
        return int(self._state.get("seuil_retards", SEUIL_PAR_DEFAUT))

    def _charger(self) -> RetardsParGare:
        """Charge les tables selon l'exclusion de 2020."""
        return _retards(self._exclut_2020())

    def _resumer(self, retards: RetardsParGare) -> ResumeRetardsGares:
        """Calcule les chiffres clés avec le seuil choisi."""
        return resumer_retards_gares(retards.overall, self._seuil())

    def _periode(self, retards: RetardsParGare) -> str:
        """Décrit la période couverte, en signalant l'exclusion de 2020."""
        dates = retards.by_month["date"]
        texte = (
            f"de {fmt_month(pd.Period(dates.min(), freq='M'))} "
            f"à {fmt_month(pd.Period(dates.max(), freq='M'))}"
        )
        if self._exclut_2020():
            texte += ", hors 2020"
        return texte

    def _journaliser(self, nom: str) -> None:
        """Enregistre dans les logs un réglage modifié par l'utilisateur."""
        logger.info("Q2 - réglage %s = %r", nom, self._state.get(nom))

    # --- Sections imposées par BasePage ---------------------------------------

    def _render_key_figures(self) -> None:
        """Pose la question en grand, puis les chiffres clés."""
        retards = self._charger()
        resume = self._resumer(retards)
        st.markdown(
            '<p style="margin:0.25rem 0 1.75rem;max-width:44rem;font-size:2rem;'
            'font-weight:600;line-height:1.3;letter-spacing:-0.01em;">'
            "Quand votre TGV arrive en retard, le problème est-il né dans sa "
            "gare de départ, ou l'a-t-il apporté d'ailleurs ?</p>",
            unsafe_allow_html=True,
        )
        gares, propres, importes, externes = st.columns(4)
        gares.metric("Gares de départ", fmt_number(resume.nombre_gares), border=True)
        propres.metric(
            "Retards nés sur place", fmt_pct(resume.part_propres), border=True
        )
        importes.metric("Retards importés", fmt_pct(resume.part_heritees), border=True)
        externes.metric(
            "Venus de l'extérieur", fmt_pct(resume.part_externes), border=True
        )
        st.caption(
            f"{fmt_number(resume.total_retards)} trains arrivés en retard. "
            f"Service national, {self._periode(retards)}. Source : SNCF Open Data."
        )

    def _render_controls(self) -> None:
        """Réglages qui s'appliquent à toute la page."""
        exclure, nombre, _ = st.columns([1, 1, 2], vertical_alignment="bottom")
        exclure.toggle(
            "Exclure 2020",
            value=EXCLURE_2020_PAR_DEFAUT,
            key=self._state.widget_key("exclure_2020"),
            on_change=self._journaliser,
            args=("exclure_2020",),
            help="Les confinements ont réduit le trafic et faussent les volumes.",
        )
        nombre.select_slider(
            "Gares par classement",
            options=[5, 10, 15],
            value=NOMBRE_PAR_DEFAUT,
            key=self._state.widget_key("nombre_gares"),
            on_change=self._journaliser,
            args=("nombre_gares",),
        )

    def _render_body(self) -> None:
        """Déroule l'enquête en cinq sections."""
        retards = self._charger()
        resume = self._resumer(retards)
        nombre = int(self._state.get("nombre_gares", NOMBRE_PAR_DEFAUT))
        self._section_grille(retards)
        self._section_constat(retards.overall, resume, nombre)
        self._section_trafic_egal(retards.overall, resume, nombre)
        self._section_carrefours(retards.overall, nombre)
        self._section_votre_gare(retards)
        st.caption(
            "Et les liaisons ? La question 3 les regroupe selon leur profil de "
            "ponctualité, la question 4 leur donne une note sur 100."
        )

    # --- Les cinq sections de l'enquête ---------------------------------------

    def _section_grille(self, retards: RetardsParGare) -> None:
        """Pose les trois familles de causes et leur évolution."""
        section_header(
            1,
            "D'où vient un retard ?",
            "Un retard peut naître sur place, être importé, ou venir de l'extérieur",
            COULEUR_Q2,
        )
        _contexte(
            "La SNCF attribue chaque retard à une cause. On regroupe ces causes "
            "en trois familles pour savoir si une gare produit ses retards ou "
            "les subit."
        )
        colonnes = st.columns(3, border=True)
        for zone, categorie in zip(colonnes, ORDRE_CATEGORIES, strict=True):
            with zone:
                _fiche(
                    FAMILLES[categorie],
                    DEFINITIONS[categorie],
                    COULEURS_CATEGORIES[categorie],
                )
        reseau = parts_reseau(retards.by_year, "annee")
        evolution = evolution_part(
            reseau, "taux_heritees", annees_completes(retards.by_month)
        )
        chart_container(
            figure_aire_parts(reseau, evolution),
            title=titre_evolution_reseau(evolution),
            caption=(
                "Chaque année totalise 100 % des retards de toutes les gares. La "
                "bande bleue du bas montre la part des retards importés ; les "
                "valeurs écrites sont celles de la première et de la dernière "
                "année complète."
            ),
            key=self._state.widget_key("aire_parts"),
        )

    def _section_constat(
        self, overall: pd.DataFrame, resume: ResumeRetardsGares, nombre: int
    ) -> None:
        """Nomme les gares qui fabriquent et encaissent le plus, en volume."""
        section_header(
            2, "Qui fabrique, qui encaisse ?", titre_constat(resume), COULEUR_Q2
        )
        with st.container(border=True):
            _phrase_cle(texte_constat(resume))
        gauche, droite = st.columns(2)
        for zone, colonne, titre in (
            (gauche, "retard_non_heritees", "Les gares qui fabriquent du retard"),
            (droite, "retard_heritees", "Les gares qui encaissent des retards"),
        ):
            with zone:
                chart_container(
                    figure_classement_gares(
                        rank_stations(overall, colonne, nombre),
                        colonne,
                        COULEURS_CATEGORIES[colonne],
                    ),
                    title=titre,
                    key=self._state.widget_key(f"classement_{colonne}"),
                )

    def _section_trafic_egal(
        self, overall: pd.DataFrame, resume: ResumeRetardsGares, nombre: int
    ) -> None:
        """Compare les gares à trafic égal, en parts de leurs propres retards."""
        section_header(3, "Et à trafic égal ?", titre_trafic_egal(resume), COULEUR_Q2)
        _contexte(
            "Une gare qui compte 30 retards ne se compare pas à une gare qui en "
            "compte 30 000 : seules les gares au-dessus du seuil sont classées."
        )
        zone_seuil, zone_compte = st.columns([2, 3], vertical_alignment="bottom")
        seuil = zone_seuil.slider(
            "Retards minimum par gare",
            min_value=0,
            max_value=SEUIL_MAXIMUM,
            value=SEUIL_PAR_DEFAUT,
            step=100,
            key=self._state.widget_key("seuil_retards"),
            on_change=self._journaliser,
            args=("seuil_retards",),
        )
        significatives = filtrer_gares_significatives(overall, seuil)
        zone_compte.caption(
            f"{len(significatives)} gares retenues sur {resume.nombre_gares}."
        )
        if significatives.empty:
            st.info("Aucune gare n'atteint ce seuil. Baissez le seuil minimal.")
            return

        references = {
            "retard_heritees": resume.part_heritees,
            "retard_non_heritees": resume.part_propres,
        }
        titres = {
            "retard_heritees": "Part des retards importés",
            "retard_non_heritees": "Part des retards nés sur place",
        }
        for zone, volume in zip(st.columns(2), references, strict=True):
            colonne = PARTS_CATEGORIES[volume]
            with zone:
                chart_container(
                    figure_classement_gares(
                        rank_stations(significatives, colonne, nombre),
                        colonne,
                        COULEURS_CATEGORIES[volume],
                        en_part=True,
                        reference=references[volume],
                    ),
                    title=titres[volume],
                    caption=(
                        "La ligne pointillée marque la moyenne de toutes les gares."
                    ),
                    key=self._state.widget_key(f"classement_{colonne}"),
                )

    def _section_carrefours(self, overall: pd.DataFrame, nombre: int) -> None:
        """Montre les gares présentes dans les deux classements."""
        croisees = croiser_classements(
            overall, "retard_non_heritees", "retard_heritees", nombre
        )
        section_header(
            4, "Qui est des deux côtés ?", titre_carrefours(len(croisees)), COULEUR_Q2
        )
        if croisees.empty:
            _contexte(
                f"Aucune gare n'est à la fois parmi les {nombre} qui fabriquent "
                f"le plus de retards et les {nombre} qui en encaissent le plus."
            )
            return

        _contexte(
            f"Ces gares sont à la fois parmi les {nombre} qui fabriquent le plus "
            f"de retards et les {nombre} qui en encaissent le plus : on ne peut "
            "pas les ranger d'un seul côté. Voici d'où viennent leurs retards."
        )
        total = overall[DELAY_COLUMNS].sum(axis=1)
        carrefours = (
            overall.assign(_total=total)
            .loc[lambda table: table["gare_depart"].isin(croisees["gare_depart"])]
            .sort_values("_total", ascending=False)
        )
        chart_container(
            figure_repartition_causes(carrefours),
            title="D'où viennent les retards de ces gares",
            caption=(
                "Chaque barre représente 100 % des retards d'une gare. Les gares "
                "sont triées de la plus touchée à la moins touchée."
            ),
            key=self._state.widget_key("repartition_carrefours"),
        )
        with st.expander("Voir le détail des rangs"):
            affichage = croisees.rename(
                columns={
                    "gare_depart": "Gare",
                    "retard_non_heritees": LIBELLES_CATEGORIES["retard_non_heritees"],
                    "retard_heritees": LIBELLES_CATEGORIES["retard_heritees"],
                    "rang_retard_non_heritees": "Rang (nés sur place)",
                    "rang_retard_heritees": "Rang (importés)",
                }
            ).round(0)
            rangs = ["Rang (nés sur place)", "Rang (importés)"]
            affichage[rangs] = affichage[rangs].astype(int)
            st.dataframe(affichage, hide_index=True, width="stretch")

    def _section_votre_gare(self, retards: RetardsParGare) -> None:
        """Raconte la gare choisie par l'utilisateur, selon ses réglages."""
        section_header(
            5,
            "Et votre gare ?",
            "Choisissez une gare : la page vous la raconte",
            COULEUR_Q2,
        )
        overall = retards.overall
        gares = sorted(overall["gare_depart"])
        total = overall[DELAY_COLUMNS].sum(axis=1)
        plus_touchee = overall.loc[total.idxmax(), "gare_depart"]

        gauche, droite, _ = st.columns([2, 2, 1], vertical_alignment="bottom")
        gare = gauche.selectbox(
            "Gare de départ",
            options=gares,
            index=gares.index(plus_touchee),
            key=self._state.widget_key("gare_evolution"),
            on_change=self._journaliser,
            args=("gare_evolution",),
        )
        niveau = droite.radio(
            "Période",
            options=["Par année", "Par mois"],
            horizontal=True,
            key=self._state.widget_key("niveau_evolution"),
            on_change=self._journaliser,
            args=("niveau_evolution",),
        )
        par_annee = niveau == "Par année"

        portrait = dresser_portrait_gare(
            gare, overall, retards.by_year, retards.by_month
        )
        phrases = rediger_portrait(
            portrait,
            "annee" if par_annee else "mois",
            inclut_2020=not self._exclut_2020(),
            minimum=self._seuil(),
        )
        with st.container(border=True):
            _phrase_cle(" ".join(phrases), taille="1.3rem")

        ensemble = ajouter_parts_retard(
            overall[DELAY_COLUMNS].sum().to_frame().T.assign(gare_depart=ENSEMBLE)
        )
        comparaison = pd.concat(
            [overall[overall["gare_depart"] == gare], ensemble], ignore_index=True
        )
        chart_container(
            figure_repartition_causes(comparaison),
            title=f"{gare} comparée à l'ensemble des gares",
            key=self._state.widget_key("comparaison_gare"),
        )

        table = retards.by_year if par_annee else retards.by_month
        axe = "annee" if par_annee else "date"
        chart_container(
            figure_evolution_gare(table[table["gare_depart"] == gare], axe),
            title=f"Retards estimés au départ de {gare}",
            caption=(
                "Chaque courbe suit une famille de retards au fil du temps. "
                "Une année ou un mois sans retard n'apparaît pas."
            ),
            key=self._state.widget_key("evolution_gare"),
        )

    def _render_method_box(self) -> None:
        """Explique la méthode et ses limites."""
        method_box(
            "**Méthode.** Pour chaque liaison et chaque mois, le nombre de trains "
            "arrivés en retard est réparti selon les pourcentages de causes "
            "publiés par la SNCF, puis regroupé en trois familles : nés sur place "
            "(infrastructure, gestion du trafic, matériel roulant), importés "
            "(gestion en gare, réutilisation du matériel, voyageurs) et venus de "
            "l'extérieur. Les retards sont additionnés par gare de départ.\n\n"
            "**Limites.**\n"
            "- Les nombres de retards par cause sont des estimations : la SNCF "
            "publie des pourcentages, pas des comptes.\n"
            "- Un retard à l'arrivée est attribué à la gare de départ de la "
            "liaison. C'est une hypothèse de lecture, pas une mesure.\n"
            "- « Gestion en gare et réutilisation de matériel » compte comme "
            "importé : une rame réutilisée transmet le retard de son trajet "
            "précédent. Ce choix se discute, la gestion en gare étant en partie "
            "locale.\n"
            "- En volume, les grandes gares dominent ; la section « Et à trafic "
            "égal ? » et son seuil nuancent ce biais.\n"
            "- Les tendances comparent des années complètes uniquement.\n"
            "- Seul le service national est étudié. Les lignes sans aucune cause "
            "renseignée sont écartées."
        )


Q2RetardsGaresPage().render()