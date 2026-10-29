"""Page : évolution et tendance de la fiabilité des liaisons (Q1)."""

import streamlit as st

from railinsight.backend.reliability import get_reliability_report
from railinsight.viz.reliability import plot_route_evolution

st.title("Évolution de la fiabilité dans le temps")


@st.cache_data
def _load_report():
    return get_reliability_report()


report = _load_report()

st.markdown(
    f"""
    Pour chacune des liaisons les moins fiables, le taux d'incidents mensuel
    est tracé dans le temps. La **tendance** (pente d'une régression
    linéaire simple) est calculée hors période COVID
    ({report.covid_start} → {report.covid_end}), un choc exceptionnel qui
    fausserait la mesure d'une évolution structurelle. Cette période reste
    visible, grisée, sur le graphique.
    """
)

top_routes = report.ranking.index[:5].tolist()
fig = plot_route_evolution(
    report.monthly, top_routes, report.covid_start, report.covid_end
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Tendance par liaison")
trend_table = report.ranking[["rate", "slope", "tendance"]].rename(
    columns={
        "rate": "Taux global",
        "slope": "Pente (pt/mois)",
        "tendance": "Tendance",
    }
)
st.dataframe(
    trend_table.style.format({"Taux global": "{:.1%}", "Pente (pt/mois)": "{:.4f}"}),
    use_container_width=True,
)

st.markdown(
    """
    **Pistes d'interprétation**
    - Les liaisons en tête du classement sont-elles structurellement peu
      fiables, ou simplement très fréquentées (donc plus exposées
      statistiquement) ?
    - La dégradation ou l'amélioration est-elle concentrée sur quelques
      liaisons, ou est-ce une tendance de réseau généralisée ?
    """
)
