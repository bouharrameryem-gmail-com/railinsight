"""Custom exceptions for the RailInsight application."""


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
