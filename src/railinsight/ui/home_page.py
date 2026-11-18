"""Présentation des données brutes et de leurs statistiques."""

import streamlit as st

from railinsight.backend.dataloader import charger_donnees

st.title("Rail Insight Dashboard")
st.write("Raw Data link")
st.write(
    "https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/information/"
)
df = charger_donnees()
st.dataframe(df)

st.write("Summary Statistics")
st.write(df.columns.tolist())
st.write(df.dtypes)
st.write(df.describe())
