"""Nettoyage des données de régularité : fonctions pures, idempotentes, vectorisées.

Deux familles de fonctions :

- des outils génériques, utilisables sur n'importe quelle colonne
  (normaliser_nom, convertir_mois, taux, invalider_hors_bornes, retirer_doublons,
  filtrer_periode, retirer_sans_train) ;

Chaque fonction ne modifie pas son argument, accepte sa propre sortie
(f(f(x)) == f(x)) et n'utilise aucune boucle Python. Les données arrivent de
railinsight.analysis.donnees.lire_donnees, avec les noms de colonnes du SCHEMA.
"""

import logging

import pandas as pd

from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

# Espaces ordinaires + insécable (U+00A0) + fine insécable (U+202F). Le motif contient
# les vrais caractères : pandas 3 utilise pyarrow, dont le moteur refuse « \u00a0 ».
ESPACES = "[\\s\u00a0\u202f]+"
COLONNES_REQUISES = (
    "date",
    "gare_depart",
    "gare_arrivee",
    "prevus",
    "annules",
    "retard_moyen_arrivee",
)


# ---------- outils génériques ----------


def normaliser_nom(serie: pd.Series) -> pd.Series:
    """Texte sans espaces superflus, en MAJUSCULES (la convention du fichier source).

    « Lyon  part-dieu » devient « LYON PART-DIEU ». La mise en forme pour
    l'affichage (« Lyon Part-Dieu ») est l'affaire de la couche viz.
    """
    return serie.str.replace(ESPACES, " ", regex=True).str.strip().str.upper()


def convertir_mois(serie: pd.Series) -> pd.Series:
    """Mois « AAAA-MM » en date (premier jour du mois) ; illisible : NaT.

    Accepte une série déjà convertie. Les valeurs devenues illisibles sont comptées.
    """
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    texte = serie.astype("string").str.strip()
    dates = pd.to_datetime(texte, format="%Y-%m", errors="coerce")
    perdues = int(dates.isna().sum() - serie.isna().sum())
    if perdues:
        logger.warning("%d mois illisible(s) remplacé(s) par NaT", perdues)
    return dates


def taux(
    numerateur: pd.Series, denominateur: pd.Series, pour: float = 100.0
) -> pd.Series:
    """Rapport multiplié par `pour` (100 : pourcentage) ; dénominateur nul : NaN.

    Évite la division par zéro : 0 train prévu ne donne ni infini ni erreur.
    """
    return numerateur / denominateur.where(denominateur != 0) * pour


def invalider_hors_bornes(
    serie: pd.Series, minimum: float | None = None, maximum: float | None = None
) -> pd.Series:
    """Remplace par NaN les valeurs hors de [minimum, maximum] ; la ligne est gardée.

    Les valeurs manquantes restent manquantes. Le nombre de valeurs remplacées est
    journalisé : chaque analyse décide elle-même de ses bornes.
    """
    hors = pd.Series(False, index=serie.index)
    if minimum is not None:
        hors |= serie < minimum
    if maximum is not None:
        hors |= serie > maximum
    if hors.any():
        logger.warning(
            "colonne %r : %d valeur(s) hors de [%s, %s] remplacée(s) par NaN",
            serie.name,
            int(hors.sum()),
            minimum,
            maximum,
        )
    return serie.mask(hors)


def retirer_doublons(df: pd.DataFrame, cle: list[str]) -> pd.DataFrame:
    """Une ligne par clé : la dernière du fichier gagne."""
    unique = df.drop_duplicates(subset=cle, keep="last").reset_index(drop=True)
    retirees = len(df) - len(unique)
    if retirees:
        logger.warning(
            "%d ligne(s) en double retirée(s) (clé : %s)", retirees, ", ".join(cle)
        )
    return unique


def filtrer_periode(
    df: pd.DataFrame,
    debut: str | None = None,
    fin: str | None = None,
    colonne: str = "mois",
) -> pd.DataFrame:
    """Garde les lignes dont le mois est entre `debut` et `fin` (« AAAA-MM », inclus).

    None = pas de borne. Une ligne sans mois est écartée dès qu'une borne est donnée.
    """
    garder = pd.Series(True, index=df.index)
    if debut:
        garder &= df[colonne] >= debut
    if fin:
        garder &= df[colonne] <= fin
    return df[garder].reset_index(drop=True)


