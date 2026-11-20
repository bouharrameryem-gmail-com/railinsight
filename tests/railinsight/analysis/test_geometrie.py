"""Tests de l'extraction et de la simplification des tracés du réseau."""

import pytest

from railinsight.analysis.geometrie import (
    MOTIF_LGV,
    extraire_lignes,
    simplifier,
    vers_geojson,
)
from railinsight.exceptions import DonneesInvalides


def _troncon(categorie, geometrie):
    return {
        "type": "Feature",
        "properties": {"catlig": categorie},
        "geometry": geometrie,
    }


COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        _troncon(
            "Ligne à grande vitesse",
            {"type": "LineString", "coordinates": [[2.0, 48.0], [3.0, 47.0]]},
        ),
        _troncon(
            "LGV",
            {
                "type": "MultiLineString",
                "coordinates": [[[4.0, 45.0], [5.0, 44.0]], [[5.0, 44.0], [5.4, 43.3]]],
            },
        ),
        _troncon(
            "Ligne à écartement normal",
            {"type": "LineString", "coordinates": [[0.0, 46.0], [1.0, 46.0]]},
        ),
        _troncon("Ligne à grande vitesse", {"type": "Point", "coordinates": [1, 2]}),
        _troncon("Ligne à grande vitesse", None),
    ],
}


def test_simplifier_retire_les_points_alignes():
    ligne = [(0.0, 0.0), (1.0, 0.0001), (2.0, 0.0), (3.0, 0.0)]
    assert simplifier(ligne, tolerance=0.01) == [(0.0, 0.0), (3.0, 0.0)]


def test_simplifier_garde_les_virages():
    ligne = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]
    assert simplifier(ligne, tolerance=0.1) == ligne


def test_simplifier_lignes_courtes_et_points_confondus():
    assert simplifier([(1.0, 1.0)], 0.1) == [(1.0, 1.0)]
    assert simplifier([(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)], 0.1) == [
        (0.0, 0.0),
        (0.0, 0.0),
    ]


def test_extraire_les_seules_lgv():
    lignes = extraire_lignes(COLLECTION, MOTIF_LGV)
    assert len(lignes) == 3
    assert lignes[0] == [(2.0, 48.0), (3.0, 47.0)]


def test_extraire_tout_sans_motif():
    assert len(extraire_lignes(COLLECTION)) == 4


def test_extraire_refuse_un_autre_format():
    with pytest.raises(DonneesInvalides):
        extraire_lignes({"type": "Feature"})


def test_vers_geojson_arrondit_et_relit():
    collection = vers_geojson([[(2.123456, 48.987654), (3.0, 47.0)]], decimales=2)

    assert collection["features"][0]["geometry"]["coordinates"][0] == [2.12, 48.99]
    assert extraire_lignes(collection) == [[(2.12, 48.99), (3.0, 47.0)]]
