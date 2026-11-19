"""Construction et analyse des indicateurs de ponctualité pour le clustering."""

from typing import Literal

import pandas as pd

from railinsight.analysis.nettoyage import retirer_mois, taux
from railinsight.exceptions import InsufficientDataError

Exclusion = Literal["none", "known", "data"]

FEATURE_SETS: dict[str, list[str]] = {
    "v3": [
        "cancellation_rate",
        "late15_rate",
        "severe_share",
        "extreme_share",
        "volatility_cv",
    ],
    "fixed": [
        "cancellation_rate",
        "late15_rate",
        "severe_share",
        "volatility",
        "chronicity",
    ],
    "composite": [
        "cancellation_rate",
        "late_arrival_rate",
        "mean_delay_when_late",
        "severe_ratio",
        "irregularity",
    ],
}

MOIS_EXCEPTIONNELS: frozenset[str] = frozenset(
    {
        "2018-04",
        "2018-05",
        "2019-12",
        "2020-01",
        "2020-03",
        "2020-04",
        "2020-05",
        "2020-11",
        "2021-04",
    }
)

COMPTES = [
    "prevus",
    "annules",
    "circules",
    "retards_sup_15min",
    "retards_sup_30min",
    "retards_sup_60min",
    "retards_arrivee",
]

MIN_LIGNES_VALIDES = 5  # en dessous, une corrélation ou un ratio n'a pas de sens
_MIN_LIAISONS = 2
_SEUIL_REDONDANCE = 0.85


def taux_reseau_mensuel(table: pd.DataFrame) -> pd.Series:
    """Calcule le taux de retard supérieur à 15 minutes du réseau par mois."""
    par_mois = table.groupby("mois")[["retards_sup_15min", "circules"]].sum()
    return taux(par_mois["retards_sup_15min"], par_mois["circules"], pour=1.0)


def mois_a_exclure(taux_reseau: pd.Series, exclusion: Exclusion) -> frozenset[str]:
    """Détermine les mois à exclure selon la règle choisie."""
    if exclusion == "none":
        return frozenset()
    if exclusion == "known":
        return MOIS_EXCEPTIONNELS
    q1, q3 = taux_reseau.quantile([0.25, 0.75])
    return frozenset(taux_reseau.index[taux_reseau > q3 + 1.5 * (q3 - q1)])


def construire_indicateurs_liaison(
    table: pd.DataFrame,
    exclusion: Exclusion = "known",
    min_months: int = 24,
    cle: str = "liaison",
) -> pd.DataFrame:
    """Calcule les indicateurs de ponctualité de chaque liaison."""
    reseau = taux_reseau_mensuel(table)
    table = retirer_mois(table, mois_a_exclure(reseau, exclusion))

    par_liaison = table.groupby(cle)
    totaux = par_liaison[COMPTES].sum()
    minutes = (
        (table["retard_moyen_retardes_arrivee"] * table["retards_arrivee"])
        .groupby(table[cle])
        .sum()
    )

    l15_mensuel = taux(table["retards_sup_15min"], table["circules"], pour=1.0)
    la_mensuel = taux(table["retards_arrivee"], table["circules"], pour=1.0)
    taux_reseau = table["mois"].map(reseau)
    au_dessus = (l15_mensuel > taux_reseau).astype(float)
    au_dessus = au_dessus.where(l15_mensuel.notna() & taux_reseau.notna())
    volatilite = l15_mensuel.groupby(table[cle]).std()
    moyenne_l15 = l15_mensuel.groupby(table[cle]).mean().where(lambda s: s > 0)

    indicateurs = pd.DataFrame(
        {
            "n_months": par_liaison.size(),
            "trip_duration_min": par_liaison["duree_moyenne"].median(),
            "cancellation_rate": taux(totaux["annules"], totaux["prevus"], pour=1.0),
            "late15_rate": taux(
                totaux["retards_sup_15min"], totaux["circules"], pour=1.0
            ),
            "late30_rate": taux(
                totaux["retards_sup_30min"], totaux["circules"], pour=1.0
            ),
            "late60_rate": taux(
                totaux["retards_sup_60min"], totaux["circules"], pour=1.0
            ),
            "severe_share": taux(
                totaux["retards_sup_30min"], totaux["retards_sup_15min"], pour=1.0
            ),
            "extreme_share": taux(
                totaux["retards_sup_60min"], totaux["retards_sup_15min"], pour=1.0
            ),
            "late_arrival_rate": taux(
                totaux["retards_arrivee"], totaux["circules"], pour=1.0
            ),
            "mean_delay_when_late": taux(minutes, totaux["retards_arrivee"], pour=1.0),
            "volatility": volatilite,
            "volatility_cv": taux(volatilite, moyenne_l15, pour=1.0),
            "severe_ratio": taux(
                totaux["retards_sup_30min"], totaux["retards_arrivee"], pour=1.0
            ),
            "irregularity": la_mensuel.groupby(table[cle]).std(),
            "chronicity": au_dessus.groupby(table[cle]).mean(),
        }
    )
    indicateurs = indicateurs[indicateurs["n_months"] >= min_months].rename_axis(
        "route"
    )

    if len(indicateurs) < _MIN_LIAISONS:
        raise InsufficientDataError(
            f"Seulement {len(indicateurs)} liaison(s) ont ≥ {min_months} mois valides. "
            "Réduisez le seuil minimum ou changez la règle d'exclusion."
        )
    return indicateurs


def detect_redundancy(
    features: pd.DataFrame,
    cols: list[str],
    threshold: float = _SEUIL_REDONDANCE,
) -> list[tuple[str, str, float]]:
    """Repère les paires d'indicateurs fortement corrélées."""
    available = [c for c in cols if c in features.columns]
    valid = features[available].dropna()
    if len(valid) < MIN_LIGNES_VALIDES:
        return []
    correlations = valid.corr(method="spearman")
    return [
        (col_a, col_b, float(correlations.loc[col_a, col_b]))
        for i, col_a in enumerate(available)
        for col_b in available[i + 1 :]
        if abs(correlations.loc[col_a, col_b]) > threshold
    ]
