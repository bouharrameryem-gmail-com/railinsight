"""Indicateurs du réseau TGV pour la page d'accueil."""

import logging
from dataclasses import dataclass

import pandas as pd

from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)

MOIS_PAR_FENETRE = 12
CLE_LIGNE = ["mois", "gare_depart", "gare_arrivee"]
COLONNES_REQUISES = (
    "date",
    "mois",
    "gare_depart",
    "gare_arrivee",
    "liaison",
    "prevus",
    "annules",
    "circules",
    "retards_sup_15min",
)
NOMBRE_DESTINATIONS = 3
# En dessous de ce nombre de trains, le taux d'une liaison est trop instable
# pour la citer parmi les plus touchées d'une gare.
MIN_TRAINS_DESTINATION = 100
# Seuil pour nommer une gare parmi les plus touchées (environ 14 trains par jour) :
# en dessous, une petite gare peut afficher un taux extrême sans être représentative.
MIN_TRAINS_GARE = 5000
# Rayon de regroupement sur la carte, en degrés (0,15 ≈ 15 km) : à l'échelle de
# la France, les gares parisiennes se superposeraient en une seule bulle illisible.
RAYON_REGROUPEMENT = 0.15


@dataclass(frozen=True)
class Fenetre:
    """Période de mois consécutifs, bornes incluses, au format « AAAA-MM »."""

    debut: str
    fin: str


@dataclass(frozen=True)
class TauxReseau:
    """Chiffres du réseau sur une période.

    `trains` compte les trains circulés ; `taux_retard` est la part de ces
    trains arrivés avec plus de 15 minutes de retard ; `taux_annulation` est
    la part des trains prévus qui ont été annulés ; `liaisons` compte les
    liaisons desservies, sans tenir compte du sens.
    """

    trains: int
    taux_retard: float
    taux_annulation: float
    liaisons: int


def preparer_donnees(nettoyees: pd.DataFrame) -> pd.DataFrame:
    """Retire les doublons et les lignes sans train prévu.

    Le fichier SNCF contient des lignes en double (été 2025) : sans ce
    filtre, ces mois compteraient deux fois dans les totaux du réseau. Pour
    chaque doublon, la dernière ligne publiée est conservée.

    Raises:
        DonneesInvalides: Si une colonne nécessaire manque.
    """
    manquantes = [c for c in COLONNES_REQUISES if c not in nettoyees.columns]
    if manquantes:
        raise DonneesInvalides(
            "colonnes manquantes pour l'accueil : " + ", ".join(manquantes)
        )
    uniques = nettoyees.drop_duplicates(subset=CLE_LIGNE, keep="last")
    doublons = len(nettoyees) - len(uniques)
    avec_train = uniques[uniques["prevus"] > 0]
    sans_train = len(uniques) - len(avec_train)
    if doublons or sans_train:
        logger.info(
            "Accueil : %d doublon(s) et %d ligne(s) sans train écartés",
            doublons,
            sans_train,
        )
    return avec_train.reset_index(drop=True)


def fenetres_annuelles(
    mois: pd.Series, taille: int = MOIS_PAR_FENETRE
) -> tuple[Fenetre, Fenetre | None]:
    """Renvoie les `taille` derniers mois et les `taille` mois qui les précèdent.

    Les fenêtres sont calendaires : un mois absent des données reste compté.
    La fenêtre précédente vaut None si les données ne la couvrent pas en entier.

    Raises:
        DonneesInvalides: Si aucun mois n'est disponible.
    """
    connus = mois.dropna()
    if connus.empty:
        raise DonneesInvalides("aucun mois disponible dans les données")
    premier = pd.Period(connus.min(), freq="M")
    fin = pd.Period(connus.max(), freq="M")
    debut = fin - (taille - 1)
    courante = Fenetre(str(debut), str(fin))
    debut_precedent = debut - taille
    if debut_precedent < premier:
        return courante, None
    return courante, Fenetre(str(debut_precedent), str(debut - 1))


def _dans(donnees: pd.DataFrame, fenetre: Fenetre) -> pd.DataFrame:
    """Garde les lignes dont le mois appartient à la fenêtre."""
    mois = donnees["mois"]
    return donnees[(mois >= fenetre.debut) & (mois <= fenetre.fin)]


