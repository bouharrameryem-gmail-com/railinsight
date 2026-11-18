"""Phrases de la page Q2, rédigées à partir des chiffres calculés.

Chaque fonction reçoit des faits (résumé, portrait, évolution) et renvoie du
texte, sans appel Streamlit. Les seuils qui décident d'une formulation sont
regroupés en tête de module.
"""

from typing import Literal

import pandas as pd

from railinsight.analysis.causes_retards import (
    Evolution,
    PortraitGare,
    ResumeRetardsGares,
)
from railinsight.utils.formatting import fmt_month, fmt_number, fmt_pct

# Moins de 2 points d'écart à la moyenne : la gare est « proche de la moyenne ».
ECART_NEUTRE = 0.02
# Moins de 2 points d'évolution entre deux années : la part est « stable ».
VARIATION_STABLE = 0.02
# Au moins la moitié des pires mois en été : on le signale.
PART_ETE_MARQUEE = 0.5


def _points(ecart: float) -> str:
    """Écrit un écart entre deux parts en points : « 3 points »."""
    nombre = round(abs(ecart) * 100)
    return f"{nombre} point{'s' if nombre > 1 else ''}"


def _rang(rang: int) -> str:
    """Écrit un rang en français : « 1re », « 2e »."""
    return "1re" if rang == 1 else f"{rang}e"


def titre_evolution_reseau(evolution: Evolution | None) -> str:
    """Titre du graphique des parts : l'évolution des retards importés."""
    if evolution is None:
        return "Part de chaque famille de causes, année par année"
    debut, fin = evolution.annee_debut, evolution.annee_fin
    if abs(evolution.ecart) < VARIATION_STABLE:
        return (
            "La part des retards importés reste stable autour de "
            f"{fmt_pct(evolution.valeur_fin, 0)} entre {debut} et {fin}"
        )
    return (
        f"La part des retards importés passe de {fmt_pct(evolution.valeur_debut, 0)} "
        f"en {debut} à {fmt_pct(evolution.valeur_fin, 0)} en {fin}"
    )


def titre_constat(resume: ResumeRetardsGares) -> str:
    """Titre de la section « Qui fabrique, qui encaisse »."""
    if resume.gare_propres == resume.gare_heritees:
        return (
            f"{resume.gare_propres} est en tête des deux côtés : elle fabrique "
            "et encaisse le plus de retards"
        )
    return (
        f"{resume.gare_propres} fabrique le plus de retards, "
        f"{resume.gare_heritees} en encaisse le plus"
    )


def texte_constat(resume: ResumeRetardsGares) -> str:
    """Encadré de la section 2 : concentration des retards et effet de taille."""
    return (
        f"Les 3 premières gares concentrent {fmt_pct(resume.part_top3_propres)} "
        "des retards nés sur place. En volume, les gares les plus desservies "
        "dominent mécaniquement : la section suivante les compare à trafic égal."
    )


def titre_trafic_egal(resume: ResumeRetardsGares) -> str:
    """Titre de la section « À trafic égal »."""
    if resume.gare_part_heritee is None or resume.part_heritee_max is None:
        return "Aucune gare n'atteint le seuil choisi"
    return (
        f"Rapportée à son trafic, {resume.gare_part_heritee} est la plus exposée "
        f"aux retards importés : {fmt_pct(resume.part_heritee_max)}, contre "
        f"{fmt_pct(resume.part_heritees)} en moyenne"
    )


def titre_carrefours(nombre: int) -> str:
    """Titre de la section « Les carrefours »."""
    if nombre == 0:
        return "Aucune gare n'est des deux côtés"
    if nombre == 1:
        return "Une gare fabrique et encaisse à la fois"
    return f"{nombre} gares fabriquent et encaissent à la fois"


