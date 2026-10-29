"""Geographic map of TGV routes coloured by cluster label or continuous value.

Draws straight lines between departure and arrival stations on a France-centered
map. Station coordinates are hardcoded (WGS84) for the main French TGV network.

Usage (discrete clusters):
    route_map(
        routes=results["routes"],
        labels=results["labels"],
        k=results["k"],
        label_names={0: "Ponctuel", 1: "Peu fiable"},
        title="Répartition géographique des profils",
    )

Usage (continuous score):
    route_map(
        routes=route_list,
        values=score_series.tolist(),
        discrete=False,
        colorscale="RdYlGn",
        title="Score de fiabilité",
    )
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import streamlit as st

from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.theme.tokens import CLUSTER_COLORS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Station coordinates (WGS84 lat, lon) — main French TGV network
# ---------------------------------------------------------------------------

_STATION_COORDS: dict[str, tuple[float, float]] = {
    # Paris terminals
    "PARIS GARE DE LYON": (48.8448, 2.3735),
    "PARIS MONTPARNASSE": (48.8408, 2.3194),
    "PARIS NORD": (48.8806, 2.3553),
    "PARIS EST": (48.8769, 2.3590),
    "PARIS ST LAZARE": (48.8762, 2.3252),
    "PARIS AUSTERLITZ": (48.8431, 2.3658),
    # Île-de-France / aéroports
    "MASSY TGV": (48.7232, 2.2726),
    "MARNE LA VALLEE CHESSY": (48.8732, 2.7794),
    "CHARLES DE GAULLE 2 TGV": (49.0057, 2.5488),
    # Nord
    "LILLE FLANDRES": (50.6389, 3.0726),
    "LILLE EUROPE": (50.6391, 3.0758),
    "ARRAS": (50.2876, 2.7804),
    "LENS": (50.4285, 2.8309),
    # Est / Alsace-Lorraine
    "STRASBOURG": (48.5852, 7.7352),
    "MULHOUSE VILLE": (47.7408, 7.3379),
    "COLMAR": (48.0791, 7.3550),
    "METZ VILLE": (49.1092, 6.1777),
    "NANCY VILLE": (48.6897, 6.1769),
    "REIMS": (49.2584, 4.0339),
    "CHAMPAGNE ARDENNE TGV": (49.2062, 4.0447),
    "MEUSE TGV": (48.8878, 5.3097),
    "LORRAINE TGV": (48.9590, 6.1419),
    # Normandie
    "CAEN": (49.1846, -0.3570),
    "ROUEN RIVE DROITE": (49.4433, 1.0994),
    "LE HAVRE": (49.4927, 0.1078),
    "CHERBOURG": (49.6335, -1.6207),
    # Grand Ouest
    "NANTES": (47.2173, -1.5422),
    "RENNES": (48.1031, -1.6725),
    "BREST": (48.3918, -4.4842),
    "QUIMPER": (47.9963, -4.0980),
    "LORIENT": (47.7459, -3.3710),
    "VANNES": (47.6587, -2.7553),
    "SAINT BRIEUC": (48.5139, -2.7654),
    "LE MANS": (47.9958, 0.1926),
    "ANGERS SAINT LAUD": (47.4634, -0.5555),
    "TOURS": (47.3904, 0.6895),
    "LA ROCHELLE VILLE": (46.1592, -1.1553),
    "POITIERS": (46.5806, 0.3420),
    "NIORT": (46.3238, -0.4667),
    # Sud-Ouest
    "BORDEAUX ST JEAN": (44.8259, -0.5573),
    "TOULOUSE MATABIAU": (43.6117, 1.4537),
    "BAYONNE": (43.4929, -1.4749),
    "BIARRITZ": (43.4858, -1.5571),
    "PAU": (43.2986, -0.3691),
    "TARBES": (43.2320, 0.0703),
    "AGEN": (44.2069, 0.6235),
    "ANGOULEME": (45.6494, 0.1505),
    "DAX": (43.7116, -1.0539),
    "HENDAYE": (43.3607, -1.7727),
    "ARCACHON": (44.6597, -1.1679),
    # Lyon et alentours
    "LYON PART DIEU": (45.7604, 4.8593),
    "LYON PERRACHE": (45.7484, 4.8261),
    "LYON ST EXUPERY TGV": (45.7225, 5.0813),
    "MACON LOCHE TGV": (46.3017, 4.8367),
    "BOURG EN BRESSE": (46.2051, 5.2261),
    # Auvergne-Rhône-Alpes
    "GRENOBLE": (45.1917, 5.7158),
    "CHAMBERY CHALLES LES EAUX": (45.5703, 5.9213),
    "ANNECY": (45.9007, 6.1188),
    "VALENCE TGV": (44.9252, 4.9742),
    "VALENCE VILLE": (44.9326, 4.8910),
    "CLUSES": (46.0616, 6.5782),
    # PACA
    "MARSEILLE ST CHARLES": (43.3036, 5.3812),
    "NICE VILLE": (43.7055, 7.2677),
    "TOULON": (43.1242, 5.9304),
    "AIX EN PROVENCE TGV": (43.4561, 5.3174),
    "AVIGNON TGV": (43.9210, 4.7858),
    "AVIGNON CENTRE": (43.9448, 4.8069),
    "MONTPELLIER ST ROCH": (43.6044, 3.8801),
    "NIMES": (43.8358, 4.3598),
    "ARLES": (43.6768, 4.6267),
    "ANTIBES": (43.5804, 7.1262),
    "CANNES": (43.5517, 7.0174),
    # Bourgogne-Franche-Comté
    "DIJON VILLE": (47.3218, 5.0412),
    "BESANCON FRANCHE COMTE TGV": (47.2560, 5.9860),
    "BELFORT MONTBELIARD TGV": (47.5991, 6.9027),
    "CHALON SUR SAONE": (46.7804, 4.8549),
    # Centre-Val de Loire
    "BLOIS ONZAIN": (47.5851, 1.3294),
    "VENDOME VILLIERS SUR LOIR": (47.7948, 0.9984),
    "SAINT PIERRE DES CORPS": (47.3831, 0.7252),
    "VIERZON": (47.2211, 2.0671),
    "BOURGES": (47.0810, 2.3975),
    # International
    "GENEVE": (46.2100, 6.1424),
    "GENÈVE": (46.2100, 6.1424),
    "LAUSANNE": (46.5165, 6.6297),
    "ZURICH": (47.3774, 8.5403),
    "BRUXELLES MIDI": (50.8355, 4.3363),
    "AMSTERDAM CENTRAAL": (52.3791, 4.8997),
    "LONDON ST PANCRAS": (51.5308, -0.1238),
}

# Alternative names that appear in the SNCF dataset
_ALIASES: dict[str, str] = {
    "PARIS LYON": "PARIS GARE DE LYON",
    "PARIS-LYON": "PARIS GARE DE LYON",
    "PARIS-MONTPARNASSE": "PARIS MONTPARNASSE",
    "PARIS-NORD": "PARIS NORD",
    "PARIS-EST": "PARIS EST",
    "LYON": "LYON PART DIEU",
    "MARSEILLE": "MARSEILLE ST CHARLES",
    "BORDEAUX": "BORDEAUX ST JEAN",
    "TOULOUSE": "TOULOUSE MATABIAU",
    "MONTPELLIER": "MONTPELLIER ST ROCH",
}


def _normalize(name: str) -> str:
    """Uppercase + strip, then apply alias table."""
    cleaned = name.strip().upper()
    return _ALIASES.get(cleaned, cleaned)


def _get_coords(station: str) -> tuple[float, float] | None:
    key = _normalize(station)
    coords = _STATION_COORDS.get(key)
    if coords is None:
        logger.debug("route_map: no coordinates for %r", station)
    return coords


def _parse_route(route: str) -> tuple[str, str] | None:
    """Split 'DEPARTURE → ARRIVAL' into (departure, arrival)."""
    for sep in (" → ", " -> ", " - "):
        if sep in route:
            parts = route.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return None


# ---------------------------------------------------------------------------
# Public component
# ---------------------------------------------------------------------------


def route_map(
    routes: list[str],
    labels: list[int],
    k: int,
    label_names: dict[int, str] | None = None,
    hover_extras: dict[str, list] | None = None,
    title: str = "Répartition géographique des profils",
    how_to_read: str = (
        "Chaque ligne relie une gare de départ à une gare d'arrivée. "
        "La couleur indique le profil de ponctualité de la liaison."
    ),
) -> None:
    """Render a geographic map of TGV routes coloured by cluster.

    Routes whose departure or arrival station is not in the coordinates
    dictionary are silently skipped (a debug log is emitted).

    Args:
        routes: List of route strings in 'A → B' format.
        labels: Integer cluster label for each route (same order as routes).
        k: Number of clusters.
        label_names: Optional dict mapping cluster int → display name.
        hover_extras: Optional dict of extra fields to show in hover tooltip.
            Each key is a field name, value is a list aligned with routes.
        title: Chart title.
        how_to_read: Reading guide text.
    """
    names = label_names or {c: f"Profil {c + 1}" for c in range(k)}
    fig = go.Figure()

    # One line trace per cluster (groups routes for legend + colour)
    for cluster_id in range(k):
        color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
        lats: list[float | None] = []
        lons: list[float | None] = []
        mid_lats: list[float] = []
        mid_lons: list[float] = []
        hover_labels: list[str] = []

        for idx, (route, lbl) in enumerate(zip(routes, labels, strict=False)):
            if int(lbl) != cluster_id:
                continue
            parsed = _parse_route(route)
            if parsed is None:
                continue
            dep, arr = parsed
            dep_c = _get_coords(dep)
            arr_c = _get_coords(arr)
            if dep_c is None or arr_c is None:
                continue

            # Line segment (None separator between routes in the same trace)
            lats += [dep_c[0], arr_c[0], None]
            lons += [dep_c[1], arr_c[1], None]

            # Midpoint for hover tooltip
            mid_lats.append((dep_c[0] + arr_c[0]) / 2)
            mid_lons.append((dep_c[1] + arr_c[1]) / 2)
            extra = ""
            if hover_extras:
                parts = [
                    f"{k_}: {v[idx]}" for k_, v in hover_extras.items() if idx < len(v)
                ]
                extra = "<br>" + "<br>".join(parts)
            hover_labels.append(f"<b>{route}</b><br>{names[cluster_id]}{extra}")

        if not lats:
            continue

        # Lines
        fig.add_trace(
            go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line={"color": color, "width": 2},
                name=names[cluster_id],
                legendgroup=str(cluster_id),
                showlegend=True,
                hoverinfo="skip",
            )
        )
        # Invisible midpoint markers for hover
        fig.add_trace(
            go.Scattergeo(
                lat=mid_lats,
                lon=mid_lons,
                mode="markers",
                marker={"size": 8, "color": color, "opacity": 0},
                name=names[cluster_id],
                legendgroup=str(cluster_id),
                showlegend=False,
                hovertext=hover_labels,
                hoverinfo="text",
            )
        )

    # Station dots (one per unique station found in the routes)
    _add_station_markers(fig, routes)

    fig.update_layout(
        geo={
            "scope": "europe",
            "center": {"lat": 46.8, "lon": 2.3},
            "projection_scale": 5,
            "showland": True,
            "landcolor": "#F5F7FA",
            "showcoastlines": True,
            "coastlinecolor": "#CBD5E0",
            "showcountries": True,
            "countrycolor": "#CBD5E0",
            "showframe": False,
        },
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=520,
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,0.85)"},
    )
    chart_container(fig, title=title, how_to_read=how_to_read)

    # Coverage info
    total = len(routes)
    mapped = sum(
        1
        for r in routes
        if (parsed := _parse_route(r))
        and _get_coords(parsed[0])
        and _get_coords(parsed[1])
    )
    if mapped < total:
        st.caption(
            f"{mapped} / {total} liaisons représentées "
            f"(coordonnées manquantes pour {total - mapped})."
        )


def _add_station_markers(fig: go.Figure, routes: list[str]) -> None:
    """Add small grey dots for each unique station found in the routes."""
    stations: dict[str, tuple[float, float]] = {}
    for route in routes:
        parsed = _parse_route(route)
        if parsed is None:
            continue
        for station in parsed:
            coords = _get_coords(station)
            if coords and station not in stations:
                stations[station] = coords

    if not stations:
        return

    fig.add_trace(
        go.Scattergeo(
            lat=[c[0] for c in stations.values()],
            lon=[c[1] for c in stations.values()],
            mode="markers",
            marker={"size": 5, "color": "#4A5568", "symbol": "circle"},
            text=list(stations.keys()),
            hoverinfo="text",
            name="Gares",
            showlegend=False,
        )
    )
