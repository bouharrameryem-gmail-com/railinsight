import pandas as pd

from railinsight.analysis.nettoyage import convertir_mois, filtrer_service, taux

CAUSES_NON_HERITEES = [
    "prct_cause_infrastructure",
    "prct_cause_trafic",
    "prct_cause_materiel",
]
CAUSES_HERITEES = ["prct_cause_gare", "prct_cause_voyageurs"]
CAUSES_EXTERNES = ["prct_cause_externe"]

GROUPES_CAUSES = {
    "retard_heritees": CAUSES_HERITEES,
    "retard_non_heritees": CAUSES_NON_HERITEES,
    "retard_externes": CAUSES_EXTERNES,
}
DELAY_COLUMNS = list(GROUPES_CAUSES)
LEVELS = {None, "annee", "date"}


def filtrer_perimetre_national(
    table: pd.DataFrame, exclude_2020: bool = True
) -> pd.DataFrame:
    """Garde les données nationales et ajoute l'année."""
    retour = filtrer_service(table)
    retour["date"] = convertir_mois(retour["date"])
    retour["annee"] = retour["date"].dt.year
    if exclude_2020:
        retour = retour[retour["annee"] != 2020]
    return retour.reset_index(drop=True)


def ajouter_categories_retard(table: pd.DataFrame) -> pd.DataFrame:
    """Calcule le nombre de retards pour chaque catégorie de cause."""
    retour = table.copy()
    for colonne, causes in GROUPES_CAUSES.items():
        retour[colonne] = retour["retards_arrivee"] * retour[causes].sum(axis=1) / 100
    return retour


def agreger_par_gare(table: pd.DataFrame, niveau: str | None = None) -> pd.DataFrame:
    """Additionne les retards par gare et par période."""
    if niveau not in LEVELS:
        raise ValueError(
            f"level must be one of {sorted(map(str, LEVELS))}, got {niveau!r}"
        )
    keys = ["gare_depart"] if niveau is None else ["gare_depart", niveau]
    return table.groupby(keys)[DELAY_COLUMNS].sum().reset_index()


def ajouter_parts_retard(table: pd.DataFrame) -> pd.DataFrame:
    """Calcule la part de chaque catégorie dans le total des retards."""
    retour = table.copy()
    total = retour[DELAY_COLUMNS].sum(axis=1)
    for colonne in DELAY_COLUMNS:
        retour[colonne.replace("retard_", "taux_")] = taux(
            retour[colonne], total, pour=1.0
        )
    return retour


def rank_stations(table: pd.DataFrame, column: str, n: int = 15) -> pd.DataFrame:
    """Renvoie les n gares ayant les valeurs les plus élevées dans une colonne."""
    return table.nlargest(n, column)