def _retards_mesures(donnees: pd.DataFrame) -> tuple[float, float]:
    """Renvoie les retards et les trains circulés des lignes où le retard est connu."""
    connus = donnees["retards_sup_15min"].notna()
    return (
        float(donnees.loc[connus, "retards_sup_15min"].sum()),
        float(donnees.loc[connus, "circules"].sum()),
    )


def taux_sur_fenetre(donnees: pd.DataFrame, fenetre: Fenetre) -> TauxReseau:
    """Calcule les chiffres du réseau sur une fenêtre.

    Raises:
        DonneesInvalides: Si aucun train n'a circulé sur la fenêtre.
    """
    periode = _dans(donnees, fenetre)
    retards, mesures = _retards_mesures(periode)
    prevus = float(periode["prevus"].sum())
    if mesures <= 0 or prevus <= 0:
        raise DonneesInvalides(
            f"aucun train mesuré entre {fenetre.debut} et {fenetre.fin}"
        )
    return TauxReseau(
        trains=int(periode["circules"].sum()),
        taux_retard=retards / mesures,
        taux_annulation=float(periode["annules"].sum()) / prevus,
        liaisons=int(periode["liaison"].nunique()),
    )


def un_sur(taux: float) -> int:
    """Traduit un taux en « 1 sur N », plus parlant pour le grand public.

    Examples:
        >>> un_sur(0.11)
        9

    Raises:
        ValueError: Si le taux n'est pas strictement compris entre 0 et 1.
    """
    if not 0 < taux <= 1:
        raise ValueError(f"taux hors de ]0, 1] : {taux}")
    return round(1 / taux)


def ecart_en_points(courant: float, precedent: float) -> float:
    """Renvoie l'écart entre deux taux, en points de pourcentage."""
    return (courant - precedent) * 100


def taux_par_mois(donnees: pd.DataFrame) -> pd.DataFrame:
    """Calcule le taux de retard du réseau pour chaque mois.

    Returns:
        Une ligne par mois : `annee`, `mois_numero` (1 à 12), `taux_retard`.
        Les mois sans retard mesuré sont absents.
    """
    connues = donnees[donnees["retards_sup_15min"].notna()]
    par_mois = connues.groupby("date")[["retards_sup_15min", "circules"]].sum()
    par_mois = par_mois[par_mois["circules"] > 0]
    dates = pd.DatetimeIndex(par_mois.index)
    return pd.DataFrame(
        {
            "annee": dates.year,
            "mois_numero": dates.month,
            "taux_retard": (
                par_mois["retards_sup_15min"] / par_mois["circules"]
            ).to_numpy(),
        }
    )


def mois_le_plus_difficile(par_mois: pd.DataFrame) -> tuple[pd.Period, float]:
    """Renvoie le mois au taux de retard le plus élevé et ce taux.

    Raises:
        DonneesInvalides: Si la table est vide.
    """
    if par_mois.empty:
        raise DonneesInvalides("aucun mois à comparer")
    pire = par_mois.loc[par_mois["taux_retard"].idxmax()]
    periode = pd.Period(
        year=int(pire["annee"]), month=int(pire["mois_numero"]), freq="M"
    )
    return periode, float(pire["taux_retard"])


def taux_par_gare(
    donnees: pd.DataFrame,
    fenetre: Fenetre,
    nombre_destinations: int = NOMBRE_DESTINATIONS,
    minimum_trains: int = MIN_TRAINS_DESTINATION,
) -> pd.DataFrame:
    """Calcule le taux de retard des trains au départ de chaque gare.

    Returns:
        Une ligne par gare de départ : `gare`, `trains`, `taux_retard` et
        `destinations`, un tuple de couples (gare d'arrivée, taux) pour les
        liaisons les plus touchées, triées de la pire à la moins mauvaise.
    """
    periode = _dans(donnees, fenetre)
    connues = periode[periode["retards_sup_15min"].notna()]
    colonnes = ["retards_sup_15min", "circules"]
    gares = connues.groupby("gare_depart")[colonnes].sum()
    gares = gares[gares["circules"] > 0]
    liaisons = connues.groupby(["gare_depart", "gare_arrivee"])[colonnes].sum()
    liaisons = liaisons[liaisons["circules"] >= minimum_trains]
    liaisons = liaisons.assign(
        taux=liaisons["retards_sup_15min"] / liaisons["circules"]
    ).sort_values("taux", ascending=False)

    destinations = {
        gare: tuple(
            (str(arrivee), float(taux))
            for (_, arrivee), taux in groupe["taux"].head(nombre_destinations).items()
        )
        for gare, groupe in liaisons.groupby(level="gare_depart")
    }
    return pd.DataFrame(
        {
            "gare": gares.index.astype(str),
            "trains": gares["circules"].astype(int).to_numpy(),
            "taux_retard": (gares["retards_sup_15min"] / gares["circules"]).to_numpy(),
            "destinations": [destinations.get(gare, ()) for gare in gares.index],
        }
    )


