"""Tests hors réseau de l'API du site et de son dernier instantané valide."""

from datetime import UTC
from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from railinsight.analysis.shema import NOMBRE, SCHEMA
from railinsight.backend import dataloader
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def api(monkeypatch):
    colonnes = [c.source for c in SCHEMA]
    valeurs = ["10" if c.genre == NOMBRE else "PARIS" for c in SCHEMA]
    valeurs[0] = "2026-09"
    texte = ";".join(colonnes) + "\n" + ";".join(valeurs) + "\n"
    reponse = MagicMock()
    reponse.content = texte.encode("utf-8-sig")
    reponse.__enter__.return_value = reponse
    get = MagicMock(return_value=reponse)
    monkeypatch.setattr(dataloader.requests, "get", get)
    monkeypatch.setattr(dataloader, "_CACHE", dataloader.CacheAPI())
    return get, reponse


def test_api_complete_validee_et_csv_local_jamais_lu(api, monkeypatch):
    get, _ = api
    vrai_lecteur = dataloader.lire_donnees

    def lecteur(flux):
        assert hasattr(flux, "read")
        return vrai_lecteur(flux)

    monkeypatch.setattr(dataloader, "lire_donnees", lecteur)
    resultat = dataloader.charger_instantane()
    assert resultat.dernier_mois == "2026-09"
    assert resultat.erreur is None
    assert resultat.recupere_le.tzinfo == UTC
    assert list(resultat.donnees.columns) == [c.nom for c in SCHEMA]
    assert resultat.donnees["prevus"].tolist() == [10.0]
    get.assert_called_once_with(
        dataloader.URL_API,
        params={"lang": "fr", "use_labels": "true", "delimiter": ";"},
        timeout=(10, 60),
    )


def test_cache_partage_ne_retourne_pas_un_dataframe_mutable(api):
    get, _ = api
    a = dataloader.charger_donnees()
    a.loc[0, "prevus"] = 0
    b = dataloader.charger_donnees()
    assert b.loc[0, "prevus"] == 10
    assert get.call_count == 1


def test_expiration_actualise_apres_une_heure(api, monkeypatch):
    get, _ = api
    temps = [0.0]
    monkeypatch.setattr(dataloader.time, "monotonic", lambda: temps[0])
    ancien = dataloader.charger_instantane()
    temps[0] = 3599
    assert dataloader.charger_instantane().recupere_le == ancien.recupere_le
    assert get.call_count == 1
    temps[0] = 3600
    dataloader.charger_instantane()
    assert get.call_count == 2


@pytest.mark.parametrize(
    "erreur", [requests.Timeout("delai"), requests.HTTPError("503")]
)
def test_panne_initiale_explicite_et_reessai_differe(api, monkeypatch, erreur):
    get, _ = api
    temps = [0.0]
    monkeypatch.setattr(dataloader.time, "monotonic", lambda: temps[0])
    get.side_effect = erreur
    for _ in range(2):
        with pytest.raises(DonneesInvalides, match="Aucun instantané API valide"):
            dataloader.charger_donnees()
    assert get.call_count == 1
    temps[0] = 300
    get.side_effect = None
    assert len(dataloader.charger_donnees()) == 1
    assert get.call_count == 2


def test_panne_conserve_dernier_jeu_valide_et_signale_retablissement(api, monkeypatch):
    get, _ = api
    temps = [0.0]
    monkeypatch.setattr(dataloader.time, "monotonic", lambda: temps[0])
    ancien = dataloader.charger_instantane()
    temps[0] = 3600
    get.side_effect = requests.ConnectionError("hors ligne")
    repli = dataloader.charger_instantane()
    assert repli.erreur
    assert repli.recupere_le == ancien.recupere_le
    pd.testing.assert_frame_equal(repli.donnees, ancien.donnees)
    dataloader.charger_donnees()
    assert get.call_count == 2
    temps[0] += 300
    get.side_effect = None
    assert dataloader.charger_instantane().erreur is None
    assert get.call_count == 3


@pytest.mark.parametrize("texte", [b"", b"erreur HTML", b"\xff"])
def test_export_vide_schema_invalide_ou_encodage_invalide(api, texte):
    _, reponse = api
    reponse.content = texte
    with pytest.raises(DonneesInvalides, match="Aucun instantané API valide"):
        dataloader.charger_donnees()


@pytest.mark.parametrize("date", ["invalide", ""])
def test_dates_invalides_refusees(api, date):
    _, reponse = api
    reponse.content = reponse.content.replace(b"2026-09", date.encode())
    with pytest.raises(DonneesInvalides, match="dates invalides"):
        dataloader.charger_donnees()


def test_export_sans_ligne_refuse(api):
    _, reponse = api
    reponse.content = reponse.content.splitlines(keepends=True)[0]
    with pytest.raises(DonneesInvalides, match="jeu vide"):
        dataloader.charger_donnees()


def test_schema_invalide_ne_remplace_pas_le_cache(api, monkeypatch):
    _, reponse = api
    temps = [0.0]
    monkeypatch.setattr(dataloader.time, "monotonic", lambda: temps[0])
    ancien = dataloader.charger_instantane()
    temps[0] = 3600
    reponse.content = b"Erreur\ninvalide\n"
    repli = dataloader.charger_instantane()
    assert repli.erreur
    assert repli.recupere_le == ancien.recupere_le
    pd.testing.assert_frame_equal(ancien.donnees, repli.donnees)


def test_export_toutes_les_lignes_conservees(api):
    _, reponse = api
    entete, ligne = reponse.content.decode("utf-8-sig").splitlines()
    reponse.content = (entete + "\n" + (ligne + "\n") * 150).encode()
    assert len(dataloader.charger_donnees()) == 150
