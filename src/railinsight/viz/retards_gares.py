"""Figures de la Q2 : gares de départ à l'origine ou victimes des retards.

Chaque fonction reçoit un tableau et renvoie une figure Plotly, sans appel Streamlit.
"""

# Orange : couleur de la Q2 ; bleu : retards hérités ; gris : causes externes.
COULEURS_CATEGORIES = {
    "retard_heritees": "#003F88",
    "retard_non_heritees": "#FF6B35",
    "retard_externes": "#9BA3AE",
}

LIBELLES_CATEGORIES = {
    "retard_heritees": "Retards hérités",
    "retard_non_heritees": "Retards propres à la gare",
    "retard_externes": "Retards externes",
}

# Colonne de part correspondant à chaque colonne de volume.
PARTS_CATEGORIES = {
    "retard_heritees": "taux_heritees",
    "retard_non_heritees": "taux_non_heritees",
    "retard_externes": "taux_externes",
}