def decrire_profil(portrait: PortraitGare) -> str:
    """Situe la part de retards importés de la gare par rapport à la moyenne."""
    debut = (
        f"À {portrait.gare}, {fmt_pct(portrait.part_heritee)} des retards "
        "sont importés"
    )
    moyenne = fmt_pct(portrait.part_heritee_moyenne)
    ecart = portrait.part_heritee - portrait.part_heritee_moyenne
    if ecart >= ECART_NEUTRE:
        return (
            f"{debut}, {_points(ecart)} de plus que la moyenne des gares "
            f"({moyenne}) : elle est plus exposée que les autres aux retards "
            "venus d'ailleurs."
        )
    if ecart <= -ECART_NEUTRE:
        return (
            f"{debut}, {_points(ecart)} de moins que la moyenne des gares "
            f"({moyenne}) : elle est moins exposée que les autres aux retards "
            "venus d'ailleurs."
        )
    return f"{debut}, proche de la moyenne des gares ({moyenne})."


def decrire_rang(portrait: PortraitGare) -> str:
    """Donne le rang de la gare dans les deux classements en volume."""
    return (
        f"Elle est la {_rang(portrait.rang_propres)} gare sur "
        f"{portrait.nombre_gares} pour les retards nés sur place, et la "
        f"{_rang(portrait.rang_heritees)} pour les retards importés."
    )


def decrire_tendance(evolution: Evolution | None) -> str | None:
    """Qualifie l'évolution de la part de retards importés, si elle est connue."""
    if evolution is None:
        return None
    debut, fin = evolution.annee_debut, evolution.annee_fin
    if abs(evolution.ecart) < VARIATION_STABLE:
        return (
            f"Sa part de retards importés est stable entre {debut} et {fin}, "
            f"autour de {fmt_pct(evolution.valeur_fin, 0)}."
        )
    sens = "progresse" if evolution.ecart > 0 else "recule"
    return (
        f"Sa part de retards importés {sens} de {_points(evolution.ecart)} "
        f"entre {debut} et {fin}."
    )


def decrire_pic(portrait: PortraitGare) -> str | None:
    """Nomme le mois le plus chargé et signale un éventuel effet de l'été."""
    if portrait.mois_pic is None:
        return None
    mois = fmt_month(pd.Period(portrait.mois_pic, freq="M"))
    phrase = (
        f"Son mois le plus chargé est {mois}, avec "
        f"{fmt_number(portrait.volume_pic)} trains arrivés en retard."
    )
    total = portrait.pires_mois_total
    if total and portrait.pires_mois_ete / total >= PART_ETE_MARQUEE:
        phrase += (
            f" L'été revient souvent : {portrait.pires_mois_ete} de ses {total} "
            "pires mois tombent entre juin et août."
        )
    return phrase


def rediger_portrait(
    portrait: PortraitGare,
    vue: Literal["annee", "mois"],
    inclut_2020: bool,
    minimum: int,
) -> list[str]:
    """Rédige 2 à 4 phrases sur la gare, selon les réglages de l'utilisateur.

    Args:
        portrait: Faits calculés par `dresser_portrait_gare`.
        vue: `annee` donne la tendance ; `mois` donne le mois le plus chargé.
        inclut_2020: Si True, prévient que 2020 fausse les volumes.
        minimum: Seuil choisi par l'utilisateur ; en dessous, les parts de la
            gare sont signalées comme fragiles.

    Returns:
        Les phrases, dans l'ordre de lecture.
    """
    phrases = [decrire_profil(portrait), decrire_rang(portrait)]
    if vue == "annee":
        temps = decrire_tendance(portrait.evolution)
    else:
        temps = decrire_pic(portrait)
    if temps is not None:
        phrases.append(temps)
    if portrait.total_retards < minimum:
        phrases.append(
            f"Avec {fmt_number(portrait.total_retards)} retards seulement, ces "
            "parts sont à lire avec prudence."
        )
    elif inclut_2020:
        phrases.append(
            "2020 est incluse : la chute de cette année-là traduit moins de "
            "trains pendant les confinements, pas une meilleure ponctualité."
        )
    return phrases