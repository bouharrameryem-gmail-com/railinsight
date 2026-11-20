"""Télécharge le tracé des lignes à grande vitesse et l'enregistre, simplifié.

Source : SNCF Réseau, jeu « Lignes LGV et par écartement » (licence ODbL).
On garde les seuls tronçons LGV, on simplifie leur tracé, puis on écrit un
GeoJSON léger que l'application lit sans accès à Internet.

Exemples :
    uv run python scripts/telecharger_reseau_lgv.py
    uv run python scripts/telecharger_reseau_lgv.py --fichier export.geojson
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import requests

from railinsight.analysis.geometrie import (
    MOTIF_LGV,
    extraire_lignes,
    simplifier,
    vers_geojson,
)
from railinsight.config import DATA_DIR

logger = logging.getLogger("railinsight.scripts.reseau_lgv")

SOURCE = (
    "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
    "lignes-lgv-et-par-ecartement/exports/geojson"
)
SORTIE = DATA_DIR / "reference" / "reseau_lgv.geojson"
TOLERANCE = 0.002  # degrés, environ 200 m
DELAI_SECONDES = 120


def telecharger(url: str) -> dict[str, Any]:
    """Télécharge et décode le GeoJSON publié par SNCF Réseau."""
    logger.info("Téléchargement de %s", url)
    reponse = requests.get(url, timeout=DELAI_SECONDES)
    reponse.raise_for_status()
    return reponse.json()


def preparer(collection: dict[str, Any], tolerance: float) -> dict[str, Any]:
    """Garde les tronçons LGV et simplifie leur tracé.

    Raises:
        SystemExit: Si aucun tronçon LGV n'est reconnu.
    """
    lignes = extraire_lignes(collection, MOTIF_LGV)
    if not lignes:
        champs = sorted(
            {
                cle
                for troncon in collection.get("features", [])
                for cle in (troncon.get("properties") or {})
            }
        )
        raise SystemExit(
            "Aucun tronçon LGV reconnu. Champs présents : " + ", ".join(champs)
        )
    simplifiees = [simplifier(ligne, tolerance) for ligne in lignes]
    avant = sum(len(ligne) for ligne in lignes)
    apres = sum(len(ligne) for ligne in simplifiees)
    logger.info("%d tronçons LGV, %d points ramenés à %d", len(lignes), avant, apres)
    return vers_geojson(simplifiees)


def main() -> None:
    """Lit les arguments, prépare le réseau et l'enregistre."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=SOURCE, help="URL du GeoJSON")
    parser.add_argument(
        "--fichier", type=Path, help="GeoJSON déjà téléchargé, à la place de l'URL"
    )
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    parser.add_argument("--tolerance", type=float, default=TOLERANCE)
    arguments = parser.parse_args()

    if arguments.fichier:
        collection = json.loads(arguments.fichier.read_text(encoding="utf-8"))
    else:
        collection = telecharger(arguments.source)
    reseau = preparer(collection, arguments.tolerance)

    arguments.sortie.parent.mkdir(parents=True, exist_ok=True)
    arguments.sortie.write_text(
        json.dumps(reseau, separators=(",", ":")), encoding="utf-8"
    )
    taille = arguments.sortie.stat().st_size / 1024
    logger.info("Réseau enregistré dans %s (%.0f Ko)", arguments.sortie, taille)


if __name__ == "__main__":
    main()
