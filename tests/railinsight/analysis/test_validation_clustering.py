"""Tests de la validation du clustering : inertie, courbe, ARI, η² et comparaison."""

import numpy as np
import pandas as pd
import pytest

from railinsight.analysis.validation_clustering import (
    _inertie,
    compare_configurations,
    compute_ari_bootstrap,
    compute_ari_seeds,
    compute_eta2,
    permutation_test,
    silhouette_curve,
)


@pytest.fixture
def deux_groupes():
    """Deux groupes bien séparés de 20 points chacun."""
    rng = np.random.default_rng(0)
    return np.vstack(
        [rng.normal(0, 0.3, size=(20, 3)), rng.normal(10, 0.3, size=(20, 3))]
    )


def test_inertie_calculee_a_la_main():
    # Groupe 1 : points 0 et 2, centre 1  -> 1 + 1 = 2
    # Groupe 2 : points 10 et 12, centre 11 -> 1 + 1 = 2
    x = np.array([[0.0], [2.0], [10.0], [12.0]])

    assert _inertie(x, np.array([0, 0, 1, 1])) == pytest.approx(4.0)


def test_silhouette_curve_colonnes_et_lignes(deux_groupes):
    courbe = silhouette_curve(deux_groupes, "kmeans", k_range=range(2, 5))

    assert list(courbe.columns) == [
        "k",
        "silhouette",
        "davies_bouldin",
        "min_cluster_size",
        "inertia",
    ]
    assert courbe["k"].tolist() == [2, 3, 4]
    assert courbe["inertia"].is_monotonic_decreasing


def test_compute_ari_seeds_stable_sur_des_groupes_nets(deux_groupes):
    ari = compute_ari_seeds(deux_groupes, "kmeans", 2, n_seeds=5)

    assert len(ari) == 5
    assert (ari == 1.0).all()


def test_compute_ari_bootstrap_stable_et_echantillons_trop_petits(deux_groupes):
    ari = compute_ari_bootstrap(
        deux_groupes, "kmeans", 2, n_iter=5, fraction=0.8, random_state=0
    )
    trop_petits = compute_ari_bootstrap(
        deux_groupes, "kmeans", 2, n_iter=5, fraction=0.05, random_state=0
    )

    assert len(ari) == 5
    assert (ari == 1.0).all()
    assert trop_petits.empty


def test_permutation_test_et_aucune_permutation(deux_groupes):
    resultat = permutation_test(
        deux_groupes, "kmeans", 2, n_permutations=3, random_state=0
    )
    sans_permutation = permutation_test(
        deux_groupes, "kmeans", 2, n_permutations=0, random_state=0
    )

    assert resultat["observed_silhouette"] > 0.9
    assert 0.0 <= resultat["p_value"] <= 1.0
    assert np.isnan(sans_permutation["max_null_silhouette"])
    assert np.isnan(sans_permutation["p_value"])


def test_compute_eta2_separation_parfaite_et_variable_constante():
    features = pd.DataFrame(
        {
            "separe": [0.0] * 5 + [10.0] * 5,
            "constante": [3.0] * 10,
        }
    )
    labels = np.array([0] * 5 + [1] * 5)

    eta2 = compute_eta2(features, labels, ["separe", "constante"])

    assert eta2["separe"] == pytest.approx(1.0)
    assert eta2["constante"] == 0.0


def test_compute_eta2_ignore_variable_absente_et_signale_peu_de_valeurs():
    features = pd.DataFrame(
        {"incomplete": [1.0, 2.0, 3.0, 4.0, np.nan], "valide": range(5)}
    )

    eta2 = compute_eta2(
        features, np.array([0, 0, 1, 1, 1]), ["absente", "incomplete", "valide"]
    )

    assert "absente" not in eta2
    assert np.isnan(eta2["incomplete"])
    assert np.isfinite(eta2["valide"])


def test_compare_configurations_ignore_la_numerotation():
    routes = pd.Index(list("abcdef"))
    labels_a = np.array([0, 0, 0, 1, 1, 1])
    labels_b = np.array([1, 1, 1, 0, 0, 0])  # mêmes groupes, numéros échangés

    resultat = compare_configurations(routes, labels_a, routes, labels_b)

    assert resultat["ari"] == pytest.approx(1.0)
    assert resultat["n_changed"] == 0


def test_compare_configurations_compte_les_liaisons_qui_changent():
    routes = pd.Index(list("abcdef"))
    labels_a = np.array([0, 0, 0, 1, 1, 1])
    labels_b = np.array([1, 1, 0, 0, 0, 0])  # « c » change de groupe

    resultat = compare_configurations(routes, labels_a, routes, labels_b)

    assert resultat["n_common"] == 6
    assert resultat["n_changed"] == 1
    assert resultat["changed_routes"] == ["c"]


def test_compare_configurations_sans_liaison_commune():
    resultat = compare_configurations(
        pd.Index(["a", "b"]), np.array([0, 1]), pd.Index(["x", "y"]), np.array([0, 1])
    )

    assert np.isnan(resultat["ari"])
    assert resultat["n_common"] == 0
