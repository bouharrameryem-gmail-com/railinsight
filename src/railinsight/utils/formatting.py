"""French number and date formatters.

French conventions used throughout the app:
  - Decimal separator: comma   (12,3 instead of 12.3)
  - Thousands separator: narrow no-break space  (12 345 instead of 12,345)
  - Percentage: space before %  (12,3 %)
  - Months: full name in lowercase  (janvier 2024)
"""

from __future__ import annotations

import pandas as pd

_MONTHS_FR = [
    "",
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

# Narrow no-break space (U+202F) — the correct French thousands separator
_NNBSP = " "


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a ratio as a French percentage string.

    Args:
        value: A ratio between 0 and 1 (e.g., 0.123).
        decimals: Number of decimal places.

    Returns:
        A string like '12,3 %'.

    Examples:
        >>> fmt_pct(0.1234)
        '12,3 %'
        >>> fmt_pct(0.0, decimals=0)
        '0 %'
    """
    formatted = f"{value * 100:.{decimals}f}".replace(".", ",")
    return f"{formatted}{_NNBSP}%"


def fmt_number(value: float, decimals: int = 0) -> str:
    """Format a number with French thousands separator.

    Args:
        value: The number to format.
        decimals: Number of decimal places.

    Returns:
        A string like '12 345' or '12 345,6'.

    Examples:
        >>> fmt_number(12345)
        '12 345'
        >>> fmt_number(12345.678, decimals=1)
        '12 345,7'
    """
    if decimals == 0:
        return f"{int(round(value)):,}".replace(",", _NNBSP)
    formatted = f"{value:,.{decimals}f}"
    # Python uses . for decimal and , for thousands; swap both for French
    return formatted.replace(",", "￿").replace(".", ",").replace("￿", _NNBSP)


def fmt_month(period: pd.Period) -> str:
    """Format a pandas Period (monthly frequency) as a French month string.

    Args:
        period: A pandas Period with freq='M'.

    Returns:
        A string like 'janvier 2024'.

    Examples:
        >>> fmt_month(pd.Period('2024-01', freq='M'))
        'janvier 2024'
    """
    return f"{_MONTHS_FR[period.month]} {period.year}"
