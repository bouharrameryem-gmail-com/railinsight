"""Page Q4 : réseau, classements et comparaison interactive des liaisons."""

import pandas as pd
import streamlit as st

from railinsight.analysis.score_fiabilite import NOMS_CATEGORIES, ParametresScore
from railinsight.backend.fiabilite import (
    analyser_fiabilite,
    charger_table_score,
    positions_reseau,
)
from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.base_page import BasePage
from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.components.method_box import method_box
from railinsight.ui.providers import get_provider
from railinsight.ui.state.base_state import PageState
from railinsight.utils.formatting import fmt_month, fmt_number, fmt_pct
from railinsight.viz.fiabilite import (
    figure_classement,
    figure_reseau,
    formater_minutes,
)

_PRIORITES = {
    "Équilibrer les deux": 0.5,
    "Éviter les annulations": 0.75,
    "Éviter les retards": 0.25,
}

_LIBELLES_CATEGORIES = {
    "Très fiable": "Bleu foncé — Très fiable (85 à 100)",
    "Fiable": "Bleu clair — Fiable (70 à moins de 85)",
    "Moyenne": "Jaune — Moyenne (55 à moins de 70)",
    "Peu fiable": "Orange — Peu fiable (40 à moins de 55)",
    "À risque": "Rouge — À risque (moins de 40)",
}

_CODE_RESEAU = """import plotly.graph_objects as go
import streamlit as st

from railinsight.backend.fiabilite import positions_reseau
from railinsight.viz.fiabilite import COULEURS_CATEGORIES

# table : données préparées ; liaisons : notes calculées sur la période.
positions = positions_reseau(table)
affichees = liaisons[liaisons["categorie"].isin(categories)]
figure = go.Figure()

for categorie, groupe in affichees.groupby("categorie"):
    x, y = [], []
    for liaison in groupe.itertuples():
        xa, ya = positions[liaison.gare_a]
        xb, yb = positions[liaison.gare_b]
        x.extend([xa, xb, None])
        y.extend([ya, yb, None])
    figure.add_trace(go.Scatter(
        x=x, y=y, mode="lines", name=categorie,
        line={"color": COULEURS_CATEGORIES[categorie]},
    ))

gares = sorted(set(affichees["gare_a"]) | set(affichees["gare_b"]))
figure.add_trace(go.Scatter(
    x=[positions[g][0] for g in gares],
    y=[positions[g][1] for g in gares],
    mode="markers", text=gares, name="Gares",
))
figure.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
st.plotly_chart(figure, width="stretch")"""


@st.cache_data(show_spinner="Préparation des données…")
def _table_score() -> pd.DataFrame:
    """Met les données préparées en cache."""
    return charger_table_score()


@st.cache_data
def _positions_reseau() -> dict[str, tuple[float, float]]:
    """Conserve les mêmes positions quand les filtres changent."""
    return positions_reseau(_table_score())


@st.cache_data
def _analyser(debut: str, fin: str, poids: float) -> pd.DataFrame:
    """Met les notes de la période et de la priorité choisies en cache."""
    return analyser_fiabilite(
        _table_score(), debut, fin, ParametresScore(poids_annulations=poids)
    )


def _nom_mois(mois: str) -> str:
    """Affiche un mois en français."""
    return fmt_month(pd.Period(mois, freq="M"))


