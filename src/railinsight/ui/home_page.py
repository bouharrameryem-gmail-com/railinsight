import pandas as pd
import streamlit as st

st.title("Rail Insight Dashboard")
st.write("Raw Data link")
st.write("https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/information/")
df = pd.read_csv("data/raw/regularite-mensuelle-tgv-aqst.csv", sep=";")
st.dataframe(df)

st.write("Summary Statistics")
st.write(df.columns.tolist())
st.write(df.dtypes)
st.write(df.describe())
