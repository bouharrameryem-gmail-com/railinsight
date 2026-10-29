# Datasheet — Régularité mensuelle TGV (AQST)

Documentation du jeu de données utilisé par RailInsight, suivant la structure
*Datasheets for Datasets* (Gebru et al., 2021, CACM), adaptée au contexte du projet.

- **Partie A** (sections 1 à 8) : le jeu **source**, tel que publié par la SNCF.
- **Partie B** (sections 9 à 17) : notre jeu **dérivé** — ce que nous avons fait des
  données, nos décisions et leurs justifications.

Correspondance avec les sept rubriques de Gebru et al. :

| Rubrique | Jeu source | Jeu dérivé |
|---|---|---|
| Motivation | 1 | 9 |
| Composition | 2 | 13 (variables dérivées) |
| Collection | 3 | 10.0 (provenance) |
| Preprocessing | 4 | 10, 11, 12 |
| Uses | 5, 7 | 14 |
| Distribution | 6 | 16 |
| Maintenance | 8 | 15 |

---

# Partie A — Jeu source

## 1. Motivation
- **Pourquoi ce jeu de données a-t-il été créé ?**
  Pour rendre compte publiquement de la ponctualité des TGV, liaison par liaison, et
  des causes des retards. Les liaisons et indicateurs suivent le format de l'AQST
  (Autorité de la qualité de service dans les transports), qui publie des indicateurs
  de régularité comparables entre modes de transport.
- **Qui l'a créé ?**
  SNCF Voyageurs (producteur), sur le portail SNCF Open Data.
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
- **Gares** : 59 gares distinctes

### Ce qui est représenté, ce qui manque

- **Population** : une sélection de liaisons TGV, pas tout le réseau. Les TER,
  Intercités et le fret sont absents (jeux séparés sur le portail).
- **Biais de représentation** : le réseau est très centré sur Paris : **108 liaisons
  sur 130** et **83,7 % des lignes** ont Paris comme origine ou destination. Les
  liaisons province–province et internationales sont peu nombreuses ; un résultat
  « moyen » reflète surtout les radiales parisiennes.
- **Unité observée** : le train au terminus de la liaison, pas le voyageur. Le retard
  vécu par un voyageur (correspondance manquée, arrêt intermédiaire) n'est pas mesuré.
- **Valeurs manquantes et mécanismes** (session 3) :

  | Manque | Mécanisme probable | Conséquence |
  |---|---|---|
  | Colonnes « Commentaire » (94 à 100 % vides) | Structurel : champ rarement saisi | Inutilisables |
  | Mois à 0 train prévu (73 lignes) | Non aléatoire : liaison non exploitée (confinement 2020) | Pas de taux calculable |
  | Parts de causes à 0 malgré des retards (80 lignes) | Non aléatoire : saisie absente, codée en 0 | Zéro à lire comme manquant |
  | `> 30 min` / `> 60 min` en janvier–mars 2025 | Non aléatoire : défaut de publication | Colonnes inexploitables sur 3 mois |

  Aucun de ces manques n'est complètement aléatoire (MCAR) : supprimer les lignes
  concernées biaise les résultats vers les périodes et liaisons « normales ».

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

- **Mesure** : les heures d'arrivée sont relevées par des capteurs qui détectent le
  passage du train à l'entrée en gare, exceptionnellement par un suivi manuel.
  Précision : la minute, **arrondie à la minute inférieure**.
- **Définition « à l'heure » (composite)**, au terminus :
  - retard < 5 min pour un trajet de moins de 1 h 30 ;
  - retard < 10 min entre 1 h 30 et 3 h ;
  - retard < 15 min au-delà de 3 h.
- **Agrégation** : mensuelle, par liaison, par SNCF Voyageurs. Un même TGV peut
  compter dans plusieurs liaisons (selon la source).
- **Périodicité de publication** : semestrielle (selon le portail). Dernière mise à
  jour des données : 2026-10-02.
