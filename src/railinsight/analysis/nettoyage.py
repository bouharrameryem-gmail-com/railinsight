"""Nettoyage du DataFrame renvoyé par `lire_donnees`.

Chaque règle est une fonction pure : elle ne modifie pas son entrée, elle est
idempotente (l'appliquer deux fois donne le même résultat que l'appliquer une
fois) et vectorisée. `nettoyer` les enchaîne.

"""

import logging

import pandas as pd

from railinsight.analysis.donnees import NOMBRE, SCHEMA
from railinsight.exceptions import ConfigInvalide, DonneesInvalides

logger = logging.getLogger(__name__)

# Traitements possibles d'une valeur négative (impossible pour un compte ou un retard).
MODES_NEGATIFS = ("nan", "garder", "supprimer")

COLONNES_NOMBRES = tuple(c.nom for c in SCHEMA if c.genre == NOMBRE)


def normaliser_gare(serie: pd.Series) -> pd.Series:
    """Espaces réduits, casse « Titre » : « PARIS  LYON » -> « Paris Lyon »."""
    return serie.str.split().str.join(" ").str.title()


def convertir_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit `date` (texte AAAA-MM) en datetime et ajoute `mois` (texte AAAA-MM).

    `date` vaut le premier jour du mois. Les lignes sans date valide sont retirées.
    """
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m", errors="coerce")
    invalides = df["date"].isna()
    if invalides.any():
        logger.warning("%d ligne(s) sans date valide retirée(s)", invalides.sum())
        df = df[~invalides].copy()
    df["mois"] = df["date"].dt.strftime("%Y-%m")
    return df


def normaliser_gares(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les noms de gares et ajoute la liaison non orientée.

    Ajoute `gare_a` et `gare_b` (les deux gares dans l'ordre alphabétique, donc
    Paris -> Lyon et Lyon -> Paris donnent la même liaison) et `liaison`
    (« gare_a - gare_b »). Les lignes sans nom de gare sont retirées.
    """
    df = df.copy()
    for colonne in ("gare_depart", "gare_arrivee"):
        df[colonne] = normaliser_gare(df[colonne])

    sans_gare = (
        df["gare_depart"].isna()
        | df["gare_arrivee"].isna()
        | (df["gare_depart"] == "")
        | (df["gare_arrivee"] == "")
    )
    if sans_gare.any():
        logger.warning("%d ligne(s) sans nom de gare retirée(s)", sans_gare.sum())
        df = df[~sans_gare].copy()

    depart, arrivee = df["gare_depart"], df["gare_arrivee"]
    df["gare_a"] = depart.where(depart <= arrivee, arrivee)
    df["gare_b"] = arrivee.where(depart <= arrivee, depart)
    df["liaison"] = df["gare_a"] + " - " + df["gare_b"]
    return df


