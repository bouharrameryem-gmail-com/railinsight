"""Logique métier pour les pages de fiabilité des liaisons (Q1)."""

from __future__ import annotations

from railinsight.analysis.reliability import ReliabilityReport, build_reliability_report


def get_reliability_report() -> ReliabilityReport:
    """Charge les données et calcule le rapport de fiabilité Q1.

    Les paramètres viennent de la section ``liaisons_fiabilite`` de
    ``config/defaut.yaml``.

    Returns:
        Le :class:`ReliabilityReport` calculé.
    """
    return build_reliability_report()
