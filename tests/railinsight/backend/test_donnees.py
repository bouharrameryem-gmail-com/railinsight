"""Tests du chargement local et du partage des données nettoyées."""

import os
import time
from unittest.mock import MagicMock

import pandas as pd
import pytest

from railinsight.analysis.nettoyage import nettoyer_regularite
from railinsight.analysis.shema import NOMBRE, SCHEMA
from railinsight.backend import dataloader
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def csv_local(tmp_path, monkeypatch):
    chemin = tmp_path / "source.csv"
    colonnes = [c.source for c in SCHEMA]
    valeurs = ["10" if c.genre == NOMBRE else "PARIS" for c in SCHEMA]
    valeurs[0] = "2026-09"
    valeurs[[c.nom for c in SCHEMA].index("service")] = "National"
    chemin.write_text(
        ";".join(colonnes) + "\n" + ";".join(valeurs) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(dataloader, "RAW_CSV_PATH", chemin)
    monkeypatch.setattr(dataloader, "CLEAN_MONTHLY_PATH", tmp_path / "clean.parquet")
    dataloader.charger_donnees.clear()
    dataloader.charger_donnees_nettoyees.clear()
    yield chemin
    dataloader.charger_donnees.clear()
    dataloader.charger_donnees_nettoyees.clear()


def test_csv_lu_une_fois_et_copies_independantes(csv_local, monkeypatch):
    lecteur = MagicMock(wraps=dataloader.lire_donnees)
    monkeypatch.setattr(dataloader, "lire_donnees", lecteur)
    a = dataloader.charger_donnees()
    a.loc[0, "prevus"] = 0
    b = dataloader.charger_donnees()
    assert b.loc[0, "prevus"] == 10
    assert list(b.columns) == [c.nom for c in SCHEMA]
    lecteur.assert_called_once_with(csv_local)


@pytest.mark.parametrize("contenu", ["", "erreur HTML", "date\ninvalide", None])
def test_csv_inutilisable_signale(csv_local, contenu):
    if contenu is None:
        csv_local.unlink()
    else:
        csv_local.write_text(contenu, encoding="utf-8")
    with pytest.raises(DonneesInvalides):
        dataloader.charger_donnees()


@pytest.mark.parametrize("date", ["invalide", ""])
def test_dates_invalides_refusees(csv_local, date):
    texte = csv_local.read_text(encoding="utf-8").replace("2026-09", date)
    csv_local.write_text(texte, encoding="utf-8")
    with pytest.raises(DonneesInvalides, match="dates invalides"):
        dataloader.charger_donnees()


def test_nettoyage_partage_sans_fichier_prepare(csv_local, monkeypatch):
    nettoyer = MagicMock(wraps=nettoyer_regularite)
    monkeypatch.setattr(dataloader, "nettoyer_regularite", nettoyer)
    a = dataloader.charger_donnees_nettoyees()
    a.loc[0, "gare_depart"] = "MODIFIE"
    b = dataloader.charger_donnees_clean()
    assert b.loc[0, "gare_depart"] == "PARIS"
    assert b.loc[0, "mois"] == "2026-09"
    assert pd.api.types.is_datetime64_any_dtype(b["date"])
    assert nettoyer.call_count == 1


@pytest.mark.parametrize("perime", [False, True])
def test_parquet_reutilise_uniquement_si_a_jour(csv_local, monkeypatch, perime):
    attendu = nettoyer_regularite(dataloader.charger_donnees())
    attendu.to_parquet(dataloader.CLEAN_MONTHLY_PATH, index=False)
    futur = time.time() + 10
    os.utime(dataloader.CLEAN_MONTHLY_PATH, (futur, futur))
    if perime:
        os.utime(csv_local, (futur + 10, futur + 10))
    nettoyer = MagicMock(wraps=nettoyer_regularite)
    monkeypatch.setattr(dataloader, "nettoyer_regularite", nettoyer)
    resultat = dataloader.charger_donnees_nettoyees()
    pd.testing.assert_frame_equal(resultat, attendu)
    assert nettoyer.call_count == int(perime)


def test_parquet_corrompu_signale(csv_local):
    dataloader.CLEAN_MONTHLY_PATH.write_bytes(b"parquet invalide")
    futur = time.time() + 10
    os.utime(dataloader.CLEAN_MONTHLY_PATH, (futur, futur))
    with pytest.raises(DonneesInvalides, match="Régénérez"):
        dataloader.charger_donnees_nettoyees()
