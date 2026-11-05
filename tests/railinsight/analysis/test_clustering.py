"""Tests du clustering : mise à l'échelle, algorithmes, choix de k et lien de Ward."""

import numpy as np
import pandas as pd
import pytest

from railinsight.analysis.clustering import (
    auto_select_k,
    calculer_liaison_ward,
    entrainer_clustering,
    mettre_a_echelle,
)
from railinsight.exceptions import InsufficientDataError


@pytest.fixture
def deux_groupes():
    """Deux groupes bien séparés de 20 points chacun."""
    rng = np.random.default_rng(0)
    return np.vstack(
        [rng.normal(0, 0.3, size=(20, 3)), rng.normal(10, 0.3, size=(20, 3))]
    )


@pytest.mark.parametrize("algorithme", ["kmeans", "ward", "gmm"])
def test_entrainer_clustering_separe_les_deux_groupes(deux_groupes, algorithme):
    labels = entrainer_clustering(deux_groupes, algorithme, 2)

    assert len(set(labels[:20])) == 1
    assert len(set(labels[20:])) == 1
    assert labels[0] != labels[20]


def test_entrainer_clustering_algorithme_inconnu(deux_groupes):
    with pytest.raises(ValueError, match="inconnu"):
        entrainer_clustering(deux_groupes, "dbscan", 2)


def test_auto_select_k_trouve_deux_groupes(deux_groupes):
    assert auto_select_k(deux_groupes, "kmeans") == 2


def test_scale_features_centre_et_reduit():
    features = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [10.0, 20.0, 40.0, 80.0]})

    x_scaled, _ = mettre_a_echelle(features, "standard")

    assert x_scaled.mean(axis=0) == pytest.approx([0.0, 0.0])
    assert x_scaled.std(axis=0) == pytest.approx([1.0, 1.0])


def test_calculer_liaison_ward_forme(deux_groupes):
    assert calculer_liaison_ward(deux_groupes).shape == (39, 4)


def test_calculer_liaison_ward_une_seule_observation():
    with pytest.raises(InsufficientDataError):
        calculer_liaison_ward(np.array([[1.0, 2.0]]))
