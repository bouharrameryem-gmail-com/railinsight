"""Accueil : orientation par usage, bilan daté et limites des données."""

import logging

import pandas as pd
import streamlit as st

from railinsight.analysis.accueil import (
    BilanAccueil,
    TauxAccueil,
    calculer_bilan_accueil,
    calculer_liaisons_accueil,
)
from railinsight.backend.profils_ponctualite import charger_donnees_clean
from railinsight.exceptions import DonneesInvalides
from railinsight.ui.components.route_map import carte_accueil
from railinsight.utils.formatting import fmt_month, fmt_number, fmt_pct

logger = logging.getLogger(__name__)
_Q1 = "src/railinsight/ui/pages/q1_liaisons_fiabilite.py"
_QUESTIONS = [
    (
        "Comparer les liaisons",
        "Repérez les liaisons les moins fiables, suivez leur évolution et "
        "explorez une prévision mensuelle à trois mois.",
        "Comparer les liaisons et leurs tendances",
        ":material/trending_up:",
        _Q1,
    ),
    (
        "Comprendre les retards",
        "Explorez les retards au départ des gares et leurs causes déclarées. "
        "Distinguez les constats des hypothèses de responsabilité.",
        "Explorer les retards par gare",
        ":material/alt_route:",
        "src/railinsight/ui/pages/q2_departure_stations.py",
    ),
    (
        "Explorer les profils",
        "Découvrez les groupes de liaisons aux comportements similaires : "
        "régularité, annulations et retards importants.",
        "Découvrir les profils de ponctualité",
        ":material/scatter_plot:",
        "src/railinsight/ui/pages/ponctualite_liaisons.py",
    ),
    (
        "Consulter les scores",
        "Comparez une note combinant annulations et retards, et situez "
        "les liaisons sur un schéma du réseau.",
        "Consulter les scores de fiabilité",
        ":material/hub:",
        "src/railinsight/ui/pages/q4_score_fiabilite.py",
    ),
]


@st.cache_data(show_spinner=False, ttl=3600, max_entries=1)
def _charger_donnees_accueil() -> pd.DataFrame:
    """Partage la même source nationale entre le bilan et la carte."""
    return charger_donnees_clean()


@st.cache_data(show_spinner=False, ttl=3600, max_entries=1)
def _charger_kpis_accueil() -> BilanAccueil:
    """Charge le bilan national sur les douze derniers mois disponibles."""
    return calculer_bilan_accueil(_charger_donnees_accueil())


@st.cache_data(show_spinner=False, ttl=3600, max_entries=1)
def _charger_liaisons_accueil() -> pd.DataFrame:
    """Prépare une seule fois les comptes de la fenêtre affichée."""
    return calculer_liaisons_accueil(
        _charger_donnees_accueil(), _charger_kpis_accueil()
    )


