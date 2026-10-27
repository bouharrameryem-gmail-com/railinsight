"""Tests du chargement et de la validation de la configuration."""

import pytest

from railinsight.config import ConfigInvalide, charger_config


def ecrire(tmp_path, texte):
    """Écrit un YAML de surcharge temporaire et renvoie son chemin."""
    fichier = tmp_path / "essai.yaml"
    fichier.write_text(texte, encoding="utf-8")
    return fichier


def test_defaut_valide():
    cfg = charger_config(environ={})
    assert cfg.chemins.donnees.is_absolute()


def test_config_invalide_est_une_valueerror():
    assert issubclass(ConfigInvalide, ValueError)


def test_surcharge_partielle(tmp_path):
    defaut = charger_config(environ={})
    cfg = charger_config(ecrire(tmp_path, "score_fiabilite:\n  poids: 0.7"), environ={})
    assert cfg.score_fiabilite.poids == 0.7
    assert cfg.score_fiabilite.min_trains == defaut.score_fiabilite.min_trains


def test_surcharge_par_variable_denvironnement(tmp_path):
    fichier = ecrire(tmp_path, "graine: 7")
    cfg = charger_config(environ={"RAILINSIGHT_CONFIG": str(fichier)})
    assert cfg.graine == 7


@pytest.mark.parametrize(
    ("texte", "cle"),
    [
        ("sueil: 0.3", "sueil"),
        ("score_fiabilite:\n  poid: 0.5", "score_fiabilite.poid"),
        ("chemins:\n  inconnu: x", "chemins.inconnu"),
        ("score_fiabilite:\n  poids: 1.5", "poids"),
        ("score_fiabilite:\n  poids: abc", "poids"),
        ("score_fiabilite:\n  min_trains: 0", "min_trains"),
        ("score_fiabilite:\n  cap_retard: 0", "cap_retard"),
        ("score_fiabilite:\n  periode_debut: '2020/01'", "periode_debut"),
        (
            "score_fiabilite:\n  periode_debut: '2024-01'\n  periode_fin: '2023-01'",
            "periode_debut",
        ),
        ("graine: abc", "graine"),
        ("graine: 4.2", "graine"),
        ("chemins:\n  donnees: null", "chemins.donnees"),
    ],
)
def test_invalides(tmp_path, texte, cle):
    with pytest.raises(ConfigInvalide, match=cle):
        charger_config(ecrire(tmp_path, texte), environ={})


def test_fichier_introuvable(tmp_path):
    with pytest.raises(ConfigInvalide, match="introuvable"):
        charger_config(tmp_path / "absent.yaml", environ={})
