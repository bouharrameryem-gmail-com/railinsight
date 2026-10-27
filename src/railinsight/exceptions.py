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


class DataUnavailableError(RailInsightError):
    """Raised when required data cannot be loaded from disk or the backend."""


class InvalidSelectionError(RailInsightError):
    """Raised when the user makes an invalid selection (route, period, etc.)."""


class PeriodOutOfRangeError(RailInsightError):
    """Raised when the requested period falls outside available date range."""


class SchemaValidationError(RailInsightError):
    """Raised when the data schema does not match expectations."""


class InsufficientDataError(RailInsightError):
    """Raised when there are too few data points for a meaningful analysis."""
