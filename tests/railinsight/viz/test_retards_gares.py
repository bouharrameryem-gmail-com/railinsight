"""Tests des figures de la Q2."""

from railinsight.analysis.causes_retards import DELAY_COLUMNS
from railinsight.viz import retards_gares


def test_constantes_couvrent_toutes_les_categories():
    for constante in (
        retards_gares.COULEURS_CATEGORIES,
        retards_gares.LIBELLES_CATEGORIES,
        retards_gares.PARTS_CATEGORIES,
    ):
        assert list(constante) == DELAY_COLUMNS