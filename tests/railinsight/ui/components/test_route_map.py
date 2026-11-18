"""Tests de la carte géographique des liaisons."""

import pandas as pd

import railinsight.ui.components.route_map as component


def test_carte_accueil_couleurs_coordonnees_et_survol():
    table = pd.DataFrame(
        {
            "gare_a": ["PARIS LYON"] * 5 + ["INCONNUE"],
            "gare_b": ["LYON PART DIEU"] * 6,
            "liaison": [f"Liaison {i}" for i in range(6)],
            "taux_incidents": [0.0, 0.1, 0.11, 0.2, 1.0, 0.5],
            "prevus": [1000] * 6,
            "n_mois": [12] * 6,
        }
    )
    figure, manquantes = component.carte_accueil(table)
    assert manquantes == ["Liaison 5"]
    assert len(figure.data) == 5
    assert [t.line.color for t in figure.data] == [
        "#0072B2",
        "#0072B2",
        "#B56500",
        "#B56500",
        "#B32865",
    ]
    assert sum(t.showlegend for t in figure.data) == 3
    assert list(figure.data[0].lat) == [48.8448, 45.7604]
    assert list(figure.data[0].lon) == [2.3735, 4.8593]
    assert "Mois mesurés : 12 / 12" in figure.data[0].text[0]
    assert "100,0 %" in figure.data[4].text[0]
    assert figure.layout.map.style == "open-street-map"


def test_carte_accueil_vide():
    figure, manquantes = component.carte_accueil(pd.DataFrame())
    assert not figure.data
    assert manquantes == []


def test_parse_route_accepte_les_separateurs_connus():
    assert component._parse_route("PARIS LYON → LYON") == ("PARIS LYON", "LYON")
    assert component._parse_route("PARIS MONTPARNASSE -> NANTES") == (
        "PARIS MONTPARNASSE",
        "NANTES",
    )
    assert component._parse_route("LYON - LILLE") == ("LYON", "LILLE")
    assert component._parse_route("liaison invalide") is None


def test_normalisation_et_coordonnees_avec_alias():
    assert component._normalize("  lyon  ") == "LYON PART DIEU"
    assert component._get_coords("LYON") == component._STATION_COORDS["LYON PART DIEU"]
    assert component._get_coords("GARE INCONNUE") is None


def test_route_map_affiche_liaisons_gares_et_couverture(monkeypatch):
    figures = []
    captions = []
    monkeypatch.setattr(
        component, "chart_container", lambda fig, **kwargs: figures.append(fig)
    )
    monkeypatch.setattr(component.st, "caption", captions.append)
    routes = [
        "PARIS LYON → LYON",
        "PARIS MONTPARNASSE -> LYON PART DIEU",
        "INCONNUE → LYON",
        "route invalide",
        "LYON - LILLE FLANDRES",
        "LYON → PARIS LYON",
    ]

    component.route_map(
        routes=routes,
        labels=[0, 1, 1, 0, 2, 2],
        k=4,
        label_names={0: "Profil A", 1: "Profil B", 2: "Profil C"},
        hover_extras={"Taux": ["10 %", "20 %"]},
    )

    figure = figures[0]
    assert len(figure.data) == 7
    assert (
        "<b>PARIS LYON → LYON</b><br>Profil A<br>Taux: 10 %" in figure.data[1].hovertext
    )
    assert any(
        texte.startswith("<b>LYON → PARIS LYON</b><br>Profil C")
        for texte in figure.data[5].hovertext
    )
    assert len(figure.data[6].lat) == 5
    assert captions == ["4 / 6 liaisons représentées (coordonnées manquantes pour 2)."]


def test_route_map_sans_liaisons_representables(monkeypatch):
    figures = []
    captions = []
    monkeypatch.setattr(
        component, "chart_container", lambda fig, **kwargs: figures.append(fig)
    )
    monkeypatch.setattr(component.st, "caption", captions.append)

    component.route_map(
        routes=["sans séparateur"],
        labels=[0],
        k=2,
        label_names={},
    )

    assert len(figures) == 1
    assert len(figures[0].data) == 0
    assert captions == ["0 / 1 liaisons représentées (coordonnées manquantes pour 1)."]
