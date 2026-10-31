"""Position des gares sur le schéma du réseau.

Le jeu de données ne contient pas les coordonnées des gares : on les place pour que
les gares reliées entre elles soient proches, sans lien avec la géographie.
"""

from collections.abc import Iterable

import networkx as nx


def positions_gares(
    aretes: Iterable[tuple[str, str]],
) -> dict[str, tuple[float, float]]:
    """Place les gares de façon reproductible, comme dans le notebook Q4."""
    graphe = nx.Graph()
    graphe.add_edges_from(sorted(set(aretes)))
    positions = nx.spring_layout(graphe, seed=3, iterations=200)
    return {gare: (float(x), float(y)) for gare, (x, y) in positions.items()}
