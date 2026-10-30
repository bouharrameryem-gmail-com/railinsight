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
 
 
def filter_scope(table: pd.DataFrame, exclude_2020: bool = True) -> pd.DataFrame:
    """Garde le service national, convertit la date et ajoute l'année.
 
    Args:
        table: Résultat de `lire_donnees` ou de `nettoyer_regularite`. Doit
            contenir `service` et `date` (texte « AAAA-MM » ou déjà une date).
        exclude_2020: Si True, les lignes de l'année 2020 sont retirées.
 
    Returns:
        Un nouveau DataFrame avec `date` convertie en date et une colonne
        `annee`. L'entrée n'est pas modifiée.
 
    Raises:
        DonneesInvalides: aucune ligne pour le service national.
    """
    retour = filtrer_service(table)
    retour["date"] = convertir_mois(retour["date"])
    retour["annee"] = retour["date"].dt.year
    if exclude_2020:
        retour = retour[retour["annee"] != 2020]
    return retour.reset_index(drop=True)
 
 
def add_delay_categories(table: pd.DataFrame) -> pd.DataFrame:
    """Ajoute le nombre de trains en retard par catégorie de cause.
 
    Chaque effectif est le nombre de trains en retard à l'arrivée multiplié par
    la somme des pourcentages des causes de la catégorie, divisée par 100. Un
    pourcentage manquant compte pour 0.
 
    Args:
        table: Une ligne par (mois, liaison). Doit contenir `retards_arrivee` et
            toutes les colonnes de CAUSES_HERITEES, CAUSES_NON_HERITEES et
            CAUSES_EXTERNES.
 
    Returns:
        Une copie de `table` avec trois colonnes de plus : `retard_heritees`,
        `retard_non_heritees` et `retard_externes`.
    """
    retour = table.copy()
    for colonne, causes in GROUPES_CAUSES.items():
        retour[colonne] = retour["retards_arrivee"] * retour[causes].sum(axis=1) / 100
    return retour
 
 
def aggregate_by_station(table: pd.DataFrame, level: str | None = None) -> pd.DataFrame:
    """Additionne les trains en retard par catégorie, pour chaque gare de départ.
 
    Args:
        table: Résultat de `add_delay_categories` (et de `filter_scope` si
            `level` vaut `annee`, car cette fonction crée la colonne).
        level: None pour une ligne par gare sur toute la période, ou `annee` /
            `date` pour une ligne par gare et par période.
 
    Returns:
        Un nouveau DataFrame avec les clés de regroupement en colonnes, puis les
        trois colonnes de catégories.
 
    Raises:
        ValueError: `level` ne vaut ni None, ni `annee`, ni `date`.
    """
    if level not in LEVELS:
        raise ValueError(
            f"level must be one of {sorted(map(str, LEVELS))}, got {level!r}"
        )
    keys = ["gare_depart"] if level is None else ["gare_depart", level]
    return table.groupby(keys)[DELAY_COLUMNS].sum().reset_index()
 
 
def add_delay_shares(table: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la part de chaque catégorie dans le total des trains en retard.
 
    Args:
        table: Résultat de `aggregate_by_station`.
 
    Returns:
        Une copie de `table` avec `taux_heritees`, `taux_non_heritees` et
        `taux_externes` (valeurs entre 0 et 1). Une ligne sans train en retard
        donne NaN.
    """
    retour = table.copy()
    total = retour[DELAY_COLUMNS].sum(axis=1)
    for colonne in DELAY_COLUMNS:
        retour[colonne.replace("retard_", "taux_")] = taux(
            retour[colonne], total, pour=1.0
        )
    return retour
 
 
def rank_stations(table: pd.DataFrame, column: str, n: int = 15) -> pd.DataFrame:
    """Renvoie les n gares qui ont la plus grande valeur dans `column`.
 
    Args:
        table: Résultat de `aggregate_by_station` ou de `add_delay_shares`.
        column: Colonne utilisée pour le classement.
        n: Nombre de lignes à garder.
 
    Returns:
        Les n lignes aux plus grandes valeurs, triées par ordre décroissant.
        Les lignes où `column` est manquante sont ignorées.
    """
    return table.nlargest(n, column)
