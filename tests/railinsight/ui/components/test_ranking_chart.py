"""Tests du composant de classement horizontal."""

import pandas as pd

import railinsight.ui.components.ranking_chart as component


def test_ranking_chart_affiche_les_valeurs_les_plus_elevees(monkeypatch):
    figures = []
    monkeypatch.setattr(
        component, "chart_container", lambda fig, **kwargs: figures.append(fig)
    )
    donnees = pd.DataFrame(
        {"liaison": ["A", "B", "C", "Sans valeur"], "taux": [0.1, 0.3, 0.2, None]}
    )

    component.ranking_chart(
        donnees,
        label_col="liaison",
        metric_col="taux",
        title="Top des liaisons",
        top_n=2,
        format_as_pct=True,
        how_to_read="Lecture",
    )

    figure = figures[0]
    assert list(figure.data[0].y) == ["B", "C"]
    assert list(figure.data[0].text) == ["30.0%", "20.0%"]
    assert figure.layout.height == 300


def test_ranking_chart_tri_ascendant_et_slider(monkeypatch):
    figures = []
    appels_slider = []

    def capturer_slider(*args, **kwargs):
        appels_slider.append(kwargs)
        return 5

    monkeypatch.setattr(
        component, "chart_container", lambda fig, **kwargs: figures.append(fig)
    )
    monkeypatch.setattr(component.st, "slider", capturer_slider)
    donnees = pd.DataFrame(
        {"gare": [f"G{i}" for i in range(10)], "retard": list(range(10))}
    )

    component.ranking_chart(
        donnees,
        label_col="gare",
        metric_col="retard",
        title="Meilleures gares",
        top_n=8,
        ascending=True,
        show_top_n_slider=True,
        key="nombre_gares",
    )

    assert appels_slider[0]["min_value"] == 5
    assert appels_slider[0]["max_value"] == 10
    assert list(figures[0].data[0].y) == ["G0", "G1", "G2", "G3", "G4"]


def test_ranking_chart_retombe_sur_top_n_sans_cle_slider(monkeypatch):
    figures = []
    monkeypatch.setattr(
        component, "chart_container", lambda fig, **kwargs: figures.append(fig)
    )
    donnees = pd.DataFrame({"gare": ["A", "B", "C"], "retard": [1, 2, 3]})

    component.ranking_chart(
        donnees,
        label_col="gare",
        metric_col="retard",
        title="Gares",
        top_n=2,
        show_top_n_slider=True,
    )

    assert list(figures[0].data[0].y) == ["C", "B"]
