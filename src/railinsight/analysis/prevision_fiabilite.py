"""Prévision exploratoire de la fiabilité mensuelle d'une liaison Q1."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import Ridge

from railinsight.exceptions import DonneesInvalides, InsufficientDataError

HORIZON_MOIS = 3
MIN_MOIS = 48
MODELES = {
    "saisonnier": "Même mois de l'année précédente",
    "ridge": "Tendance et saisonnalité (Ridge)",
}


@dataclass(frozen=True, eq=False)
class PrevisionFiabilite:
    """Prévisions en proportions, scores MAE en points de pourcentage."""

    liaison: str
    modele: str
    historique: pd.DataFrame
    previsions: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    scores_validation: pd.DataFrame
    mae_test: float
    mae_reference: float


def _variables(mois: pd.DatetimeIndex) -> NDArray[np.float64]:
    """Encode le temps et deux harmoniques annuelles sans donnée future."""
    temps = np.asarray(mois.year - 2000 + (mois.month - 1) / 12, dtype=float)
    angle = np.asarray(2 * np.pi * mois.month / 12, dtype=float)
    return np.column_stack(
        [temps, np.sin(angle), np.cos(angle), np.sin(2 * angle), np.cos(2 * angle)]
    )


def _predire(
    apprentissage: pd.DataFrame, mois: pd.DatetimeIndex, modele: str
) -> NDArray[np.float64]:
    """Prévoit trois mois à partir des seules observations déjà disponibles."""
    if modele == "saisonnier":
        precedents = mois - pd.DateOffset(years=1)
        return (
            apprentissage.set_index("mois")
            .loc[precedents, "fiabilite"]
            .to_numpy(dtype=float)
        )

    recent = apprentissage.tail(36)
    regression = Ridge(alpha=1.0)
    regression.fit(
        _variables(pd.DatetimeIndex(recent["mois"])),
        recent["fiabilite"].to_numpy(dtype=float),
        sample_weight=(recent["prevus"] / recent["prevus"].mean()).to_numpy(
            dtype=float
        ),
    )
    return np.clip(regression.predict(_variables(mois)), 0, 1)


def _historique(mensuel: pd.DataFrame, liaison: str) -> pd.DataFrame:
    """Vérifie les comptages et exige 48 mois récents consécutifs, sans imputation."""
    requises = {"liaison", "mois", "prevus", "incidents"}
    manquantes = sorted(requises - set(mensuel.columns))
    if manquantes:
        raise DonneesInvalides(
            "Prévision Q1 : colonnes manquantes : " + ", ".join(manquantes)
        )
    mensuel = mensuel.reset_index(drop=True)
    dates = pd.to_datetime(mensuel["mois"], errors="coerce")
    if dates.isna().any() or mensuel.empty:
        raise DonneesInvalides("Prévision Q1 : les dates mensuelles sont invalides.")
    dates = dates.dt.to_period("M").dt.to_timestamp()
    serie = mensuel.loc[mensuel["liaison"].eq(liaison)].copy()
    if serie.empty:
        raise DonneesInvalides(f"Prévision Q1 : liaison inconnue : {liaison}.")
    serie["mois"] = dates.loc[serie.index]
    if serie["mois"].duplicated().any():
        raise DonneesInvalides(
            "Prévision Q1 : agrégez les services par liaison et mois au préalable."
        )
    for colonne in ["prevus", "incidents"]:
        serie[colonne] = pd.to_numeric(serie[colonne], errors="coerce")
    comptages = serie[["prevus", "incidents"]].to_numpy(dtype=float)
    if (
        not np.isfinite(comptages).all()
        or serie["prevus"].le(0).any()
        or serie["incidents"].lt(0).any()
        or serie["incidents"].gt(serie["prevus"]).any()
    ):
        raise DonneesInvalides(
            "Prévision Q1 : comptages manquants ou impossibles "
            "(prévus > 0 et 0 ≤ incidents ≤ prévus requis)."
        )
    serie = serie.sort_values("mois").tail(MIN_MOIS)
    attendus = pd.date_range(end=dates.max(), periods=MIN_MOIS, freq="MS")
    if not pd.DatetimeIndex(serie["mois"]).equals(attendus):
        raise InsufficientDataError(
            f"Prévision indisponible pour {liaison} : {MIN_MOIS} mois valides "
            "consécutifs jusqu'au dernier mois du jeu sont nécessaires. "
            "Les mois absents ne sont pas remplacés par des zéros."
        )
    serie["fiabilite"] = 1 - serie["incidents"] / serie["prevus"]
    return serie[["mois", "prevus", "incidents", "fiabilite"]].reset_index(drop=True)


def prevoir_fiabilite(mensuel: pd.DataFrame, liaison: str) -> PrevisionFiabilite:
    """Prévoit les trois mois suivant le dernier mois disponible du jeu.

    Sur les 48 derniers mois consécutifs, quatre blocs de trois mois servent à
    choisir entre la référence saisonnière et Ridge. Les trois derniers mois,
    distincts de cette validation, évaluent le modèle retenu. Chaque origine
    n'utilise que son passé ; Ridge apprend sur 36 mois au maximum, pondérés par
    le nombre de trains prévus. Les prévisions finales réutilisent tout le passé.
    Les mois exceptionnels restent présents. Aucun retard journalier ni
    intervalle de prédiction calibré n'est estimé.
    """
    historique = _historique(mensuel, liaison)
    validations: list[pd.DataFrame] = []
    for debut in range(len(historique) - 15, len(historique) - 3, 3):
        apprentissage = historique.iloc[:debut]
        bloc = historique.iloc[debut : debut + HORIZON_MOIS]
        evaluation = bloc[["mois", "fiabilite"]].copy()
        evaluation["origine"] = apprentissage["mois"].iloc[-1]
        for modele in MODELES:
            evaluation[modele] = _predire(
                apprentissage, pd.DatetimeIndex(bloc["mois"]), modele
            )
        validations.append(evaluation)
    validation = pd.concat(validations, ignore_index=True)
    scores = pd.DataFrame(
        {
            "modele": list(MODELES),
            "mae_points": [
                (validation[modele] - validation["fiabilite"]).abs().mean() * 100
                for modele in MODELES
            ],
        }
    ).set_index("modele")
    # En cas d'égalité, préférer la référence la plus simple.
    modele_retenu = str(scores["mae_points"].idxmin())
    apprentissage = historique.iloc[:-HORIZON_MOIS]
    test = historique.tail(HORIZON_MOIS)[["mois", "fiabilite"]].copy()
    mois_test = pd.DatetimeIndex(test["mois"])
    test["prevision"] = _predire(apprentissage, mois_test, modele_retenu)
    test["reference"] = _predire(apprentissage, mois_test, "saisonnier")
    mae_test = float((test["prevision"] - test["fiabilite"]).abs().mean() * 100)
    mae_reference = float((test["reference"] - test["fiabilite"]).abs().mean() * 100)
    futurs = pd.date_range(
        start=historique["mois"].iloc[-1] + pd.offsets.MonthBegin(1),
        periods=HORIZON_MOIS,
        freq="MS",
    )
    previsions = pd.DataFrame(
        {
            "mois": futurs,
            "fiabilite": _predire(historique, futurs, modele_retenu),
            "reference": _predire(historique, futurs, "saisonnier"),
        }
    )
    return PrevisionFiabilite(
        liaison=liaison,
        modele=modele_retenu,
        historique=historique,
        previsions=previsions,
        validation=validation,
        test=test.reset_index(drop=True),
        scores_validation=scores,
        mae_test=mae_test,
        mae_reference=mae_reference,
    )