- **Consentement** : sans objet, aucune donnée personnelle (section 7).
- **Notre collecte** : téléchargement manuel du CSV complet depuis le portail, sans
  filtre ni transformation.

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
  - `Nombre trains en retard > 30min` : min -44, max 202 (43 lignes négatives,
    toutes en janvier–mars 2025 : voir section 11)
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
| 4 | Score de fiabilité par liaison, cartographié | `Nombre de circulations prévues`, `Nombre de trains annulés`, `Retard moyen de tous les trains à l'arrivée`, `Gare de départ`/`Gare d'arrivée` (le fichier ne contient pas la position des gares : le schéma du réseau est topologique, pas géographique) |
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

- **Licence** : [Open Database License (ODbL)](https://data.sncf.com/pages/cgu/A1#A1).
  Elle impose de **citer la source** (SNCF Voyageurs — SNCF Open Data) et, si une base
  dérivée est rendue publique, de la partager **sous la même licence** (section 16).
- Le fichier est redistribué tel quel dans `data/raw/`. Page source :
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
- **Risque de stigmatisation** : un classement des liaisons « les moins fiables » peut
  être lu comme un jugement sur des territoires ou des équipes. Il reflète aussi la
  durée des trajets et la charge des axes (section 14).

## 8. Maintenance

- **Source** : maintenue par SNCF Voyageurs ; erreurs à signaler via le formulaire de
  contact du portail SNCF Open Data.
- Le fichier `data/raw/regularite-mensuelle-tgv-aqst.csv` est un instantané figé,
  téléchargé manuellement. Il n'est pas mis à jour automatiquement.
- Pour rafraîchir les données avec les mois publiés après 2026-09, retélécharger le
  CSV depuis la source ci-dessus et remplacer le fichier dans `data/raw/`, puis
  suivre la procédure de la section 15.

---

# Partie B — Jeu dérivé RailInsight

## 9. Motivation du jeu dérivé

- **Thème** : la **fiabilité** des TGV, c'est-à-dire la capacité d'une liaison à faire
  circuler les trains prévus, à l'heure.
- **Nos 4 questions** :

  | # | Question | Responsable |
  |---|---|---|
  | Q1 | Quelles liaisons sont les moins fiables, et la situation se dégrade-t-elle ? | Michelle |
  | Q2 | Quelles gares de départ concentrent les retards, lesquelles les subissent ? | Éric |
  | Q3 | Peut-on regrouper les liaisons par profil de ponctualité ? | Bachelard |
  | Q4 | Quel score de fiabilité par liaison, cartographié sur le réseau ? | Meryem |

  Le `README.md` mentionne une 5ᵉ question (prédiction des retards > 15/30 min),
  non attribuée à ce jour.
- **Pourquoi un jeu dérivé ?** Le fichier source contient des valeurs impossibles,
  des zéros qui masquent des valeurs manquantes et des anomalies propres à 2025
  (section 11). Les quatre questions ont besoin des **mêmes** taux, calculés de la
  même façon, pour que leurs résultats soient comparables. Le jeu dérivé fixe ces
  règles une fois pour toutes.
- **Où il vit dans le code** :
  - lecture et contrat de schéma : `src/railinsight/analysis/donnees.py`
    (noms de colonnes propres, colonnes « Commentaire » écartées) ;
  - règles communes : `src/railinsight/analysis/nettoyage.py` ;
  - paramètres : `config/defaut.yaml` ;
  - règles spécifiques : notebooks et modules de chaque question.

## 10. Décisions de nettoyage et justifications

### 10.0 Provenance : du fichier brut au jeu dérivé

```text
CSV SNCF (data/raw/, intact)
  → lire_donnees()          contrôle du schéma, noms propres, types numériques
  → nettoyer_regularite()   règles communes (10.1), aucune ligne retirée
  → règles D1–D10 (10.2), traitement 2025 (11), exclusions (12)
  → variables dérivées (13) → résultats Q1 à Q4 et application Streamlit
```

Le fichier brut n'est jamais modifié : toute la chaîne est rejouable depuis lui.

**Principe** : on invalide le **champ**, pas la ligne. Une ligne qui contient une
valeur impossible contient aussi d'autres mesures valides ; la supprimer entière
faisait perdre 106 lignes, contre 73 avec cette règle.

### 10.1 Règles communes (implémentées dans `nettoyage.py`)

`nettoyer_regularite()` ne supprime **aucune** ligne (retirer des lignes est une
décision d'analyse) :

1. `date` convertie en date, `mois` au format `AAAA-MM` ;
2. noms de gares normalisés : espaces (y compris insécables) réduits, MAJUSCULES ;
3. doublons sur *(mois, gare de départ, gare d'arrivée)* **signalés**, pas supprimés ;
4. ajout des variables `liaison`, `gare_a`, `gare_b`, `circules`, `minutes_retard`,
   `circules_mesures` (section 13).

Outils optionnels, appelés explicitement par chaque analyse : `retirer_sans_train`,
`filtrer_periode`, `invalider_hors_bornes`, `retirer_doublons`, `taux` (division
protégée : dénominateur nul → NaN).

### 10.2 Invalidation champ par champ

Règles établies dans `notebooks/Q3_punctuality_profiles_EDA.ipynb` (section I.5 bis).
Elles ne sont **pas encore** portées dans `nettoyage.py`.

| Code | Anomalie | Volume | Traitement | Justification |
|---|---|---:|---|---|
| D1 | Comptage négatif (`> 30 min`) | 43 valeurs | → NaN | Un nombre de trains ne peut pas être négatif |
| D2 | 0 train prévu | **73 lignes** | **Ligne retirée** | Mois où la liaison n'a pas circulé (surtout avril–mai 2020) : aucune base pour un taux |
| D3 | Annulés > prévus | 0 (couvert par D2) | → NaN | Impossible |
| D4a | `> 60 min` > `> 30 min` | 354 valeurs | `> 60 min` → NaN | Seuils emboîtés violés (voir section 11) |
| D4b | `> 30 min` > `> 15 min` | 3 valeurs | `> 30 min` → NaN | Seuils emboîtés violés |
| D4c | `> 15 min` > trains circulés | 65 valeurs | `> 15`, `> 30`, `> 60` → NaN | Plus de trains en retard que de trains circulés |
| D5 | Durée du trajet ≤ 0 | 73 valeurs | Médiane de la liaison | Mêmes lignes que D2 |
| D6 | Retard moyen des trains en retard ≤ 0 sans train en retard | 192 valeurs | → NaN | **Zéro qui masque un manquant** : moyenne non définie |
| D6b | Même champ = 0 avec des trains en retard | 38 valeurs | → NaN | Une moyenne de retards positifs ne peut pas valoir 0 |
| D7 | Parts de causes toutes à 0 alors qu'il y a des retards | 80 lignes | → NaN | **Zéro qui masque un manquant** : causes non saisies |
| D7b | Somme des parts de causes éloignée de 100 | 202 lignes → NaN ; 7 renormalisées | Voir ci-dessous | Parts incohérentes |
| D8 | Retard moyen de tous les trains < −15 min | 11 (arrivée) + 5 (départ) | → NaN | Erreurs grossières (minimum −472 min) |
| D9 | Colonnes « Commentaire » + retard moyen > 15 min « si concurrence aérienne » | 4 colonnes | Écartées | 94 à 100 % vides ou non interprétables |
| D10 | 0 train circulé (tout annulé) | — | **Conservé** | 100 % d'annulation est une mesure, pas une erreur |

**Renormalisation des causes (D7b)** : si la somme $S = \sum_i p_i$ des six parts
est comprise entre 95 et 105, on la ramène à 100 : $p_i' = 100 \cdot p_i / S$.
Au-delà, les six parts de la ligne passent à NaN.

**Résultat** : 12 907 lignes → **12 834 lignes** conservées.

> Les volumes D4c, D6, D6b, D7b et D8 proviennent du notebook Q3. Les volumes D1,
> D2, D4a, D4b et D7 ont été recontrôlés sur le CSV du 2026-09.

### 10.3 Ce que fait chaque question aujourd'hui

| Question | Source | Unité | Périmètre | Lignes retirées | Invalidations |
|---|---|---|---|---|---|
| Q1 (`analysis/reliability.py`, notebook `01_liaisons_moins_fiables`) | `lire_donnees` + `nettoyer_regularite` | Liaison orientée | National + International | 0 train prévu (`retirer_sans_train`) | Aucune |
| Q2 (`eric-explore2`) | CSV brut | Gare de départ | **National seulement** | Aucune | Aucune |
| Q3 (`Q3_punctuality_profiles_EDA`) | CSV brut, nettoyage dans le notebook | Liaison orientée | National + International | D2 ; liaisons < 24 mois | D1 à D10 |
| Q4 (`score_fiabilite`) | CSV brut | Liaison **non orientée** (65 retenues) | National + International | 0 train prévu ; liaisons < 100 trains | Aucune |

Conséquences des écarts :

- **Q4** utilise `Retard moyen de tous les trains à l'arrivée` sans la règle D8 : les
  valeurs aberrantes (jusqu'à −472 min) entrent dans le calcul des minutes de retard
  et peuvent remonter artificiellement le score de certaines liaisons.
- **Q2** filtre sur `National` : pour les 14 liaisons doublées de l'été 2025
  (section 11.2), la partie `International` du flux est perdue.
- **Q2** ne retire pas les mois à 0 train prévu ; sans effet sur des sommes de
  volumes, mais à retirer dès qu'on calcule un taux.

**À harmoniser** : les quatre questions devraient partir de la même sortie de
`nettoyer_regularite()` complétée par les règles D1 à D10.

## 11. Anomalies de 2025

### 11.1 Janvier–mars 2025 : colonnes « > 30 min » et « > 60 min » inutilisables

Constats sur le fichier (363 lignes, 121 liaisons par mois, comme les mois voisins) :

- `> 30 min` vaut **0 sur 304 lignes** et est **négatif sur 43** (ce sont les
  43 valeurs négatives de tout le fichier) ;
- `> 60 min` dépasse `> 30 min` sur **354 lignes** (aucune hors de ces 3 mois) ;
- rapport au nombre de trains `> 15 min`, sur l'ensemble du réseau :

  | Période | `> 30` / `> 15` | `> 60` / `> 15` |
  |---|---:|---:|
  | Mois habituels (2024-07 → 2026-09) | 0,44 à 0,60 | 0,14 à 0,33 |
  | 2025-01 → 2025-03 | **≈ −0,02** | **≈ 0,49** |

**Interprétation** : la colonne `> 60 min` porte, ces trois mois, un volume
correspondant à celui habituellement publié dans `> 30 min`, et `> 30 min` n'est pas
renseignée (zéros). C'est un **trou de publication** combiné à un **changement
apparent de définition** des colonnes de retard grave.

**Décision** : les colonnes `> 30 min` et `> 60 min` de janvier à mars 2025 sont
traitées comme **manquantes** (363 lignes). `> 15 min`, annulations et retards moyens
restent utilisables.

> **Point ouvert** : le notebook Q3 (section I.5 bis) conclut à une définition
> « par tranches » ([30, 60[ et ≥ 60 min). Les rapports ci-dessus ne la soutiennent pas
> (une tranche [30, 60[ représenterait ≈ 0,3 du `> 15 min`, pas ≈ 0). Il signale
> aussi des liaisons absentes début 2025, alors que le fichier compte 121 liaisons
> chaque mois. À vérifier sur le portail SNCF et à trancher en équipe.

### 11.2 Été 2025 : lignes en double

- **84 lignes = 42 paires** sur *(mois, gare de départ, gare d'arrivée)*, uniquement
  en **juillet, août et septembre 2025** ;
- 14 liaisons concernées (axes Paris Lyon ↔ Bellegarde, Chambéry, Dijon, Mâcon,
  Mulhouse ; Paris Est ↔ Strasbourg ; Lyon ↔ Marseille) ;
- chaque paire = une ligne `National` + une ligne `International` ;
- les trains prévus ne sont **jamais identiques** dans une paire (0 / 42).

**Décision** : ce sont deux flux distincts d'une même liaison. Pour un indicateur par
liaison, on **additionne** les comptages des deux lignes. Ne **pas** utiliser
`retirer_doublons()` (qui garde la dernière ligne) sur ces données.

### 11.3 Conséquence

Toute tendance qui traverse 2025 sur les retards graves (`> 30`, `> 60 min`) est
faussée tant que 11.1 n'est pas appliqué. Q1, Q2 et Q4 n'utilisent pas ces colonnes et
ne sont pas touchées par 11.1 ; seule Q3 l'est (parts > 30 et > 60 min).

## 12. Mois exceptionnels (grèves, confinements)

### 12.1 Liste documentée

Établie à partir d'événements connus, puis **confirmée par les données** : z-score
robuste du réseau (médiane / MAD) comparé au même mois calendaire des autres années ;
confirmé si $z > 3{,}5$. Source : notebook Q3, section I.9.

| Mois | Événement | Confirmé |
|---|---|---|
| 2018-04, 2018-05, 2018-06 | Grève perlée (réforme ferroviaire) | Oui (avril : 33 % d'annulations) |
| 2019-12, 2020-01 | Grève contre la réforme des retraites | Oui |
| ~~2020-02~~ | Fin de la grève des retraites | **Non** ($z = -0{,}1$) : retiré de la liste |
| 2020-03, 2020-04, 2020-05 | 1er confinement | Oui (avril : 47 % d'annulations) |
| 2020-06 | Plan de transport réduit | Oui (limite) |
| 2020-11, 2020-12 | 2e confinement | Oui |
| 2021-04, 2021-05 | 3e confinement, restrictions | Oui (avril : 37,5 % d'annulations) |
| 2022-12 | Grève des contrôleurs (Noël) | Oui |
| 2023-01, 2023-02, 2023-03 | Grèves des retraites | Oui |
| 2024-02 | Grève des contrôleurs (vacances d'hiver) | Oui |
| 2026-06 | Grève nationale du 10 juin | Oui |

**Total : 19 mois.** Les étés, régulièrement mauvais, ne sont **pas** exclus : ils
font partie du fonctionnement normal (chaleur, travaux, affluence).

### 12.2 Impact mesuré (clustering Q3)

| Variante | Mois exclus | Accord (ARI) avec la liste documentée | Écart moyen retards > 15 min | Écart moyen annulations |
|---|---:|---:|---:|---:|
| Aucune exclusion | 0 | 0,62 | 0,19 pt | 1,95 pt |
| Liste documentée | 20* | 1,00 | — | — |
| Détection automatique | 25 | 0,87 | 0,44 pt | 0,17 pt |

\* calcul fait avant le retrait de 2020-02.

Garder les mois de crise bouleverse les groupes, surtout via les annulations : les
profils mesureraient alors l'exposition aux grèves, pas la qualité d'exploitation
habituelle. La détection automatique retire aussi des mois simplement mauvais et
biaise les retards à la baisse.

### 12.3 Traitement par question

- **Q3** : les 19 mois sont exclus du calcul des indicateurs.
- **Q1** : seule la fenêtre COVID **2020-03 → 2021-06** (`liaisons_fiabilite.covid_debut`,
  `covid_fin` dans `config/defaut.yaml`) est exclue, et **uniquement de la pente de tendance** ; les mois
  restent dans les séries affichées.
- **Q2** : aucune exclusion dans le code. Le cadrage du notebook prévoit une variante
  « toute la période sans 2020 » ; elle est à rendre explicite.
- **Q4** : aucune exclusion ; période réglable (`periode_debut`, `periode_fin` dans
  `config/defaut.yaml`). Le notebook reconnaît qu'une grève peut abaisser le score
  d'une liaison sur toute la période.

> **À harmoniser** : quatre règles différentes (liste de 19 mois, fenêtre COVID,
> année 2020 entière, aucune exclusion). Une liste
> unique (`config/known_events.csv`, chemin déjà prévu dans `config.py`) éviterait
> l'écart.

## 13. Variables dérivées

Notations pour une liaison $r$ et un mois $m$ : $P$ trains prévus, $A$ annulés,
$C = P - A$ circulés, $L^{15}, L^{30}, L^{60}$ trains en retard de plus de 15, 30,
60 min, $D$ durée moyenne du trajet. Les agrégats sur une période **somment les
comptages puis divisent** (jamais de moyenne de taux ni de somme de moyennes).

| Variable | Formule | Où |
|---|---|---|
| `liaison` (non orientée) | paire $\{gare_a, gare_b\}$ en ordre alphabétique, « A - B » | `nettoyage.py` |
| `circules` | $C = P - A$ | `nettoyage.py` |
| `minutes_retard` | retard moyen à l'arrivée $\times C$ | `nettoyage.py` |
| `circules_mesures` | $C$ si le retard moyen est connu, sinon NaN | `nettoyage.py` |
| Taux d'annulation | $\tau^{ann}_r = \sum_m A_m / \sum_m P_m$ | Q3, Q4 |
| Taux de retard > 15 min | $\tau^{15}_r = \sum_m L^{15}_m / \sum_m C_m$ | Q3 |
| Part des retards > 30 min | $s_r = \sum_m L^{30}_m / \sum_m L^{15}_m \approx P(>30 \mid >15)$ | Q3 |
| Part des retards > 60 min | $e_r = \sum_m L^{60}_m / \sum_m L^{15}_m \approx P(>60 \mid >15)$ | Q3 |
| Volatilité relative | $CV_r = \sigma(\tau^{15}_{r,m}) / \overline{\tau^{15}_{r,m}}$ | Q3 |
| Taux d'incidents (orienté) | $\sum_m (A_m + L^{15}_m) / \sum_m P_m$ | Q1 |
| Pente de tendance | coefficient $b$ de la régression $\text{taux}_{r,m} = a + b\,t$, hors COVID | Q1 |
| Score de fiabilité | $100\,[1 - w \min(\tfrac{\tau^{ann}}{c_{ann}}, 1) - (1-w) \min(\tfrac{\bar{R}}{c_{ret}}, 1)]$ | Q4 |
| Retards hérités (par gare de départ) | $\sum (\text{retards à l'arrivée}) \times (p_{gare} + p_{voyageurs}) / 100$ | Q2 |
| Retards non hérités | $\sum (\text{retards à l'arrivée}) \times (p_{infra} + p_{trafic} + p_{matériel}) / 100$ | Q2 |
| Retards externes | $\sum (\text{retards à l'arrivée}) \times p_{externe} / 100$ | Q2 |
| Part héritée | hérités / (hérités + non hérités + externes) | Q2 |

**Ajustement à la durée (Q3)** : le taux de retard > 15 min croît avec la durée
(≈ 5 % pour 1 h de trajet, ≈ 19 % pour 7 h ; Spearman 0,72). On retire cet effet :

$$\tilde{f}_r = f_r - \hat{b}\,(\ln D_r - \overline{\ln D})$$

où $\hat{b}$ est la pente de la régression $f \sim \ln D$ sur toutes les liaisons.
Appliqué seulement si $|\rho_{Spearman}(f, D)| > 0{,}3$. Après ajustement, la
corrélation du taux > 15 min avec la durée passe de 0,72 à −0,01.

**Score Q4** : $w$ = `poids` (0,5), $c_{ann}$ = `cap_annulation` (6 %),
$c_{ret}$ = `cap_retard` (12 min), $\bar{R} = \sum \text{minutes\_retard} / \sum C$
(retard moyen à l'arrivée, tous trains) ; liaisons de moins de `min_trains` (100)
trains prévus ignorées. Valeurs dans `config/defaut.yaml`. Catégories : très fiable
(≥ 85), fiable (70–84), moyenne (55–69), peu fiable (40–54), à risque (< 40).
Sensibilité testée : en faisant varier poids et plafonds, la corrélation des
classements avec la référence reste entre 0,92 et 1.

**Retards hérités (Q2)** : hypothèse de classement des causes. Gestion en gare et
prise en compte des voyageurs (correspondances, affluence) = hérité ; infrastructure,
gestion du trafic et matériel roulant = non hérité ; causes externes à part.
« Concentrer » est lu en **volume** (nombre de trains), pas en taux.

## 14. Limites d'usage

- **Pas de total national par simple somme** : un même train est compté dans
  plusieurs liaisons (une ligne par couple origine–destination desservi). Sommer
  les liaisons compte plusieurs fois les mêmes trains.
- **Seuil de retard composite** : la colonne « trains en retard à l'arrivée » utilise
  un seuil de 5, 10 ou 15 min selon la durée du trajet (section 3) ; elle n'est pas
  comparable d'une liaison à l'autre. C'est la base des volumes de Q2. Les colonnes
  `> 15 / 30 / 60 min` ont des seuils fixes : à préférer pour comparer.
- **Parts de causes appliquées à des nombres de trains (Q2)** : la source ne précise
  pas si les parts portent sur des trains ou des minutes de retard. Multiplier le
  nombre de trains en retard par une part donne un ordre de grandeur, pas un compte
  exact.
- **Gares de départ (Q2)** : une gare très desservie (Paris) concentre mécaniquement
  plus de retards en volume ; comparer aussi les parts.
- **Effet de la durée** : les liaisons longues ont mécaniquement plus de retards
  > 15 min. Un classement brut les pénalise ; utiliser l'ajustement (section 13) ou le
  signaler.
- **Pas de conclusion causale** : les données sont observationnelles et agrégées.
  Les parts de causes sont déclarées par l'opérateur et souvent incomplètes (D7).
  Les analyses décrivent des associations.
- **Faibles volumes** : les taux des liaisons à peu de trains sont bruités (seuils :
  24 mois minimum en Q3, 100 trains en Q4).
- **Agrégation mensuelle** : impossible de distinguer un train très en retard de
  plusieurs trains légèrement en retard.
- **2025** : retards graves inexploitables de janvier à mars (section 11).
- **Schéma du réseau (Q4)** : disposition calculée par un algorithme de graphe, pas
  de coordonnées réelles ; les distances à l'écran n'ont pas de sens géographique.
- **Choix arbitraires (Q4)** : poids et plafonds du score sont des conventions,
  documentées et testées (section 13), pas des normes.

## 15. Maintenance du jeu dérivé

- **Responsables** : l'équipe RailInsight ; la datasheet est tenue à jour par la
  personne en charge de la documentation, chaque responsable de question validant
  les sections qui le concernent.
- **Signaler une erreur** : ouvrir une *issue* sur le dépôt GitHub du projet.
- **Mise à jour** : à chaque nouvelle publication de la source (semestrielle) et à
  chaque changement de règle de nettoyage.

### 15.1 Régénérer

Il n'existe pas encore de script unique : le jeu dérivé est recalculé à la volée.

1. Remplacer `data/raw/regularite-mensuelle-tgv-aqst.csv` par la nouvelle version.
2. Vérifier le schéma : `comparer_colonnes(chemin)` (`analysis/donnees.py`) doit
   renvoyer deux listes vides.
3. Lancer les tests : `uv run pytest`.
4. Réexécuter les notebooks Q1, Q3 et Q4, puis relancer l'application
   (`uv run streamlit run app.py`).
5. Recontrôler les chiffres des sections 2, 4, 10 et 11, et la liste de la
   section 12 si de nouveaux mois exceptionnels apparaissent.
6. Ajouter une entrée au changelog ci-dessous.

Sorties prévues (chemins déclarés dans `config.py`, **pas encore produites**) :
`data/processed/clean_monthly.parquet`, `route_features.parquet`,
`network_monthly.parquet`, `quality_report.json`.

### 15.2 Changelog

| Date | Version | Changement |
|---|---|---|
| 2026-10-21 | 1.0 | Datasheet du jeu source (partie A) |
| 2026-10-29 | 1.1 | Partie B : jeu dérivé, décisions de nettoyage, anomalies 2025, mois exceptionnels, variables dérivées, limites, maintenance |
| 2026-10-29 | 1.2 | Alignement sur le cours (session 6) : collecte (mesure, définition composite), composition (biais, mécanismes de manque), licence ODbL, provenance, maintenance |
| 2026-10-29 | 1.3 | Intégration des choix de Q2 (`eric-explore2`) et Q4 (`score_fiabilite`) : périmètres, exclusions, variables, limites |

## 16. Distribution du jeu dérivé

- Le jeu dérivé n'est pas publié en tant que fichier : il est recalculé par le code
  du dépôt et exposé à travers l'application Streamlit.
- La source étant sous **ODbL**, toute publication d'une base dérivée (par exemple
  les fichiers prévus dans `data/processed/`) doit rester sous ODbL et citer
  « SNCF Voyageurs — SNCF Open Data ». L'application et ses graphiques doivent
  mentionner la source.

## 17. Lien avec le cadre réglementaire

RailInsight n'est pas un système d'IA à haut risque au sens de l'AI Act. Cette
datasheet reprend néanmoins les exigences de son article 10 :

| Exigence (art. 10, simplifié) | Où |
|---|---|
| Origine et processus de collecte | Sections 1, 3 |
| Examen des biais et mesures d'atténuation | Sections 2, 7, 12, 13 (ajustement à la durée), 14 |
| Pertinence, représentativité, erreurs, complétude | Sections 2, 4, 10, 11 |
| Documentation des choix et de leur justification | Sections 10 à 13 |
