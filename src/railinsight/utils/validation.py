"""Outils de validation de valeurs, utilisés par railinsight.config."""

import re

from railinsight.exceptions import ConfigInvalide

_PERIODE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def verifier_entier(cle: str, valeur: object, minimum: int | None = None) -> None:
    """Exige un entier (booléen exclu), éventuellement >= minimum."""
    if not isinstance(valeur, int) or isinstance(valeur, bool):
        raise ConfigInvalide(f"'{cle}' doit être un entier, reçu : {valeur!r}")
    if minimum is not None and valeur < minimum:
        raise ConfigInvalide(f"'{cle}' doit être >= {minimum}, reçu : {valeur!r}")


def verifier_nombre(
    cle: str,
    valeur: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strict: bool = False,
) -> None:
    """Exige un nombre dans l'intervalle voulu (bornes exclues si strict)."""
    if isinstance(valeur, bool) or not isinstance(valeur, int | float):
        raise ConfigInvalide(f"'{cle}' doit être un nombre, reçu : {valeur!r}")
    bas = minimum is None or (valeur > minimum if strict else valeur >= minimum)
    haut = maximum is None or (valeur < maximum if strict else valeur <= maximum)
    if not (bas and haut):
        signe_bas, signe_haut = (">", "<") if strict else (">=", "<=")
        regles = []
        if minimum is not None:
            regles.append(f"{signe_bas} {minimum}")
        if maximum is not None:
            regles.append(f"{signe_haut} {maximum}")
        raise ConfigInvalide(
            f"'{cle}' doit être {' et '.join(regles)}, reçu : {valeur!r}"
        )


def verifier_periode(cle: str, valeur: object) -> None:
    """Exige null ou une chaîne 'AAAA-MM'."""
    if valeur is not None and not (
        isinstance(valeur, str) and _PERIODE.fullmatch(valeur)
    ):
        raise ConfigInvalide(
            f"'{cle}' doit valoir null ou 'AAAA-MM', reçu : {valeur!r}"
        )