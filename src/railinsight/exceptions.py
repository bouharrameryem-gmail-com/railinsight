"""Exceptions propres à RailInsight.

Toutes héritent de ErreurRailInsight : une couche appelante (l'interface
Streamlit, par exemple) attrape cette seule classe pour afficher un message
propre. Chacune hérite aussi de l'exception standard la plus proche de son sens.
"""


class ErreurRailInsight(Exception):
    """Base de toutes les erreurs volontaires du paquet."""


class ConfigInvalide(ErreurRailInsight, ValueError):
    """Configuration invalide : le message contient le nom de la clé en cause."""


class DonneesInvalides(ErreurRailInsight, ValueError):
    """Fichier de données invalide : vide, illisible ou colonnes manquantes."""


class RailInsightError(Exception):
    """Base exception for all RailInsight domain errors."""


class InvalidSelectionError(RailInsightError):
    """Raised when the user makes an invalid selection (route, period, etc.)."""


class InsufficientDataError(RailInsightError):
    """Raised when there are too few data points for a meaningful analysis."""
