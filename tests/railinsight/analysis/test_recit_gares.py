"""Tests de la rédaction des phrases de la page Q2."""

from dataclasses import replace

import pandas as pd

from railinsight.analysis.causes_retards import (
    Evolution,
    PortraitGare,
    ResumeRetardsGares,
)
from railinsight.analysis.recit_gares import (
    decrire_pic,
    decrire_profil,
    decrire_rang,
    decrire_tendance,
    rediger_portrait,
    texte_constat,
    titre_carrefours,
    titre_constat,
    titre_evolution_reseau,
    titre_trafic_egal,
)

RESUME = ResumeRetardsGares(
    nombre_gares=4,
    total_retards=2300.0,
    part_propres=0.43,
    part_heritees=0.24,
    part_externes=0.33,
    gare_propres="PARIS",
    volume_propres=500.0,
    part_top3_propres=0.9,
    gare_heritees="LYON",
    volume_heritees=400.0,
    nombre_significatives=2,
    gare_part_heritee="LYON",
    part_heritee_max=0.4,
)

PORTRAIT = PortraitGare(
    gare="LYON",
    total_retards=1000.0,
    part_heritee=0.4,
    part_heritee_moyenne=0.24,
    rang_propres=2,
    rang_heritees=1,
    nombre_gares=4,
    evolution=Evolution(2019, 0.30, 2025, 0.40),
    mois_pic=pd.Timestamp("2023-07-01"),
    volume_pic=120.0,
    pires_mois_ete=7,
    pires_mois_total=12,
)


def test_titre_evolution_reseau():
    assert "année par année" in titre_evolution_reseau(None)
    assert "reste stable" in titre_evolution_reseau(Evolution(2019, 0.24, 2025, 0.25))
    titre = titre_evolution_reseau(Evolution(2019, 0.20, 2025, 0.30))
    assert titre.startswith("La part des retards importés passe de 20")
    assert "en 2025" in titre


def test_titre_constat_selon_les_gares_en_tete():
    assert titre_constat(RESUME) == (
        "PARIS fabrique le plus de retards, LYON en encaisse le plus"
    )
    meme_gare = replace(RESUME, gare_heritees="PARIS")
    assert "en tête des deux côtés" in titre_constat(meme_gare)


def test_texte_constat_donne_la_concentration():
    assert "90,0" in texte_constat(RESUME)


def test_titre_trafic_egal():
    assert titre_trafic_egal(RESUME).startswith("Rapportée à son trafic, LYON")
    sans_gare = replace(RESUME, gare_part_heritee=None, part_heritee_max=None)
    assert titre_trafic_egal(sans_gare) == "Aucune gare n'atteint le seuil choisi"


def test_titre_carrefours():
    assert titre_carrefours(0) == "Aucune gare n'est des deux côtés"
    assert titre_carrefours(1) == "Une gare fabrique et encaisse à la fois"
    assert titre_carrefours(3) == "3 gares fabriquent et encaissent à la fois"


def test_profil_au_dessus_en_dessous_ou_proche_de_la_moyenne():
    assert "16 points de plus" in decrire_profil(PORTRAIT)
    assert "14 points de moins" in decrire_profil(replace(PORTRAIT, part_heritee=0.1))
    assert "proche de la moyenne" in decrire_profil(
        replace(PORTRAIT, part_heritee=0.25)
    )


def test_rang_en_francais():
    phrase = decrire_rang(PORTRAIT)

    assert "la 2e gare sur 4" in phrase
    assert "la 1re pour les retards importés" in phrase


def test_tendance():
    assert decrire_tendance(None) is None
    assert "progresse de 10 points entre 2019 et 2025" in decrire_tendance(
        PORTRAIT.evolution
    )
    assert "recule" in decrire_tendance(Evolution(2019, 0.4, 2025, 0.3))
    assert "est stable" in decrire_tendance(Evolution(2019, 0.30, 2025, 0.31))


def test_pic_et_effet_de_l_ete():
    phrase = decrire_pic(PORTRAIT)
    assert "juillet 2023" in phrase
    assert "7 de ses 12 pires mois" in phrase

    sans_ete = decrire_pic(replace(PORTRAIT, pires_mois_ete=2))
    assert "L'été" not in sans_ete

    assert decrire_pic(replace(PORTRAIT, mois_pic=None)) is None


def test_portrait_vue_annuelle_ou_mensuelle():
    annuel = rediger_portrait(PORTRAIT, "annee", inclut_2020=False, minimum=1000)
    assert len(annuel) == 3
    assert "progresse" in annuel[2]

    mensuel = rediger_portrait(PORTRAIT, "mois", inclut_2020=False, minimum=1000)
    assert "mois le plus chargé" in mensuel[2]

    sans_tendance = replace(PORTRAIT, evolution=None)
    assert len(rediger_portrait(sans_tendance, "annee", False, 1000)) == 2


def test_portrait_mises_en_garde():
    avec_2020 = rediger_portrait(PORTRAIT, "annee", inclut_2020=True, minimum=1000)
    assert avec_2020[-1].startswith("2020 est incluse")

    fragile = rediger_portrait(PORTRAIT, "annee", inclut_2020=True, minimum=5000)
    assert "à lire avec prudence" in fragile[-1]
    assert not any(phrase.startswith("2020") for phrase in fragile)