def _afficher_carte() -> None:
    """Propose une exploration géographique et son équivalent tabulaire."""
    st.header("Explorer le réseau sur la carte")
    try:
        bilan = _charger_kpis_accueil()
        liaisons = _charger_liaisons_accueil()
    except DonneesInvalides as exc:
        logger.exception("Carte de l'accueil indisponible")
        st.error(f"Carte indisponible : {exc}")
        return
    st.write(
        f"**TGV nationaux · {fmt_month(pd.Period(bilan.debut))} → "
        f"{fmt_month(pd.Period(bilan.fin))}**"
    )
    st.caption(
        "Choisissez une gare pour alléger la carte. Survolez une liaison "
        "ou touchez ses extrémités pour consulter ses chiffres."
    )
    if liaisons.empty:
        st.info("Aucune liaison ne dispose de comptes valides pour cette carte.")
        return
    gares = sorted(set(liaisons["gare_a"]) | set(liaisons["gare_b"]))
    options = ["Tout le réseau", *gares]
    cle = "accueil_gare_carte"
    if st.session_state.get(cle) not in options:
        st.session_state[cle] = options[0]
    gare = st.selectbox("Gare à explorer", options, key=cle)
    selection = liaisons
    if gare != options[0]:
        selection = liaisons[liaisons["gare_a"].eq(gare) | liaisons["gare_b"].eq(gare)]
    figure, manquantes = carte_accueil(selection)
    if figure.data:
        st.plotly_chart(
            figure,
            width="stretch",
            key="accueil_carte",
            alt="Connexions entre gares TGV, colorées par taux d'annulation "
            "ou retard supérieur à quinze minutes ; chiffres dans le tableau associé.",
            config={"scrollZoom": False, "displaylogo": False},
        )
    else:
        st.info("Les coordonnées de cette sélection ne sont pas disponibles.")
    st.caption(
        f"{len(selection) - len(manquantes)} / {len(selection)} liaison(s) "
        f"représentée(s) dans la sélection · {len(liaisons)} mesurable(s) "
        f"sur {bilan.n_liaisons} avec trafic."
    )
    if manquantes:
        st.warning(
            f"Coordonnées absentes pour {len(manquantes)} liaison(s) : "
            "elles restent consultables dans le tableau ci-dessous."
        )
    if len(liaisons) < bilan.n_liaisons:
        st.warning(
            "Certaines liaisons avec trafic n'ont pas de comptes valides "
            "pour calculer leur taux d'incidents."
        )
    st.caption(
        "Traits directs entre gares, pas le tracé ferroviaire réel. Deux sens "
        "regroupés. Couleur = (annulations + retards > 15 min) / trains prévus "
        "mesurés. Seuils visuels 10 % et 20 %, sans valeur de norme SNCF. "
        "Une liaison peut avoir moins de 12 mois mesurés. Fond © OpenStreetMap."
    )
    with st.expander("Chiffres de la carte — tableau accessible"):
        tableau = selection[["liaison", "taux_incidents", "prevus", "n_mois"]].copy()
        tableau["taux_incidents"] = tableau["taux_incidents"].map(fmt_pct)
        tableau["Localisation"] = tableau["liaison"].map(
            lambda liaison: (
                "Coordonnées absentes" if liaison in manquantes else "Sur la carte"
            )
        )
        st.dataframe(
            tableau.rename(
                columns={
                    "liaison": "Liaison (deux sens)",
                    "taux_incidents": "Annulés ou retardés > 15 min",
                    "prevus": "Trains prévus mesurés",
                    "n_mois": "Mois mesurés / 12",
                }
            ),
            hide_index=True,
            alt="Liste des liaisons de la sélection, y compris sans coordonnées.",
        )


def _afficher_taux(label: str, mesure: TauxAccueil, aide: str) -> None:
    """Affiche un taux et une variation dont une baisse est favorable."""
    delta = mesure.evolution_points
    st.metric(
        label,
        fmt_pct(mesure.valeur) if mesure.valeur is not None else "Non disponible",
        delta=(f"{delta:+.1f} pts".replace(".", ",") if delta is not None else None),
        delta_color="inverse",
        help=aide,
        border=True,
    )
    if mesure.valeur is None:
        st.caption("Aucune mesure valide sur cette période.")
    elif delta is None:
        st.caption("Évolution non disponible : historique ou périmètre non comparable.")
    if mesure.lignes_ecartees:
        st.caption(
            f"{mesure.lignes_ecartees} ligne(s) exclue(s) : "
            "comptes manquants ou incohérents."
        )


def _afficher_bilan() -> None:
    """Présente des chiffres contextualisés sans bloquer la navigation."""
    st.header("Le réseau en bref")
    try:
        bilan = _charger_kpis_accueil()
    except DonneesInvalides as exc:
        logger.exception("Indicateurs de l'accueil indisponibles")
        st.error(f"Indicateurs indisponibles : {exc}")
        return
    debut = fmt_month(pd.Period(bilan.debut))
    fin = fmt_month(pd.Period(bilan.fin))
    st.write(f"**TGV nationaux · {debut} → {fin}**")
    st.caption(
        "Fenêtre des 12 derniers mois disponibles, pas des 12 mois précédant "
        "aujourd'hui. Les données SNCF sont publiées avec un décalage."
    )
    if bilan.n_mois < 12:
        st.warning(
            f"Historique incomplet : {bilan.n_mois} mois présent(s) sur 12. "
            "Les taux portent uniquement sur les mois disponibles."
        )
    with st.container(horizontal=True, gap="medium"):
        with st.container():
            st.metric(
                "Liaisons nationales",
                fmt_number(bilan.n_liaisons),
                help="Paires de gares avec des trains prévus sur cette période, "
                "les deux sens regroupés. Q1 utilise des liaisons orientées et "
                "inclut aussi le service international : ses effectifs diffèrent.",
                border=True,
            )
            st.caption("Deux sens regroupés, avec du trafic sur la période.")
        with st.container():
            _afficher_taux(
                "Retards à l'arrivée > 15 min",
                bilan.retards,
                "Trains en retard de plus de 15 minutes / trains circulés. "
                "Ratio des sommes, pondéré par le trafic mesuré.",
            )
        with st.container():
            _afficher_taux(
                "Annulations",
                bilan.annulations,
                "Trains annulés / trains prévus. Ratio des sommes, "
                "pondéré par le trafic mesuré.",
            )
    st.caption(
        "Variations en points de pourcentage par rapport à "
        f"{fmt_month(pd.Period(bilan.debut_precedent))} → "
        f"{fmt_month(pd.Period(bilan.fin_precedent))}, uniquement si les mois "
        "et les liaisons mesurés sont comparables. Une baisse est favorable."
    )


