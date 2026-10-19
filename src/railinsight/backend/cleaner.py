import pandas as pd


def clean_data(
    brut: pd.DataFrame,
    periode_debut: str | None = None,
    periode_fin: str | None = None,
) -> pd.DataFrame:
    """Clean the raw dataset and derive analysis columns.

    Args:
        brut: Raw SNCF dataset loaded from the CSV file.
        periode_debut: Optional inclusive start month, formatted as YYYY-MM.
        periode_fin: Optional inclusive end month, formatted as YYYY-MM.

    Returns:
        A cleaned DataFrame with one row per monthly connection and direction
        as provided in the source dataset, plus derived analysis columns.
    """
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(brut["Date"]),
            "depart": brut["Gare de départ"].str.strip().str.title(),
            "arrivee": brut["Gare d'arrivée"].str.strip().str.title(),
            "prevus": pd.to_numeric(brut["Nombre de circulations prévues"]),
            "annules": pd.to_numeric(brut["Nombre de trains annulés"]),
            "retard_tous": pd.to_numeric(
                brut["Retard moyen de tous les trains à l'arrivée"]
            ),
        }
    )

    data = data[data["prevus"] > 0].copy()
    data["circules"] = data["prevus"] - data["annules"]
    data["minutes_retard"] = data["retard_tous"] * data["circules"]
    data["gare_a"] = data[["depart", "arrivee"]].min(axis=1)
    data["gare_b"] = data[["depart", "arrivee"]].max(axis=1)
    data["mois"] = data["date"].dt.to_period("M").astype(str)

    if periode_debut is not None:
        data = data[data["mois"] >= periode_debut]

    if periode_fin is not None:
        data = data[data["mois"] <= periode_fin]

    return data.reset_index(drop=True)