# ---------- règles propres au jeu de données ----------


def ajouter_liaison(
    df: pd.DataFrame, depart: str = "gare_depart", arrivee: str = "gare_arrivee"
) -> pd.DataFrame:
    """Ajoute gare_a, gare_b (ordre alphabétique) et liaison (« A - B »).

    Une liaison est une paire de gares dont l'ordre n'a pas d'importance :
    Paris -> Lyon et Lyon -> Paris donnent la même gare_a, gare_b et liaison.
    """
    resultat = df.copy()
    a_avant = df[depart] <= df[arrivee]
    resultat["gare_a"] = df[depart].where(a_avant, df[arrivee])
    resultat["gare_b"] = df[arrivee].where(a_avant, df[depart])
    resultat["liaison"] = resultat["gare_a"] + " - " + resultat["gare_b"]
    return resultat


def ajouter_minutes_retard(
    df: pd.DataFrame, retard_moyen: str = "retard_moyen_arrivee"
) -> pd.DataFrame:
    """Ajoute circules, minutes_retard et circules_mesures pour additionner des mois.

    La somme de moyennes n'est pas une moyenne : on reconvertit chaque retard
    moyen en minutes (moyenne x trains circulés), on additionne les minutes et
    les trains, puis on divise à la fin.

    `circules_mesures` ne compte que les trains dont le retard est connu : pour une
    moyenne, divisez minutes_retard par circules_mesures et non par circules, sinon
    une ligne au retard manquant fausserait le résultat.
    """
    resultat = df.copy()
    resultat["circules"] = resultat["prevus"] - resultat["annules"]
    resultat["minutes_retard"] = resultat[retard_moyen] * resultat["circules"]
    resultat["circules_mesures"] = resultat["circules"].where(
        resultat["minutes_retard"].notna()
    )
    return resultat


def retirer_sans_train(df: pd.DataFrame, colonne: str = "prevus") -> pd.DataFrame:
    """Retire les lignes sans train prévu (prevus <= 0 ou manquant).

    À appeler explicitement : c'est une décision d'analyse, utile quand on calcule
    des taux, inutile quand on additionne des volumes.
    """
    sans_train = ~(df[colonne] > 0)
    if sans_train.any():
        logger.info("%d ligne(s) sans train prévu retirée(s)", int(sans_train.sum()))
    return df[~sans_train].reset_index(drop=True)


def _exiger_colonnes(df: pd.DataFrame, colonnes: tuple[str, ...]) -> None:
    """Nomme toutes les colonnes manquantes d'un coup (pas un KeyError isolé)."""
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise DonneesInvalides(
            "colonnes manquantes pour le nettoyage : " + ", ".join(manquantes)
        )


def nettoyer_regularite(brut: pd.DataFrame) -> pd.DataFrame:
    """Applique les règles communes, dans l'ordre ; ne modifie pas l'argument.

    Ne supprime aucune ligne : retirer des lignes est une décision d'analyse, qui
    revient à chacun (retirer_sans_train, filtrer_periode, un filtre sur `service`).

    1. `date` convertie en vraie date, `mois` en texte « AAAA-MM » ;
    2. noms de gares normalisés (espaces, MAJUSCULES) ;
    3. les lignes en double sur (mois, gare_depart, gare_arrivee) sont signalées,
       pas supprimées : le fichier peut légitimement en contenir ;
    4. ajout de liaison, gare_a, gare_b, circules, minutes_retard et
       circules_mesures.
    """
    _exiger_colonnes(brut, COLONNES_REQUISES)
    df = brut.copy()
    df["date"] = convertir_mois(df["date"])
    df["mois"] = df["date"].dt.strftime("%Y-%m")
    for colonne in ("gare_depart", "gare_arrivee"):
        df[colonne] = normaliser_nom(df[colonne])

    doublons = int(df.duplicated(subset=["mois", "gare_depart", "gare_arrivee"]).sum())
    if doublons:
        logger.warning(
            "%d ligne(s) en double sur (mois, gare_depart, gare_arrivee), conservées",
            doublons,
        )

    return ajouter_minutes_retard(ajouter_liaison(df))
