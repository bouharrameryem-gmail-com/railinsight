import pandas as pd
import pytest
from railinsight.analysis.shema import NOMBRE, SCHEMA

@pytest.fixture
def donnees_fiabilite():
    """Petit réseau avec deux mois, les deux sens et deux services."""
    return pd.DataFrame(
        [
            ("2024-01", "National", "Paris", "Lyon", 100, 0, 2.0),
            ("2024-01", "National", "Lyon", "Paris", 300, 12, 6.0),
            ("2024-02", "National", "Paris", "Lyon", 1000, 0, 1.0),
            ("2024-01", "International", "Paris", "Bruxelles", 200, 0, 0.0),
            ("2024-01", "National", "Lyon", "Bruxelles", 10, 0, 1.0),
            ("2024-01", "National", "Lyon", "Lille", 200, 0, float("nan")),
        ],
        columns=[
            "date",
            "service",
            "gare_depart",
            "gare_arrivee",
            "prevus",
            "annules",
            "retard_moyen_arrivee",
        ],
    )


@pytest.fixture
def raw():
    cols = [
        "prct_cause_infrastructure",
        "prct_cause_trafic",
        "prct_cause_materiel",
        "prct_cause_gare",
        "prct_cause_voyageurs",
        "prct_cause_externe",
    ]
    rows = [
        ("2024-01", "National", "PARIS", 100, [30, 10, 20, 10, 20, 10]),
        ("2024-02", "National", "PARIS", 50, [100, 0, 0, 0, 0, 0]),
        ("2024-01", "National", "LYON", 10, [0, 0, 0, 0, 0, 100]),
        ("2020-03", "National", "PARIS", 999, [100, 0, 0, 0, 0, 0]),
        ("2024-01", "International", "PARIS", 999, [100, 0, 0, 0, 0, 0]),
    ]
    return pd.DataFrame(
        [
            {
                "date": d,
                "service": s,
                "gare_depart": g,
                "retards_arrivee": r,
                **dict(zip(cols, p, strict=True)),
            }
            for d, s, g, r, p in rows
        ]
    )



LIGNES_RESEAU = [
    ("PARIS LYON", "LYON PART DIEU", 1000, 10, 50, 99),
    ("LYON PART DIEU", "PARIS LYON", 500, 0, 50, 100),
    ("PARIS LYON", "MARSEILLE ST CHARLES", 200, 0, 30, 60),
    ("GARE INCONNUE", "PARIS LYON", 100, 0, 10, 10),
]
CAUSES_RESEAU = {
    "prct_cause_infrastructure": 40.0,
    "prct_cause_trafic": 10.0,
    "prct_cause_materiel": 10.0,
    "prct_cause_gare": 20.0,
    "prct_cause_voyageurs": 10.0,
    "prct_cause_externe": 10.0,
}


def _ligne_reseau(mois, service, depart, arrivee, prevus, annules, retards):
    """Une ligne au format de `lire_donnees`, colonnes inutiles laissées vides."""
    ligne = {colonne.nom: float("nan") for colonne in SCHEMA if colonne.genre == NOMBRE}
    ligne.update(
        {
            "date": mois,
            "service": service,
            "gare_depart": depart,
            "gare_arrivee": arrivee,
            "prevus": float(prevus),
            "annules": float(annules),
            "retards_sup_15min": float(retards),
            "retards_arrivee": float(retards),
            "retard_moyen_arrivee": 5.0,
            **CAUSES_RESEAU,
        }
    )
    return ligne


@pytest.fixture
def brut_reseau():
    """Deux ans de données : 2024 plus en retard que 2023, juillet 2024 le pire.

    S'y ajoutent une ligne en double, une ligne internationale et une ligne
    sans train prévu, que l'accueil doit écarter.
    """
    lignes = []
    for annee in (2023, 2024):
        for numero in range(1, 13):
            mois = f"{annee}-{numero:02d}"
            for depart, arrivee, prevus, annules, r2023, r2024 in LIGNES_RESEAU:
                retards = r2023 if annee == 2023 else r2024
                if (mois, depart) == ("2024-07", "LYON PART DIEU"):
                    retards *= 2
                lignes.append(
                    _ligne_reseau(
                        mois, "National", depart, arrivee, prevus, annules, retards
                    )
                )
    lignes.append(dict(lignes[-1]))
    lignes.append(
        _ligne_reseau("2024-01", "International", "PARIS LYON", "MILAN", 100, 0, 90)
    )
    lignes.append(
        _ligne_reseau("2024-01", "National", "PARIS LYON", "DIJON VILLE", 0, 0, 0)
    )
    return pd.DataFrame(lignes)


@pytest.fixture
def coordonnees_reseau():
    """Coordonnées de toutes les gares sauf GARE INCONNUE."""
    return pd.DataFrame(
        {
            "gare": ["PARIS LYON", "LYON PART DIEU", "MARSEILLE ST CHARLES"],
            "latitude": [48.8443, 45.7606, 43.3027],
            "longitude": [2.3743, 4.8594, 5.3805],
        }
    )