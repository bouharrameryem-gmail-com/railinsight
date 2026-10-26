"""Tests de la lecture du CSV et du contrat de schéma."""

import logging
import re

import pandas as pd
import pytest

from railinsight.analysis.donnees import NOMBRE, SCHEMA, lire_donnees, normaliser
from railinsight.exceptions import DonneesInvalides

SOURCES = [c.source for c in SCHEMA]
NOMS = [c.nom for c in SCHEMA]
GENRE = {c.source: c.genre for c in SCHEMA}


def valeur(source):
    """Valeur valide pour une colonne du schéma (identifiée par son nom CSV)."""
    return "1" if GENRE.get(source) == NOMBRE else "Paris"


def ecrire_csv(tmp_path, colonnes=None, ligne=None, bom=False):
    """Écrit un CSV de test (séparateur ';') et renvoie son chemin."""
    colonnes = SOURCES if colonnes is None else colonnes
    ligne = [valeur(c) for c in colonnes] if ligne is None else ligne
    texte = ";".join(colonnes) + "\n" + ";".join(ligne) + "\n"
    fichier = tmp_path / "donnees.csv"
    fichier.write_bytes(texte.encode("utf-8-sig" if bom else "utf-8"))
    return fichier


def test_lecture_valide_colonnes_renommees(tmp_path):
    df = lire_donnees(ecrire_csv(tmp_path))
    assert list(df.columns) == NOMS
    assert pd.api.types.is_float_dtype(df["annules"])
    assert df.loc[0, "gare_depart"] == "Paris"


def test_bom_retire_du_nom_de_la_premiere_colonne(tmp_path):
    df = lire_donnees(ecrire_csv(tmp_path, bom=True))
    assert list(df.columns) == NOMS


def test_en_tetes_reconnus_malgre_casse_accents_et_apostrophe(tmp_path):
    alteres = [f"  {c.upper().replace(chr(39), chr(8217))}  " for c in SOURCES]
    df = lire_donnees(ecrire_csv(tmp_path, alteres))
    assert list(df.columns) == NOMS


def test_zeros_initiaux_conserves_dans_les_colonnes_texte(tmp_path):
    ligne = [valeur(c) for c in SOURCES]
    ligne[SOURCES.index("Gare de départ")] = "000123"
    df = lire_donnees(ecrire_csv(tmp_path, SOURCES, ligne))
    assert df.loc[0, "gare_depart"] == "000123"


def test_colonnes_manquantes_toutes_nommees(tmp_path):
    colonnes = [c for c in SOURCES if c not in ("Date", "Service")]
    with pytest.raises(DonneesInvalides, match="colonnes manquantes : Date, Service"):
        lire_donnees(ecrire_csv(tmp_path, colonnes))


def test_colonne_en_plus_ignoree_et_ordre_fixe(tmp_path):
    colonnes = ["Export demain", *reversed(SOURCES)]
    df = lire_donnees(ecrire_csv(tmp_path, colonnes))
    assert list(df.columns) == NOMS


def test_valeur_non_numerique_devient_nan_avec_avertissement(tmp_path, caplog):
    ligne = [valeur(c) for c in SOURCES]
    ligne[SOURCES.index("Nombre de trains annulés")] = "n/d"
    with caplog.at_level(logging.WARNING):
        df = lire_donnees(ecrire_csv(tmp_path, SOURCES, ligne))
    assert df["annules"].isna().all()
    assert "annules" in caplog.text


def test_fichier_vide(tmp_path):
    fichier = tmp_path / "vide.csv"
    fichier.write_bytes(b"")
    with pytest.raises(DonneesInvalides, match="vide") as info:
        lire_donnees(fichier)
    assert isinstance(info.value.__cause__, pd.errors.EmptyDataError)


def test_fichier_absent_leve_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        lire_donnees(tmp_path / "absent.csv")


def test_encodage_non_utf8(tmp_path):
    fichier = tmp_path / "latin1.csv"
    fichier.write_bytes("Gare d'arrivée;Date\nLyon;2024-01\n".encode("cp1252"))
    with pytest.raises(DonneesInvalides, match="encodage"):
        lire_donnees(fichier)


def test_donnees_invalides_est_une_valueerror():
    assert issubclass(DonneesInvalides, ValueError)


def test_schema_sans_doublon_ni_nom_invalide():
    assert len(set(NOMS)) == len(NOMS)
    assert len({normaliser(s) for s in SOURCES}) == len(SOURCES)
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", nom) for nom in NOMS)


def test_normaliser():
    assert normaliser("  Gare d’arrivée ") == "gare d arrivee"
    assert (
        normaliser("Nombre trains en retard > 15min") == "nombre trains en retard 15min"
    )
