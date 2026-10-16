import streamlit as st

st.set_page_config(page_title="Rail Insight", layout="wide")

pg = st.navigation(
    [
        st.Page(
            "src/railinsight/ui/home_page.py",
            title="Home",
            icon=":material/home:",
            default=True,
        ),
        st.Page("src/railinsight/ui/pages/1_page_one.py", title="Page One"),
        st.Page("src/railinsight/ui/pages/2_page_two.py", title="Page Two"),
        st.Page("src/railinsight/ui/pages/3_page_three.py", title="Page Three"),
    ]
)
pg.run()
