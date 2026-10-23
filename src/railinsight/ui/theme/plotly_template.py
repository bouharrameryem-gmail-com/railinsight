"""Register the shared RailInsight Plotly template.

Call register_template() once at app startup. All subsequent figures that
do not specify a template will use it automatically.
"""

import plotly.graph_objects as go
import plotly.io as pio

from railinsight.ui.theme.tokens import CLUSTER_COLORS, GRAY_100, GRAY_700, GRAY_900

TEMPLATE_NAME = "railinsight"


def register_template() -> None:
    """Register the RailInsight Plotly template (idempotent).

    Sets the template as the global default so every go.Figure() and
    px.* call inherits it without extra arguments.
    """
    if TEMPLATE_NAME in pio.templates:
        return

    layout = go.Layout(
        font={"family": "Inter, Arial, sans-serif", "color": GRAY_900, "size": 13},
        paper_bgcolor="white",
        plot_bgcolor=GRAY_100,
        colorway=CLUSTER_COLORS,
        title={"font": {"size": 16, "color": GRAY_900}, "x": 0.02},
        xaxis={
            "gridcolor": GRAY_100,
            "linecolor": GRAY_700,
            "tickcolor": GRAY_700,
            "ticks": "outside",
        },
        yaxis={
            "gridcolor": GRAY_100,
            "linecolor": GRAY_700,
            "tickcolor": GRAY_700,
            "ticks": "outside",
        },
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": GRAY_700,
            "borderwidth": 0.5,
        },
        margin={"l": 60, "r": 30, "t": 60, "b": 60},
    )

    pio.templates[TEMPLATE_NAME] = go.layout.Template(layout=layout)
    pio.templates.default = TEMPLATE_NAME
