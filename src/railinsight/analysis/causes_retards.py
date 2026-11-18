"""Analyse des causes de retard par gare de départ."""

from dataclasses import dataclass

import pandas as pd

from railinsight.analysis.nettoyage import convertir_mois, filtrer_service, taux
from railinsight.exceptions import DonneesInvalides, InvalidSelectionError


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
MOIS_PAR_AN = 12
MOIS_ETE = (6, 7, 8)
NOMBRE_PIRES_MOIS = 12
MIN_ANNEES_TENDANCE = 3



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
    toutes = CAUSES_HERITEES + CAUSES_NON_HERITEES + CAUSES_EXTERNES
    masque = retour[toutes].isna().all(axis=1)
    retour = retour[~masque].copy()

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


def filtrer_gares_significatives(table: pd.DataFrame, minimum: int) -> pd.DataFrame:
    """Garde les lignes dont le total de retards atteint un minimum.

    Évite qu'une gare avec très peu de retards domine un classement en parts.

    Args:
        table: Résultat de `agreger_par_gare`, avec les colonnes de DELAY_COLUMNS.
        minimum: Nombre minimal de retards (toutes catégories confondues).

    Returns:
        Une copie des lignes retenues, index remis à zéro.

    Raises:
        ValueError: Si `minimum` est négatif.
    """
    if minimum < 0:
        raise ValueError(f"minimum doit être positif ou nul, reçu : {minimum!r}")
    total = table[DELAY_COLUMNS].sum(axis=1)
    return table[total >= minimum].reset_index(drop=True)


def croiser_classements(
    table: pd.DataFrame, colonne_a: str, colonne_b: str, n: int = 15
) -> pd.DataFrame:
    """Repère les gares présentes dans les n premières de deux classements.

    Args:
        table: Une ligne par gare, avec `gare_depart`, `colonne_a` et `colonne_b`.
        colonne_a: Colonne du premier classement (valeur la plus haute en tête).
        colonne_b: Colonne du second classement.
        n: Taille du haut de classement considéré.

    Returns:
        Les gares présentes dans les deux hauts de classement, avec leurs deux
        valeurs et leurs deux rangs (`rang_<colonne>`), triées selon le premier
        rang. Les valeurs manquantes ne sont jamais classées.
    """

    rang_a = table[colonne_a].rank(ascending=False, method="first")
    rang_b = table[colonne_b].rank(ascending=False, method="first")
    dans_les_deux = (rang_a <= n) & (rang_b <= n)
    resultat = table.loc[dans_les_deux, ["gare_depart", colonne_a, colonne_b]].copy()

    resultat[f"rang_{colonne_a}"] = rang_a[dans_les_deux]
    resultat[f"rang_{colonne_b}"] = rang_b[dans_les_deux]
    return resultat.sort_values(f"rang_{colonne_a}").reset_index(drop=True)



@dataclass(frozen=True)
class ResumeRetardsGares:
    """Chiffres clés de la page Q2, calculés sur la table agrégée par gare.

    Les volumes sont des nombres de trains estimés, les parts sont entre 0 et 1.
    `gare_part_heritee` et `part_heritee_max` valent None quand aucune gare
    n'atteint le minimum de retards demandé.
    """

    nombre_gares: int
    total_retards: float
    part_propres: float
    part_heritees: float
    part_externes: float
    gare_propres: str
    volume_propres: float
    part_top3_propres: float
    gare_heritees: str
    volume_heritees: float
    nombre_significatives: int
    gare_part_heritee: str | None
    part_heritee_max: float | None


@dataclass(frozen=True)
class Evolution:
    """Valeur d'un indicateur la première et la dernière année retenues."""

    annee_debut: int
    valeur_debut: float
    annee_fin: int
    valeur_fin: float

    @property
    def ecart(self) -> float:
        """Différence entre la valeur de fin et celle de début."""
        return self.valeur_fin - self.valeur_debut


@dataclass(frozen=True)
class PortraitGare:
    """Faits sur une gare de départ, comparée à l'ensemble des gares.

    `mois_pic` vaut None si la gare n'a aucun mois de données ; `evolution`
    vaut None s'il y a trop peu d'années complètes.
    """

    gare: str
    total_retards: float
    part_heritee: float
    part_heritee_moyenne: float
    rang_propres: int
    rang_heritees: int
    nombre_gares: int
    evolution: Evolution | None
    mois_pic: pd.Timestamp | None
    volume_pic: float
    pires_mois_ete: int
    pires_mois_total: int


def _part(valeur: float, total: float) -> float:
    """Renvoie valeur / total, ou 0 si le total est nul."""
    return float(valeur / total) if total > 0 else 0.0


