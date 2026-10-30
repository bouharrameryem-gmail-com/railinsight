"""Définit le schéma attendu du fichier CSV de régularité SNCF."""

from dataclasses import dataclass

TEXTE = "texte"
NOMBRE = "nombre"


@dataclass(frozen=True)
class Colonne:
    """Décrit une colonne du CSV : nom source, nom interne et type."""

    source: str
    nom: str
    genre: str


SCHEMA: tuple[Colonne, ...] = (
    Colonne("Date", "date", TEXTE),  # format AAAA-MM
    Colonne("Service", "service", TEXTE),
    Colonne("Gare de départ", "gare_depart", TEXTE),
    Colonne("Gare d'arrivée", "gare_arrivee", TEXTE),
    Colonne("Durée moyenne du trajet", "duree_moyenne", NOMBRE),
    Colonne("Nombre de circulations prévues", "prevus", NOMBRE),
    Colonne("Nombre de trains annulés", "annules", NOMBRE),
    Colonne("Nombre de trains en retard au départ", "retards_depart", NOMBRE),
    # Avec « retardes » : moyenne sur les seuls trains en retard.
    # Sans « retardes » : moyenne sur tous les trains.
    Colonne(
        "Retard moyen des trains en retard au départ",
        "retard_moyen_retardes_depart",
        NOMBRE,
    ),
    Colonne("Retard moyen de tous les trains au départ", "retard_moyen_depart", NOMBRE),
    Colonne("Nombre de trains en retard à l'arrivée", "retards_arrivee", NOMBRE),
    Colonne(
        "Retard moyen des trains en retard à l'arrivée",
        "retard_moyen_retardes_arrivee",
        NOMBRE,
    ),
    Colonne(
        "Retard moyen de tous les trains à l'arrivée", "retard_moyen_arrivee", NOMBRE
    ),
    Colonne("Nombre trains en retard > 15min", "retards_sup_15min", NOMBRE),
    Colonne(
        "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)",
        "retard_moyen_sup_15min_vol",
        NOMBRE,
    ),
    Colonne("Nombre trains en retard > 30min", "retards_sup_30min", NOMBRE),
    Colonne("Nombre trains en retard > 60min", "retards_sup_60min", NOMBRE),
    Colonne("Prct retard pour causes externes", "prct_cause_externe", NOMBRE),
    Colonne(
        "Prct retard pour cause infrastructure", "prct_cause_infrastructure", NOMBRE
    ),
    Colonne("Prct retard pour cause gestion trafic", "prct_cause_trafic", NOMBRE),
    Colonne("Prct retard pour cause matériel roulant", "prct_cause_materiel", NOMBRE),
    Colonne(
        "Prct retard pour cause gestion en gare et réutilisation de matériel",
        "prct_cause_gare",
        NOMBRE,
    ),
    Colonne(
        "Prct retard pour cause prise en compte voyageurs "
        "(affluence, gestions PSH, correspondances)",
        "prct_cause_voyageurs",
        NOMBRE,
    ),
)
