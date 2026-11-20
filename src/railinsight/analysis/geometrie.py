"""Tracés du réseau ferré : extraction et simplification de lignes GeoJSON.

Les coordonnées suivent l'ordre GeoJSON : (longitude, latitude), en degrés WGS84.
"""

import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

from railinsight.exceptions import DonneesInvalides

Point = tuple[float, float]
Ligne = list[Point]

MOTIF_LGV = r"grande vitesse|\blgv\b"
DECIMALES = 4  # environ 10 m : bien assez précis à l'échelle de la France


def _distance_au_segment(point: Point, debut: Point, fin: Point) -> float:
    """Distance d'un point au segment [debut, fin], en degrés."""
    dx, dy = fin[0] - debut[0], fin[1] - debut[1]
    longueur = dx * dx + dy * dy
    if longueur == 0:
        return math.dist(point, debut)
    t = ((point[0] - debut[0]) * dx + (point[1] - debut[1]) * dy) / longueur
    t = max(0.0, min(1.0, t))
    return math.dist(point, (debut[0] + t * dx, debut[1] + t * dy))


def simplifier(ligne: Ligne, tolerance: float) -> Ligne:
    """Simplifie une ligne par l'algorithme de Douglas-Peucker.

    On garde les deux extrémités, puis, récursivement, le point le plus éloigné
    du segment qui les relie tant que cet écart dépasse la tolérance. Une pile
    remplace la récursion pour ne pas dépasser la profondeur maximale de Python.

    Args:
        ligne: Points de la ligne.
        tolerance: Écart maximal toléré, en degrés (0,002 ≈ 200 m).

    Returns:
        Les points conservés, dans leur ordre d'origine.
    """
    if len(ligne) <= 2:
        return list(ligne)
    garder = [False] * len(ligne)
    garder[0] = garder[-1] = True
    pile = [(0, len(ligne) - 1)]
    while pile:
        debut, fin = pile.pop()
        ecart, indice = 0.0, debut
        for i in range(debut + 1, fin):
            distance = _distance_au_segment(ligne[i], ligne[debut], ligne[fin])
            if distance > ecart:
                ecart, indice = distance, i
        if ecart > tolerance:
            garder[indice] = True
            pile.extend([(debut, indice), (indice, fin)])
    return [point for point, garde in zip(ligne, garder, strict=True) if garde]


def _correspond(proprietes: Mapping[str, Any], motif: str) -> bool:
    """Indique si une valeur texte des propriétés contient le motif."""
    expression = re.compile(motif, re.IGNORECASE)
    return any(
        isinstance(valeur, str) and expression.search(valeur)
        for valeur in proprietes.values()
    )


def _lignes_de(geometrie: Mapping[str, Any] | None) -> Iterable[Ligne]:
    """Renvoie les lignes d'une géométrie LineString ou MultiLineString."""
    if not geometrie:
        return []
    genre, coordonnees = geometrie.get("type"), geometrie.get("coordinates", [])
    if genre == "LineString":
        parties = [coordonnees]
    elif genre == "MultiLineString":
        parties = coordonnees
    else:
        return []
    return [[(float(p[0]), float(p[1])) for p in partie] for partie in parties]


def extraire_lignes(
    collection: Mapping[str, Any], motif: str | None = None
) -> list[Ligne]:
    """Extrait les lignes d'une FeatureCollection GeoJSON.

    Args:
        collection: Contenu GeoJSON déjà décodé.
        motif: Expression régulière cherchée dans les propriétés de chaque
            tronçon ; None garde tous les tronçons.

    Raises:
        DonneesInvalides: Si le contenu n'est pas une FeatureCollection.
    """
    if collection.get("type") != "FeatureCollection":
        raise DonneesInvalides("le fichier du réseau n'est pas une FeatureCollection")
    lignes: list[Ligne] = []
    for troncon in collection.get("features", []):
        proprietes = troncon.get("properties") or {}
        if motif is None or _correspond(proprietes, motif):
            lignes.extend(_lignes_de(troncon.get("geometry")))
    return [ligne for ligne in lignes if len(ligne) >= 2]


def vers_geojson(lignes: Iterable[Ligne], decimales: int = DECIMALES) -> dict[str, Any]:
    """Écrit des lignes dans une FeatureCollection compacte, sans propriétés."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(lon, decimales), round(lat, decimales)]
                        for lon, lat in ligne
                    ],
                },
            }
            for ligne in lignes
        ],
    }