def resumer_retards_gares(
    par_gare: pd.DataFrame, minimum: int = 1000
) -> ResumeRetardsGares:
    """Calcule les chiffres clés de la page Q2.

    Args:
        par_gare: Une ligne par gare de départ, avec les colonnes de
            DELAY_COLUMNS et leurs parts (voir `ajouter_parts_retard`).
        minimum: Nombre minimal de retards pour qu'une gare compte dans le
            classement en parts.

    Returns:
        Les chiffres clés, prêts à être mis en forme par la page.

    Raises:
        DonneesInvalides: Si la table ne contient aucune gare.
    """
    if par_gare.empty:
        raise DonneesInvalides("aucune gare de départ à résumer")

    totaux = par_gare[DELAY_COLUMNS].sum()
    total = float(totaux.sum())
    propres = par_gare.nlargest(3, "retard_non_heritees")
    heritees = par_gare.nlargest(1, "retard_heritees")
    significatives = filtrer_gares_significatives(par_gare, minimum)
    meilleure = significatives.dropna(subset=["taux_heritees"]).nlargest(
        1, "taux_heritees"
    )

    return ResumeRetardsGares(
        nombre_gares=len(par_gare),
        total_retards=total,
        part_propres=_part(totaux["retard_non_heritees"], total),
        part_heritees=_part(totaux["retard_heritees"], total),
        part_externes=_part(totaux["retard_externes"], total),
        gare_propres=str(propres.iloc[0]["gare_depart"]),
        volume_propres=float(propres.iloc[0]["retard_non_heritees"]),
        part_top3_propres=_part(
            propres["retard_non_heritees"].sum(), totaux["retard_non_heritees"]
        ),
        gare_heritees=str(heritees.iloc[0]["gare_depart"]),
        volume_heritees=float(heritees.iloc[0]["retard_heritees"]),
        nombre_significatives=len(significatives),
        gare_part_heritee=(
            str(meilleure.iloc[0]["gare_depart"]) if not meilleure.empty else None
        ),
        part_heritee_max=(
            float(meilleure.iloc[0]["taux_heritees"]) if not meilleure.empty else None
        ),
    )


def parts_reseau(par_periode: pd.DataFrame, niveau: str) -> pd.DataFrame:
    """Additionne les retards de toutes les gares pour chaque période.

    Args:
        par_periode: Résultat de `agreger_par_gare` au niveau `niveau`.
        niveau: Colonne de temps, `annee` ou `date`.

    Returns:
        Une ligne par période, triée dans le temps, avec les volumes et les
        parts de chaque catégorie.
    """
    reseau = par_periode.groupby(niveau)[DELAY_COLUMNS].sum().reset_index()
    return ajouter_parts_retard(reseau).sort_values(niveau, ignore_index=True)


def annees_completes(par_mois: pd.DataFrame) -> list[int]:
    """Renvoie les années dont les douze mois figurent dans les données.

    Args:
        par_mois: Table avec une colonne `date`, un mois par valeur.

    Returns:
        Les années complètes, dans l'ordre chronologique.
    """
    mois = par_mois["date"].drop_duplicates()
    comptes = mois.groupby(mois.dt.year).size()
    return [int(annee) for annee in comptes[comptes == MOIS_PAR_AN].index]


def evolution_part(
    par_annee: pd.DataFrame,
    colonne: str,
    annees: list[int],
    minimum: int = MIN_ANNEES_TENDANCE,
) -> Evolution | None:
    """Compare une part entre la première et la dernière année retenue.

    Args:
        par_annee: Une ligne par année, avec les colonnes `annee` et `colonne`.
        colonne: Part à comparer, entre 0 et 1.
        annees: Années utilisables, par exemple les années complètes.
        minimum: Nombre d'années nécessaire pour parler d'évolution.

    Returns:
        L'évolution, ou None s'il y a moins de `minimum` années utilisables.
    """
    serie = (
        par_annee[par_annee["annee"].isin(annees)]
        .dropna(subset=[colonne])
        .sort_values("annee")
    )
    if len(serie) < minimum:
        return None
    debut, fin = serie.iloc[0], serie.iloc[-1]
    return Evolution(
        annee_debut=int(debut["annee"]),
        valeur_debut=float(debut[colonne]),
        annee_fin=int(fin["annee"]),
        valeur_fin=float(fin[colonne]),
    )


def dresser_portrait_gare(
    gare: str,
    par_gare: pd.DataFrame,
    par_annee: pd.DataFrame,
    par_mois: pd.DataFrame,
) -> PortraitGare:
    """Rassemble les faits sur une gare, comparée à l'ensemble des gares.

    Args:
        gare: Nom de la gare de départ choisie.
        par_gare: Une ligne par gare, avec volumes et parts.
        par_annee: Une ligne par gare et par année, avec volumes et parts.
        par_mois: Une ligne par gare et par mois, avec les volumes.

    Returns:
        Le portrait de la gare.

    Raises:
        InvalidSelectionError: Si la gare n'existe pas dans les données.
    """
    indexee = par_gare.set_index("gare_depart")
    if gare not in indexee.index:
        raise InvalidSelectionError(f"gare de départ inconnue : {gare!r}")

    ligne = indexee.loc[gare]
    total = float(ligne[DELAY_COLUMNS].sum())
    totaux = indexee[DELAY_COLUMNS].sum()
    rangs_propres = indexee["retard_non_heritees"].rank(ascending=False, method="min")
    rangs_heritees = indexee["retard_heritees"].rank(ascending=False, method="min")

    volumes = (
        par_mois[par_mois["gare_depart"] == gare]
        .set_index("date")[DELAY_COLUMNS]
        .sum(axis=1)
    )
    pires = volumes.nlargest(NOMBRE_PIRES_MOIS)

    return PortraitGare(
        gare=gare,
        total_retards=total,
        part_heritee=_part(ligne["retard_heritees"], total),
        part_heritee_moyenne=_part(totaux["retard_heritees"], totaux.sum()),
        rang_propres=int(rangs_propres[gare]),
        rang_heritees=int(rangs_heritees[gare]),
        nombre_gares=len(indexee),
        evolution=evolution_part(
            par_annee[par_annee["gare_depart"] == gare],
            "taux_heritees",
            annees_completes(par_mois),
        ),
        mois_pic=volumes.idxmax() if not volumes.empty else None,
        volume_pic=float(volumes.max()) if not volumes.empty else 0.0,
        pires_mois_ete=int(pires.index.month.isin(MOIS_ETE).sum()),
        pires_mois_total=len(pires),
    )