def retirer_sans_circulation(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les lignes sans train prévu (`prevus` nul ou manquant).

    Elles rendraient tout taux impossible à calculer (division par zéro).
    """
    sans_train = ~(df["prevus"] > 0)
    if sans_train.any():
        logger.warning("%d ligne(s) sans train prévu retirée(s)", sans_train.sum())
    return df[~sans_train].copy()


def traiter_negatifs(df: pd.DataFrame, mode: str = "nan") -> pd.DataFrame:
    """Traite les valeurs négatives des colonnes numériques (impossibles).

    Args:
        df: données lues.
        mode: "nan" met ces valeurs à NaN ; "garder" les conserve ; "supprimer"
            retire la ligne entière.

    Returns:
        Un DataFrame avec une colonne booléenne `anomalie_negative` : vraie pour
        les lignes qui avaient au moins une valeur négative, quel que soit le mode.

    Raises:
        ConfigInvalide: mode inconnu.
    """
    if mode not in MODES_NEGATIFS:
        raise ConfigInvalide(
            f"mode inconnu pour les valeurs négatives : {mode!r} "
            f"(attendu : {', '.join(MODES_NEGATIFS)})"
        )
    df = df.copy()
    colonnes = list(COLONNES_NOMBRES)
    negatifs = df[colonnes] < 0
    par_colonne = negatifs.sum()
    par_colonne = par_colonne[par_colonne > 0]
    if not par_colonne.empty:
        detail = ", ".join(f"{nom}={n}" for nom, n in par_colonne.items())
        logger.warning("valeurs négatives (mode %s) : %s", mode, detail)

    ligne = negatifs.any(axis=1)
    if "anomalie_negative" in df.columns:
        ligne = ligne | df["anomalie_negative"].astype(bool)
    df["anomalie_negative"] = ligne

    if mode == "nan":
        df[colonnes] = df[colonnes].mask(negatifs)
    elif mode == "supprimer":
        df = df[~negatifs.any(axis=1)].copy()
    return df


def ajouter_indicateurs(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes dérivées communes à toutes les analyses.

    - `circules` : trains partis (prévus - annulés, jamais négatif) ;
    - `taux_annulation` : annulés / prévus, en % ;
    - `minutes_retard` : retard moyen à l'arrivée x trains circulés. C'est ce
      total qu'on additionne : une somme de moyennes n'est pas une moyenne ;
    - `circules_mesures` : trains circulés dont le retard est connu. C'est le
      bon dénominateur d'un retard moyen (le retard peut être NaN).
    """
    df = df.copy()
    df["circules"] = (df["prevus"] - df["annules"]).clip(lower=0)
    df["taux_annulation"] = df["annules"] / df["prevus"] * 100
    df["minutes_retard"] = df["retard_moyen_arrivee"] * df["circules"]
    df["circules_mesures"] = df["circules"].where(
        df["retard_moyen_arrivee"].notna(), 0.0
    )
    return df


def nettoyer(df: pd.DataFrame, negatifs: str = "nan") -> pd.DataFrame:
    """Applique toutes les règles de nettoyage, dans l'ordre.

    Args:
        df: DataFrame renvoyé par `lire_donnees`.
        negatifs: traitement des valeurs négatives (voir `traiter_negatifs`).

    Returns:
        Un nouveau DataFrame trié par date et liaison, avec les colonnes de
        `lire_donnees` plus `mois`, `gare_a`, `gare_b`, `liaison`,
        `anomalie_negative`, `circules`, `taux_annulation`, `minutes_retard`
        et `circules_mesures`.

    Raises:
        DonneesInvalides: colonnes de `lire_donnees` manquantes.
        ConfigInvalide: mode `negatifs` inconnu.
    """
    manquantes = [c.nom for c in SCHEMA if c.nom not in df.columns]
    if manquantes:
        raise DonneesInvalides("colonnes manquantes : " + ", ".join(manquantes))

    propre = (
        df.pipe(convertir_dates)
        .pipe(normaliser_gares)
        .pipe(retirer_sans_circulation)
        .pipe(traiter_negatifs, mode=negatifs)
        .pipe(ajouter_indicateurs)
        .sort_values(["date", "gare_depart", "gare_arrivee"], kind="stable")
        .reset_index(drop=True)
    )
    logger.info("nettoyage : %d ligne(s) lues, %d conservées", len(df), len(propre))
    return propre


def diagnostiquer(df: pd.DataFrame) -> dict[str, int]:
    """Compte les anomalies d'un DataFrame lu, sans rien modifier.

    À lancer sur la sortie de `lire_donnees` (avant `nettoyer`), pour vérifier que
    la DATASHEET décrit bien le fichier courant.
    """
    rapport = {
        "lignes": len(df),
        "mois_distincts": int(df["date"].nunique()),
        "prevus_nul_ou_manquant": int((~(df["prevus"] > 0)).sum()),
        "annules_superieur_prevus": int((df["annules"] > df["prevus"]).sum()),
        "doublons_date_depart_arrivee": int(
            df.duplicated(["date", "gare_depart", "gare_arrivee"]).sum()
        ),
    }
    for nom in COLONNES_NOMBRES:
        n = int((df[nom] < 0).sum())
        if n:
            rapport[f"negatif_{nom}"] = n
    return rapport
