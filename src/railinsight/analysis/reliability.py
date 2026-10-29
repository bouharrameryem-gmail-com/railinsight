"""Fiabilité des liaisons TGV (question 1 du projet).

Porte la logique du notebook ``notebooks/01_liaisons_moins_fiables.ipynb``
dans le package pour réutilisation par la webapp Streamlit. Un train est
considéré en incident le mois où il est annulé ou arrive avec plus de 15
minutes de retard.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from railinsight.analysis.donnees import lire_donnees
from railinsight.analysis.nettoyage import nettoyer_regularite, retirer_sans_train
from railinsight.config import Config, charger_config


def load_data(chemin: Path | None = None, cfg: Config | None = None) -> pd.DataFrame:
    """Lit et nettoie le CSV de régularité (règles communes du projet).

    Args:
        chemin: Chemin du CSV. Par défaut ``cfg.chemins.donnees``.
        cfg: Configuration. Chargée depuis ``config/defaut.yaml`` si omise.

    Returns:
        Le DataFrame nettoyé, une ligne par mois x liaison orientée.
    """
    cfg = cfg or charger_config()
    return nettoyer_regularite(lire_donnees(chemin or cfg.chemins.donnees))


def build_route_incidents(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le taux d'incidents par liaison et par mois.

    Les lignes sans train prévu sont retirées pour éviter une division par
    zéro (voir DATASHEET.md).

    Args:
        df: DataFrame renvoyé par :func:`load_data`.

    Returns:
        Un DataFrame avec les colonnes ``route``, ``date``, ``month``,
        ``planned``, ``cancelled``, ``late15``, ``incidents`` et ``rate``.
    """
    df = retirer_sans_train(df)
    work = pd.DataFrame(
        {
            "route": df["gare_depart"] + " → " + df["gare_arrivee"],
            "date": df["date"],
            "planned": df["prevus"],
            "cancelled": df["annules"],
            "late15": df["retards_sup_15min"],
        }
    )
    work["incidents"] = work["cancelled"] + work["late15"]
    work["rate"] = work["incidents"] / work["planned"]
    work["month"] = work["date"].dt.to_period("M")
    return work


def rank_routes(work: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Classe les liaisons par taux d'incidents sur toute la période.

    Args:
        work: Sortie de :func:`build_route_incidents`.
        top_n: Nombre de liaisons les moins fiables à conserver.

    Returns:
        DataFrame indexé par ``route`` (``planned``, ``incidents``,
        ``rate``), trié par taux décroissant, limité à ``top_n`` lignes.
    """
    ranking = (
        work.groupby("route")
        .agg(planned=("planned", "sum"), incidents=("incidents", "sum"))
        .assign(rate=lambda d: d["incidents"] / d["planned"])
        .sort_values("rate", ascending=False)
    )
    return ranking.head(top_n)


def compute_monthly_rates(work: pd.DataFrame) -> pd.DataFrame:
    """Agrège le taux d'incidents par liaison et par mois.

    Args:
        work: Sortie de :func:`build_route_incidents`.

    Returns:
        DataFrame avec une ligne par (``route``, ``month``) et les colonnes
        ``planned``, ``incidents``, ``rate``.
    """
    monthly = work.groupby(["route", "month"], as_index=False).agg(
        planned=("planned", "sum"), incidents=("incidents", "sum")
    )
    monthly["rate"] = monthly["incidents"] / monthly["planned"]
    return monthly


def _trend_slope(group: pd.DataFrame) -> float:
    """Pente (taux/mois) d'une régression linéaire taux ~ t ; NaN si un seul point."""
    if group["t"].nunique() < 2:
        return np.nan
    slope, _ = np.polyfit(group["t"], group["rate"], 1)
    return slope


def compute_trend_slopes(
    monthly: pd.DataFrame, covid_start: str, covid_end: str
) -> pd.DataFrame:
    """Calcule la pente de tendance du taux d'incidents par liaison.

    La période COVID est exclue de la régression (choc exceptionnel, non
    structurel) mais reste présente dans la série mensuelle affichée.

    Args:
        monthly: Sortie de :func:`compute_monthly_rates`.
        covid_start: Premier mois (``YYYY-MM``) exclu de la régression.
        covid_end: Dernier mois (``YYYY-MM``) exclu de la régression.

    Returns:
        DataFrame indexé par ``route`` avec une colonne ``slope`` (NaN si
        une liaison a moins de deux points hors période COVID).
    """
    monthly = monthly.copy()
    base_month = monthly["month"].min()
    monthly["t"] = (monthly["month"] - base_month).apply(lambda p: p.n)

    covid_start_p = pd.Period(covid_start, freq="M")
    covid_end_p = pd.Period(covid_end, freq="M")
    monthly_for_trend = monthly[~monthly["month"].between(covid_start_p, covid_end_p)]

    return (
        monthly_for_trend.groupby("route")
        .apply(_trend_slope, include_groups=False)
        .rename("slope")
        .to_frame()
    )


@dataclass
class ReliabilityReport:
    """Résultats pré-calculés pour les pages de fiabilité des liaisons (Q1)."""

    ranking: pd.DataFrame
    monthly: pd.DataFrame
    covid_start: pd.Period
    covid_end: pd.Period


def build_reliability_report(
    df: pd.DataFrame | None = None, cfg: Config | None = None
) -> ReliabilityReport:
    """Exécute le pipeline d'analyse complet de la question 1.

    Args:
        df: DataFrame nettoyé. Chargé via :func:`load_data` si omis.
        cfg: Configuration (section ``liaisons_fiabilite``). Chargée depuis
            ``config/defaut.yaml`` si omise.

    Returns:
        Un :class:`ReliabilityReport` contenant le classement (avec pente et
        direction de tendance) et la série mensuelle des liaisons classées.
    """
    cfg = cfg or charger_config()
    p = cfg.liaisons_fiabilite
    data = df if df is not None else load_data(cfg=cfg)
    work = build_route_incidents(data)
    ranking = rank_routes(work, top_n=p.top_n)
    monthly = compute_monthly_rates(work)
    trends = compute_trend_slopes(monthly, p.covid_debut, p.covid_fin)

    ranking = ranking.join(trends)
    ranking["tendance"] = np.where(ranking["slope"] > 0, "se dégrade", "s'améliore")

    monthly_top = monthly[monthly["route"].isin(ranking.index)]

    return ReliabilityReport(
        ranking=ranking,
        monthly=monthly_top,
        covid_start=pd.Period(p.covid_debut, freq="M"),
        covid_end=pd.Period(p.covid_fin, freq="M"),
    )
