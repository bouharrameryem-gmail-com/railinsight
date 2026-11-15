"""Préparation des données et orchestration de l'analyse Q1."""

from railinsight.analysis.liaisons_fiabilite import (
    AnalyseLiaisonsFiabilite,
    calculer_analyse_liaisons_fiabilite,
)
from railinsight.analysis.nettoyage import nettoyer_regularite, retirer_sans_train
from railinsight.backend.dataloader import charger_donnees
from railinsight.config import charger_config


def charger_analyse_liaisons_fiabilite() -> AnalyseLiaisonsFiabilite:
    """Charge les données SNCF et calcule les résultats de la Q1."""
    config = charger_config()
    donnees = retirer_sans_train(nettoyer_regularite(charger_donnees()))
    parametres = config.liaisons_fiabilite
    return calculer_analyse_liaisons_fiabilite(
        donnees,
        covid_debut=parametres.covid_debut,
        covid_fin=parametres.covid_fin,
    )