st.caption("RAILINSIGHT · PROJET TÉLÉCOM PARIS · SNCF OPEN DATA")
st.title("Comprendre la fiabilité de votre liaison TGV")
st.write(
    "Comparez les liaisons, comprenez les retards et explorez les tendances "
    "à partir des statistiques mensuelles de la SNCF."
)
with st.container(horizontal=True, vertical_alignment="center"):
    if st.button(
        "Explorer une liaison",
        icon=":material/search:",
        type="primary",
    ):
        st.switch_page(_Q1)
    st.caption("Données mensuelles · pas de suivi des trains en temps réel")

_afficher_bilan()
_afficher_carte()
st.header("Que souhaitez-vous explorer ?")
for debut in range(0, len(_QUESTIONS), 2):
    colonnes = st.columns(2, gap="medium")
    for colonne, (titre, texte, action, icone, chemin) in zip(
        colonnes, _QUESTIONS[debut : debut + 2], strict=True
    ):
        with colonne, st.container(border=True, height="stretch"):
            st.subheader(titre)
            st.write(texte)
            st.space("stretch")
            st.page_link(chemin, label=action, icon=icone, width="stretch")

st.info(
    "Q5 — Prédiction des retards > 15/30 min : en cours de développement. "
    "Cette analyse n'est pas encore disponible. La prévision mensuelle "
    "exploratoire de Q1 est un travail distinct.",
    icon=":material/construction:",
)
with st.expander("Méthode, périmètre et limites"):
    st.markdown(
        "- **Source :** [SNCF Open Data — Régularité mensuelle TGV (AQST)]"
        "(https://ressources.data.sncf.com/explore/dataset/"
        "regularite-mensuelle-tgv-aqst/).\n"
        "- **Accueil :** service national, deux sens regroupés pour le nombre "
        "de liaisons ; comptage limité à la fenêtre affichée.\n"
        "- **Calcul :** ratios de sommes sur les lignes aux comptes valides, "
        "pas une moyenne simple des pourcentages mensuels. Les doublons "
        "mois/départ/arrivée sont dédupliqués en gardant la dernière ligne.\n"
        "- **Comparaison :** deux fenêtres de 12 mois avec la même couverture "
        "mois de l'année/départ/arrivée pour chaque indicateur ; sinon, "
        "aucune variation n'est affichée. Les mois absents ne sont pas "
        "remplacés par des zéros.\n"
        "- **Prudence :** les périmètres et nettoyages diffèrent selon "
        "l'analyse. Les agrégats par liaison ne représentent pas nécessairement "
        "des trains physiques distincts. Aucune garantie pour un trajet précis.\n"
        "- **Actualisation :** le site utilise l'API ; le dernier mois et "
        "l'heure de récupération UTC sont affichés dans la barre latérale. "
        "Les notebooks conservent leur CSV local."
    )
with st.expander("Le projet et l'équipe"):
    st.write(
        "Q1 — Michelle : fiabilité des liaisons et prévision mensuelle.  \n"
        "Q2 — Éric : retards par gare.  \n"
        "Q3 — Bachelard : profils de ponctualité.  \n"
        "Q4 — Meryem : score de fiabilité.  \n"
        "Q5 — Prédiction des retards : en cours."
    )
st.caption(
    "Projet pédagogique indépendant ; ni service officiel SNCF ni outil temps réel."
)
