"""Tests du backend profils_ponctualite."""

import numpy as np
import pandas as pd
import pytest

from railinsight.backend.profils_ponctualite import ResultatClustering, clusteriser
from railinsight.exceptions import DonneesInvalides


def _indicateurs(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "cancellation_rate": rng.uniform(0, 0.1, n),
            "late15_rate": rng.uniform(0, 0.3, n),
            "severe_share": rng.uniform(0, 0.5, n),
            "extreme_share": rng.uniform(0, 0.3, n),
            "volatility_cv": rng.uniform(0, 0.5, n),
        },
        index=[f"Liaison_{i}" for i in range(n)],
    )


class TestClusteriser:
    def test_retourne_resultat_clustering(self):
        result = clusteriser(_indicateurs())
        assert isinstance(result, ResultatClustering)

    def test_k_fixe_respecte(self):
        for k in [2, 3, 4]:
            result = clusteriser(_indicateurs(n=k * 6), k=k)
            assert result.k == k

    def test_etiquettes_meme_taille_que_liaisons(self):
        indicateurs = _indicateurs()
        result = clusteriser(indicateurs)
        assert len(result.etiquettes) == len(indicateurs)

    def test_trop_peu_de_liaisons_leve_erreur(self):
        with pytest.raises(DonneesInvalides):
            clusteriser(_indicateurs(n=2))

    def test_silhouette_entre_0_et_1(self):
        result = clusteriser(_indicateurs())
        assert 0 <= result.silhouette <= 1

    def test_coordonnees_pca_bonne_forme(self):
        indicateurs = _indicateurs()
        result = clusteriser(indicateurs)
        assert result.pca_coordonnees.shape == (len(indicateurs), 2)


class TestNommerClusters:
    @pytest.mark.parametrize("k", [2, 3, 4, 5])
    def test_noms_coherents_avec_k(self, k: int):
        result = clusteriser(_indicateurs(n=k * 6), k=k)
        assert len(result.noms_clusters) == k

    @pytest.mark.parametrize("k", [2, 3, 4])
    def test_noms_distincts(self, k: int):
        result = clusteriser(_indicateurs(n=k * 6), k=k)
        noms = list(result.noms_clusters.values())
        assert len(set(noms)) == len(noms), "Chaque profil doit avoir un nom unique"
