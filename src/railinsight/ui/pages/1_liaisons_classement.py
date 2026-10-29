"""Page : classement des liaisons TGV les moins fiables (Q1)."""

import streamlit as st

from railinsight.backend.reliability import get_reliability_report
from railinsight.viz.reliability import plot_worst_routes_bar

st.title("Les liaisons les moins fiables du réseau")

st.markdown(
    """
    Une liaison est considérée **en incident** le mois où un train est
    **annulé** ou **arrive avec plus de 15 minutes de retard** (seuil utilisé
    par la SNCF pour ses propres indicateurs de ponctualité). Le taux
    d'incidents est agrégé par liaison sur l'ensemble de la période
    (2018-01 → aujourd'hui) pour établir ce classement.
    """
)


@st.cache_data
def _load_report():
    return get_reliability_report()


report = _load_report()

st.plotly_chart(plot_worst_routes_bar(report.ranking), use_container_width=True)

st.subheader("Détail du classement")
st.dataframe(
    report.ranking[["planned", "incidents", "rate"]]
    .rename(
        columns={
            "planned": "Circulations prévues",
            "incidents": "Incidents",
            "rate": "Taux d'incidents",
        }
    )
    .style.format({"Taux d'incidents": "{:.1%}"}),
    use_container_width=True,
)

st.caption(
    "Les lignes où le nombre de circulations prévues est nul (73 lignes du "
    "jeu de données) sont exclues du calcul pour éviter une division par "
    "zéro — voir DATASHEET.md."
)
