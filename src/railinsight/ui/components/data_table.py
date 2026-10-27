"""Interactive data table with a CSV download button.

Usage:
    data_table(df, title="Détail des liaisons", filename="liaisons.csv")
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def data_table(
    df: pd.DataFrame,
    title: str | None = None,
    filename: str = "export.csv",
    max_rows: int | None = None,
    key: str = "data_table_download",
) -> None:
    """Render a DataFrame as an interactive table with a CSV download button.

    Args:
        df: The DataFrame to display.
        title: Optional section heading above the table.
        filename: Name of the downloaded CSV file.
        max_rows: If set, only display the first max_rows rows. The full
            DataFrame is always exported to CSV.
        key: Unique key for the download button. Must be unique per page if
            the component is used more than once. Use widget_key() from PageState.
    """
    if title:
        st.markdown(f"**{title}**")

    display_df = df.head(max_rows) if max_rows is not None else df

    st.dataframe(display_df, use_container_width=True)

    if max_rows is not None and len(df) > max_rows:
        st.caption(
            f"Affichage limité aux {max_rows} premières lignes. "
            f"Le téléchargement contient les {len(df)} lignes."
        )

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Télécharger en CSV",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        key=key,
    )
