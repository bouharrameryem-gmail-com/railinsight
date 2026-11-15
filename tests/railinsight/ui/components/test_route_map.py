"""Tests de la carte géographique des liaisons."""

import railinsight.ui.components.route_map as component


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