class Q4ScoreFiabilitePage(BasePage):
    """Affiche le score de fiabilité sans réglages techniques."""

    def __init__(self, provider: DataProvider) -> None:
        super().__init__(provider)
        self._state = PageState(page_key="q4_score_fiabilite")

    @property
    def question_number(self) -> int:
        return 4

    @property
    def question_title(self) -> str:
        return "Score de fiabilité"

    @property
    def author(self) -> str:
        return "Meryem"

    def _render_header(self) -> None:
        titre, auteur = st.columns([8, 2])
        with titre:
            st.title("Q4: score de fiabilité")
        with auteur:
            st.caption(f"Analyse : {self.author}")

    def _render_key_figures(self) -> None:
        st.write(
            "Peut-on résumer les annulations et les retards en une seule note ? "
            "Oui : plus la note sur 100 est élevée, plus la liaison est fiable."
        )

    def _render_controls(self) -> None:
        mois = sorted(_table_score()["mois"].unique())
        st.select_slider(
            "Période étudiée",
            options=mois,
            value=(mois[0], mois[-1]),
            format_func=_nom_mois,
            key=self._state.widget_key("periode"),
        )
        st.radio(
            "Pour vous, un trajet fiable, c'est surtout…",
            options=list(_PRIORITES),
            horizontal=True,
            key=self._state.widget_key("priorite"),
        )
        st.caption(
            "Changez votre priorité : les notes, les couleurs et le classement "
            "se mettent à jour. Les données restent les mêmes."
        )

    def _render_body(self) -> None:
        debut, fin = st.session_state[self._state.widget_key("periode")]
        priorite = st.session_state[self._state.widget_key("priorite")]
        liaisons = _analyser(debut, fin, _PRIORITES[priorite])
        nombre, meilleure, moins_bonne = st.columns(3)
        nombre.metric("Liaisons analysées", fmt_number(len(liaisons)))
        nombre.caption("Les deux sens sont regroupés.")
        meilleure.metric("Meilleure note", fmt_number(liaisons.iloc[0]["note"], 1))
        meilleure.caption(liaisons.iloc[0]["liaison"])
        moins_bonne.metric(
            "Note la plus basse", fmt_number(liaisons.iloc[-1]["note"], 1)
        )
        moins_bonne.caption(liaisons.iloc[-1]["liaison"])

        reseau, classement, match = st.tabs(
            ["Le réseau", "Le classement", "Le match des trajets"]
        )
        with reseau:
            self._afficher_reseau(liaisons)
        with classement:
            self._afficher_classement(liaisons)
        with match:
            self._afficher_match(liaisons)

    def _afficher_reseau(self, liaisons: pd.DataFrame) -> None:
        """Affiche les catégories choisies sans changer les notes ni les positions."""
        st.write(
            "Ce réseau relie les gares par les liaisons TGV étudiées. "
            "Un point représente une gare ; un trait, une liaison."
        )
        categories = st.multiselect(
            "Quelles liaisons afficher ?",
            options=NOMS_CATEGORIES,
            default=NOMS_CATEGORIES,
            format_func=_LIBELLES_CATEGORIES.__getitem__,
            key=self._state.widget_key("categories_reseau"),
            help=(
                "Choisissez une ou plusieurs catégories. "
                "Ce filtre ne change que le réseau."
            ),
        )
        affichees = liaisons[liaisons["categorie"].isin(categories)]
        st.caption(
            f"{len(affichees)} liaisons affichées sur {len(liaisons)}. "
            "Les classements et le match gardent toutes les liaisons."
        )
        if not categories:
            st.info("Choisissez au moins une catégorie pour afficher le réseau.")
        elif affichees.empty:
            st.info(
                "Aucune liaison dans ces catégories sur cette période. "
                "Choisissez une autre catégorie ou élargissez la période."
            )
        else:
            chart_container(
                figure_reseau(affichees, _positions_reseau()),
                title="Fiabilité des liaisons TGV",
                caption=(
                    "Bleu : fiable. Rouge : peu fiable. "
                    "Survolez le milieu d'un trait pour voir sa note. "
                    "Cliquez sur une catégorie de la légende pour la masquer."
                ),
            )
        st.caption(
            "Ce n'est pas une carte géographique : les distances ne sont pas "
            "des kilomètres."
        )
        with st.expander("Code source simplifié", expanded=False):
            st.caption(
                "Exemple pédagogique : on relie les positions des deux gares, "
                "puis on colore le trait selon la catégorie."
            )
            st.caption(
                "Ce code utilise la table préparée, les notes de la période "
                "et les catégories sélectionnées. Les détails au survol sont "
                "omis pour garder l'exemple court."
            )
            st.code(_CODE_RESEAU, language="python")

    def _afficher_classement(self, liaisons: pd.DataFrame) -> None:
        """Affiche les meilleures et les moins bonnes notes côte à côte."""
        st.write("Quelles liaisons se distinguent avec votre priorité ?")
        n = st.select_slider(
            "Nombre de liaisons par classement",
            options=[5, 10, 15],
            value=10,
            key=self._state.widget_key("nombre_classement"),
        )
        n = min(n, len(liaisons))
        meilleures, moins_bonnes = st.columns(2)
        with meilleures:
            chart_container(
                figure_classement(liaisons, n),
                title=f"Les {n} meilleures notes",
                key=self._state.widget_key("classement_meilleures"),
            )
        with moins_bonnes:
            chart_container(
                figure_classement(liaisons, n, meilleures=False),
                title=f"Les {n} notes les plus basses",
                key=self._state.widget_key("classement_moins_bonnes"),
            )
        st.caption(
            "Une barre = une liaison. Toutes les notes sont sur 100. "
            "Survolez une barre pour consulter les annulations et le retard moyen."
        )

    def _afficher_match(self, liaisons: pd.DataFrame) -> None:
        """Invite à deviner la mieux notée à partir de ses deux indicateurs."""
        st.write(
            "Deux liaisons, deux profils : laquelle obtient la meilleure note ? "
            "Comparez les indicateurs, puis révélez le résultat."
        )
        if len(liaisons) < 2:
            st.info("Élargissez la période pour comparer au moins deux liaisons.")
            return

        noms = sorted(liaisons["liaison"])
        gauche, droite = st.columns(2)
        with gauche:
            premier = st.selectbox(
                "Première liaison", noms, key=self._state.widget_key("match_a")
            )
        with droite:
            second = st.selectbox(
                "Deuxième liaison",
                [nom for nom in noms if nom != premier],
                key=self._state.widget_key("match_b"),
            )
        afficher = st.toggle("Révéler les notes", key=self._state.widget_key("reveler"))
        selection = liaisons.set_index("liaison")
        for colonne, nom in ((gauche, premier), (droite, second)):
            ligne = selection.loc[nom]
            with colonne:
                with st.container(border=True):
                    st.metric("Trains annulés", fmt_pct(ligne["taux_annulation"]))
                    st.metric(
                        "Retard moyen à l'arrivée",
                        formater_minutes(ligne["retard_moyen"]),
                    )
                    st.caption(f"{fmt_number(ligne['prevus'])} trains prévus")
                    if afficher:
                        st.metric("Note sur 100", fmt_number(ligne["note"], 1))
                        st.progress(float(ligne["note"]) / 100)
                        st.caption(ligne["categorie"])
        if afficher:
            note_a = round(float(selection.loc[premier, "note"]), 1)
            note_b = round(float(selection.loc[second, "note"]), 1)
            if note_a == note_b:
                st.info("Égalité à un dixième de point près avec votre priorité.")
            else:
                gagnante = premier if note_a > note_b else second
                st.success(
                    f"{gagnante} obtient la meilleure note avec votre priorité "
                    f"({fmt_number(abs(note_a - note_b), 1)} points d'écart)."
                )
        st.caption(
            "Il s'agit d'observations passées, pas d'une garantie pour votre "
            "prochain train. Ces liaisons ne sont pas forcément des alternatives."
        )

    def _render_method_box(self) -> None:
        method_box(
            "Par défaut, annulations et retard moyen comptent autant. "
            "Votre priorité donne un poids de 75 % au critère choisi "
            "et de 25 % à l'autre.\n\n"
            "À partir de 6 % d'annulations ou de 12 minutes de retard moyen, "
            "le critère concerné vaut zéro.\n\n"
            "Seules les liaisons avec au moins 100 trains prévus et un retard "
            "mesuré sont affichées. Tous les services sont inclus.\n\n"
            "Ces seuils sont des choix d'analyse, pas une note officielle de la SNCF."
        )


Q4ScoreFiabilitePage(get_provider()).render()