def placer_gares(
    gares: pd.DataFrame, coordonnees: pd.DataFrame
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Ajoute la latitude et la longitude de chaque gare.

    Args:
        gares: Résultat de `taux_par_gare`.
        coordonnees: Table `gare`, `latitude`, `longitude`.

    Returns:
        Les gares placées, et les noms des gares sans coordonnées.
    """
    placees = gares.merge(coordonnees, on="gare", how="left")
    absentes = placees["latitude"].isna() | placees["longitude"].isna()
    return (
        placees[~absentes].reset_index(drop=True),
        tuple(sorted(placees.loc[absentes, "gare"])),
    )


def gares_les_plus_touchees(
    gares: pd.DataFrame, nombre: int, minimum_trains: int = MIN_TRAINS_GARE
) -> pd.DataFrame:
    """Renvoie les gares au taux de retard le plus élevé, parmi les gares actives.

    Une petite gare avec quelques dizaines de trains peut afficher un taux
    extrême sans être représentative : elle n'est pas retenue pour être nommée.
    """
    actives = gares[gares["trains"] >= minimum_trains]
    return actives.nlargest(nombre, "taux_retard").reset_index(drop=True)


def _nom_du_groupe(noms: list[str]) -> str:
    """Nom d'un groupe de gares : leur premier mot commun, sinon la plus grande."""
    premiers = {nom.split()[0] for nom in noms}
    return premiers.pop() if len(premiers) == 1 else noms[0]


def regrouper_gares_proches(
    gares: pd.DataFrame, rayon: float = RAYON_REGROUPEMENT
) -> pd.DataFrame:
    """Fusionne en une seule bulle les gares trop proches pour être distinguées.

    Les gares sont parcourues de la plus fréquentée à la moins fréquentée ;
    chacune rejoint le premier groupe dont la gare principale est à moins de
    `rayon` degrés, sinon elle ouvre un nouveau groupe. Le taux du groupe est
    pondéré par le nombre de trains.

    Args:
        gares: Résultat de `placer_gares`.
        rayon: Distance maximale à la gare principale du groupe, en degrés.

    Returns:
        Les colonnes de `gares`, plus `membres` : un tuple de couples
        (gare, taux) pour les groupes de plusieurs gares, vide sinon.
    """
    triees = gares.sort_values("trains", ascending=False).reset_index(drop=True)
    groupes: list[list[int]] = []
    for indice, gare in triees.iterrows():
        for groupe in groupes:
            principale = triees.loc[groupe[0]]
            ecart = (
                (gare["latitude"] - principale["latitude"]) ** 2
                + (gare["longitude"] - principale["longitude"]) ** 2
            ) ** 0.5
            if ecart <= rayon:
                groupe.append(indice)
                break
        else:
            groupes.append([indice])

    lignes = []
    for groupe in groupes:
        membres = triees.loc[groupe]
        trains = membres["trains"].sum()
        poids = membres["trains"] / trains if trains > 0 else 1 / len(membres)
        lignes.append(
            {
                "gare": _nom_du_groupe(list(membres["gare"])),
                "latitude": float((membres["latitude"] * poids).sum()),
                "longitude": float((membres["longitude"] * poids).sum()),
                "trains": int(trains),
                "taux_retard": float((membres["taux_retard"] * poids).sum()),
                "destinations": membres["destinations"].iloc[0]
                if len(membres) == 1
                else (),
                "membres": ()
                if len(membres) == 1
                else tuple(
                    (str(nom), float(taux))
                    for nom, taux in zip(
                        membres["gare"], membres["taux_retard"], strict=True
                    )
                ),
            }
        )
    return pd.DataFrame(lignes)
