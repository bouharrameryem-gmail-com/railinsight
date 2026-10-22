# Datasheet — Régularité mensuelle TGV (AQST)

Documentation du jeu de données utilisé par RailInsight, suivant la structure
*Datasheets for Datasets* (Gebru et al., 2018), adaptée au contexte du projet.

---

## 1. Motivation
- **Pourquoi ce jeu de données a-t-il été créé ?**
  Publié par la SNCF (programme AQST — Amélioration de la Qualité du Service Attendu)
  pou r rendre compte publiquement de la ponctualité des circulations TGV, liaison par
  liaison, et des causes structurelles des retards.
- **Qui l'a créé ?**
  SNCF, mis à disposition sur son portail open data.
- **Qui l'a financé ?**
  SNCF (service public).

## 2. Composition

- **Source** : [ressources.data.sncf.com — Régularité mensuelle TGV (AQST)](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/)
- **Fichier local** : `data/raw/regularite-mensuelle-tgv-aqst.csv` (séparateur `;`, ~2,78 Mo)
- **Granularité** : une ligne = un mois × une liaison (gare de départ → gare d'arrivée)
- **Volume** : 12 907 lignes, 26 colonnes
- **Période couverte** : 2018-01 → 2026-09, sans mois manquant sur l'ensemble de la série
- **Liaisons** : 130 liaisons uniques (paires gare de départ / gare d'arrivée)
- **Services** : `National` (11 339 lignes) et `International` (1 568 lignes)

### Liste exhaustive des colonnes (26)

| # | Colonne | Type | Description |
|---|---|---|---|
| 1 | `Date` | texte (`YYYY-MM`) | Mois concerné |
| 2 | `Service` | catégorielle | `National` ou `International` |
| 3 | `Gare de départ` | texte | Gare d'origine de la liaison |
| 4 | `Gare d'arrivée` | texte | Gare de destination de la liaison |
| 5 | `Durée moyenne du trajet` | numérique (min) | Durée moyenne du trajet ce mois |
| 6 | `Nombre de circulations prévues` | numérique | Trains prévus ce mois pour cette liaison |
| 7 | `Nombre de trains annulés` | numérique | Nombre d'annulations |
| 8 | `Commentaire annulations` | texte libre | Récit d'incidents liés aux annulations (100 % vide dans ce fichier) |
| 9 | `Nombre de trains en retard au départ` | numérique | Trains partis en retard |
| 10 | `Retard moyen des trains en retard au départ` | numérique (min) | Moyenne calculée sur les seuls trains en retard au départ |
| 11 | `Retard moyen de tous les trains au départ` | numérique (min) | Moyenne calculée sur tous les trains (retard nul inclus) |
| 12 | `Commentaire retards au départ` | texte libre | Récit d'incidents liés aux retards au départ (100 % vide) |
| 13 | `Nombre de trains en retard à l'arrivée` | numérique | Trains arrivés en retard |
| 14 | `Retard moyen des trains en retard à l'arrivée` | numérique (min) | Moyenne sur les seuls trains en retard à l'arrivée |
| 15 | `Retard moyen de tous les trains à l'arrivée` | numérique (min) | Moyenne sur tous les trains à l'arrivée |
| 16 | `Commentaire retards à l'arrivée` | texte libre | Récit d'incidents (94,59 % vide, voir section 4) |
| 17 | `Nombre trains en retard > 15min` | numérique | Trains arrivés avec plus de 15 min de retard |
| 18 | `Retard moyen trains en retard > 15 (si liaison concurrencée par vol)` | numérique (min) | Spécifique aux liaisons en concurrence avec le transport aérien |
| 19 | `Nombre trains en retard > 30min` | numérique | Trains arrivés avec plus de 30 min de retard |
| 20 | `Nombre trains en retard > 60min` | numérique | Trains arrivés avec plus de 60 min de retard |
| 21 | `Prct retard pour causes externes` | % | Part des retards due à des causes externes (météo, colis suspects, etc.) |
| 22 | `Prct retard pour cause infrastructure` | % | Part due à l'infrastructure ferroviaire |
| 23 | `Prct retard pour cause gestion trafic` | % | Part due à la gestion du trafic |
| 24 | `Prct retard pour cause matériel roulant` | % | Part due au matériel roulant |
| 25 | `Prct retard pour cause gestion en gare et réutilisation de matériel` | % | Part due à la gestion en gare |
| 26 | `Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)` | % | Part due à la prise en charge des voyageurs |

## 3. Processus de collecte

- Données agrégées mensuellement par la SNCF à partir de ses systèmes d'exploitation,
  puis publiées en open data. RailInsight ne fait que télécharger le CSV publié,
  sans collecte ni traitement supplémentaire à la source.

## 4. Prétraitement / nettoyage requis

Constats faits sur le fichier actuel (2026-10-19), à prendre en compte dans tout
code d'analyse :

- **Champs texte multi-lignes** : les colonnes `Commentaire annulations`,
  `Commentaire retards au départ` et `Commentaire retards à l'arrivée` contiennent
  parfois des retours à la ligne et des guillemets (récits d'incidents). Un
  `read_csv` naïf peut mal découper les lignes ; utiliser un moteur de parsing
  tolérant (`engine="python"`) ou gérer explicitement le quoting.
- **Colonnes de commentaires presque toujours vides** :
  - `Commentaire annulations` : 100 % manquant (12 907 / 12 907)
  - `Commentaire retards au départ` : 100 % manquant
  - `Commentaire retards à l'arrivée` : 94,59 % manquant (seules ~5,4 % des lignes
    contiennent un récit d'incident)
- **Valeurs négatives dans des colonnes de retard moyen**, physiquement incohérentes
  mais présentes telles quelles dans la publication SNCF (anomalie connue du jeu de
  données, à ne pas corriger silencieusement — à signaler ou filtrer selon l'analyse) :
  - `Retard moyen de tous les trains au départ` : min -229,27, max 115,05 (170 lignes négatives)
  - `Retard moyen des trains en retard à l'arrivée` : min -40,11, max 299,6 (2 lignes négatives)
  - `Retard moyen de tous les trains à l'arrivée` : min -472,64, max 92 (122 lignes négatives)
  - `Retard moyen trains en retard > 15 (si liaison concurrencée par vol)` : min -4, max 299,6 (8 lignes négatives)
  - `Nombre trains en retard > 30min` : min -44, max 202 (43 lignes négatives)
- **Division par zéro potentielle** : `Nombre de circulations prévues` vaut 0 sur
  73 lignes. Tout calcul de taux (ex. taux d'annulation, taux de retard) doit gérer
  ce cas (filtrer ces lignes ou utiliser une garde explicite) avant de diviser.
- **Encodage** : certains caractères accentués dans les noms de colonnes et de gares
  nécessitent un décodage explicite (`utf-8-sig` recommandé) pour éviter les
  mismatchs de noms de colonnes.

## 5. Usages prévus

Le jeu de données est suffisant pour couvrir les 5 questions d'analyse du projet
(voir `README.md`), chacune s'appuyant sur un sous-ensemble différent de colonnes :

| # | Question | Colonnes principalement utilisées |
|---|---|---|
| 1 | Liaisons les moins fiables, évolution dans le temps | `Nombre de circulations prévues`, `Nombre de trains annulés`, `Nombre trains en retard > 15min`, `Date`, `Gare de départ`/`Gare d'arrivée` |
| 2 | Gares de départ : concentration de retards vs. victimes de correspondances | `Gare de départ`, `Gare d'arrivée`, `Nombre de trains en retard au départ`/`à l'arrivée`, `Retard moyen ...` |
| 3 | Clustering des liaisons par profil de ponctualité | L'ensemble des colonnes de retard/annulation + les 6 colonnes `Prct retard pour cause ...` comme variables de profil |
| 4 | Score de fiabilité par liaison, cartographié | `Nombre de circulations prévues`, `Nombre de trains annulés`, `Retard moyen de tous les trains à l'arrivée`, `Gare de départ`/`Gare d'arrivée` (nécessite un enrichissement géographique externe pour la carte, non inclus dans ce fichier) |
| 5 | Prédiction retard > 15/30 min selon mois et liaison | `Date`, `Gare de départ`/`Gare d'arrivée`, `Nombre trains en retard > 15min`/`> 30min`, `Nombre de circulations prévues` (variables explicatives) |

- Exploration dans les notebooks du dossier `notebooks/` (lecture directe du CSV,
  sans dépendance au package `railinsight`).
- Alimentation de la webapp Streamlit via `railinsight.backend` après nettoyage.

### Usages déconseillés

- Ne pas utiliser ce jeu de données pour attribuer une responsabilité individuelle
  (humaine) dans les retards : les causes publiées sont agrégées et catégorielles,
  pas nominatives.
- Ne pas extrapoler au-delà des liaisons TGV couvertes (le jeu de données ne couvre
  ni les TER, ni les Intercités, ni le fret).

## 6. Distribution

- Le fichier est redistribué tel quel dans `data/raw/`, conformément à la licence
  ouverte de la SNCF. Voir la page source pour les conditions de réutilisation :
  <https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/>

## 7. Considérations éthiques et confidentialité

- **Données personnelles** : aucune. Le jeu de données est agrégé à l'échelle
  mensuelle et par liaison ; il ne contient aucune information sur des personnes
  physiques (ni voyageurs, ni conducteurs, ni personnel SNCF).
- **Champs texte libre** : les colonnes `Commentaire annulations`,
  `Commentaire retards au départ` et `Commentaire retards à l'arrivée` sont des
  récits d'incidents rédigés par la SNCF (ex. intempéries, incidents techniques).
  Elles ne mentionnent pas de personnes nommément, mais restent du texte libre à
  ne pas réutiliser sans vérification si de nouvelles versions du fichier
  venaient à en contenir.
- **Biais potentiel** : les lignes à faible volume (`Nombre de circulations
  prévues` petit) peuvent produire des taux de retard/incident extrêmes (proches
  de 0 % ou 100 %) qui ne reflètent pas une tendance structurelle. À pondérer par
  le volume plutôt qu'à interpréter un taux brut isolément.

## 8. Maintenance


- Le fichier `data/raw/regularite-mensuelle-tgv-aqst.csv` est un instantané figé,
  téléchargé manuellement. Il n'est pas mis à jour automatiquement.
- Pour rafraîchir les données avec les mois publiés après 2026-09, retélécharger le
  CSV depuis la source ci-dessus et remplacer le fichier dans `data/raw/`, puis
  mettre à jour les chiffres de cette datasheet (nombre de lignes, période couverte).
