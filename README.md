# RailInsight

Application web Streamlit permettant d'explorer les données de ponctualité des TGV SNCF
(données ouvertes, de 2018 à aujourd'hui).

Réalisée dans le cadre d'un projet de science des données à Télécom Paris. Les quatre
analyses étudient la fiabilité des TGV à partir de données mensuelles par liaison.

---

## Source des données

**SNCF — Régularité mensuelle TGV (AQST)**
[ressources.data.sncf.com](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/)

Une ligne = un mois × une liaison (départ → arrivée). Environ 13 000 lignes, de 2018-01
à aujourd'hui. Voir `DATASHEET.md` pour la documentation complète du jeu de données et
de ses limites.

**Données de référence pour la carte de la page d'accueil** (`data/reference/`)

- `gares_coordonnees.csv` : coordonnées GPS des gares TGV, saisies à la main avec les noms
  de gares utilisés dans le jeu de données AQST. Les gares absentes de ce fichier sont
  consignées dans les journaux et ne figurent pas sur la carte.
- `reseau_lgv.geojson` : tracé simplifié des lignes à grande vitesse, fourni par SNCF
  Réseau ([Lignes LGV et par écartement](https://ressources.data.sncf.com/explore/dataset/lignes-lgv-et-par-ecartement/),
  licence ODbL). Pour le régénérer :

```bash
uv run python scripts/telecharger_reseau_lgv.py
```

L'application lit uniquement ces fichiers : elle n'appelle aucune API externe à
l'exécution.

---

## Analyses

| # | Question | Auteur / état |
|---|---|---|
| 1 | Quelles liaisons sont les moins fiables, et leur fiabilité se dégrade-t-elle avec le temps ? | Michelle |
| 2 | Quelles gares de départ concentrent les retards ou en subissent les effets en cascade ? | Éric |
| **3** | **Peut-on regrouper les liaisons selon leur profil de ponctualité ?** | **Bachelard** |
| 4 | Score de fiabilité par liaison, représenté sur le réseau | Meryem |

La page d'accueil présente les quatre questions comme une seule enquête, de l'observation
(Q1) à la conclusion (Q4).

---

## Structure du projet

```
.
├── app.py                      # Point d'entrée Streamlit (navigation uniquement)
├── .streamlit/config.toml      # Configuration du serveur et du client Streamlit
├── config/defaut.yaml          # Paramètres d'analyse par défaut validés
├── data/
│   ├── raw/                    # CSV d'origine, jamais modifié
│   ├── reference/              # Coordonnées des gares et réseau LGV (carte de la page d'accueil)
│   └── processed/              # Données Parquet préparées et nettoyées (facultatif)
├── models/                     # Artefacts des modèles entraînés
├── notebooks/                  # Analyses exploratoires (Jupyter, autonomes)
├── scripts/                    # Scripts ponctuels de préparation des données
├── docs/                       # Documentation Sphinx (référence de l'API)
├── logs/                       # Journaux d'exécution (debug.log, errors.log)
├── src/railinsight/
│   ├── config.py               # Chemins, correspondance des colonnes, constantes
│   ├── exceptions.py           # Exceptions personnalisées
│   ├── logging_config.py       # Deux gestionnaires de fichiers rotatifs + console
│   ├── analysis/               # Lecture et nettoyage des données, indicateurs réseau, fiabilité Q1, causes Q2, clustering Q3, score Q4
│   ├── backend/                # Chargement validé des données et orchestration de l'accueil et de Q1–Q4
│   ├── viz/                    # Fonctions réutilisables de création de graphiques
│   ├── utils/                  # Fonctions utilitaires génériques
│   └── ui/
│       ├── pages/              # Un fichier par page, sans logique métier
│       └── components/         # Composants Streamlit réutilisables
└── tests/railinsight/          # Reprend la structure de src/railinsight/
```

### Architecture

```
app.py → ui → backend → analysis
              └───────→ viz
```

Streamlit appartient à la couche UI. Les modules d'analyse et de visualisation doivent
rester utilisables sans Streamlit.

---

## Couches

### `notebooks/`
Exploration et analyses propres à chaque question. Les anciens notebooks lisent souvent
directement le CSV brut ; `notebook_example.ipynb` montre le modèle de lecture et de
configuration validées. Le notebook Q1 et la page Streamlit utilisent
`charger_config()`, `lire_donnees()` et `nettoyer_regularite()`. Le notebook conserve
l'analyse exploratoire complète ; la page présente son classement, ses tendances, ses
analyses de sensibilité et ses résultats ajustés à la durée.

### `railinsight.analysis`
Ingénierie des caractéristiques et fonctions d'analyse utilisées par l'application et les
notebooks. Aucune dépendance à Streamlit ; tests exécutés avec pytest.

### `railinsight.backend`
Charge les données locales validées selon leur schéma, les met en cache avec Streamlit et
orchestre les analyses pour l'interface. Tests unitaires exécutés avec pytest.

### `railinsight.ui.pages`
Contient la page d'accueil et les pages Q1 à Q4. Chaque page d'analyse délègue le
traitement des données au backend et utilise la mise en page et les composants partagés.
Les pages de démonstration inutilisées et les composants prototypes ont été supprimés du
projet final.

### `railinsight.viz`
Fonctions qui prennent un DataFrame et renvoient un graphique Plotly.
Elles n'importent pas Streamlit ; les graphiques sont donc aussi réutilisables dans les
notebooks.

### `railinsight.utils`
Fonctions utilitaires génériques (analyse des dates, formatage…). Aucun mock nécessaire
dans les tests.

---

## Développement local

**Prérequis** : Python ≥ 3.14, [uv](https://docs.astral.sh/uv/)

```shell
# Installer les dépendances et le paquet dans l'environnement du projet
uv sync

# Lancer l'application
uv run streamlit ./app.py

# Vérification du code et formatage
uv run ruff check .
uv run ruff format --check .

# Tests et couverture des branches (la CI exige au moins 90 %)
uv run pytest --tb=short -q --cov=src/railinsight --cov-report=term-missing --cov-report=xml --cov-fail-under=90

uv run sphinx-build -W -b html docs/source docs/build/html
```

### Configuration

Les valeurs par défaut se trouvent dans `config/defaut.yaml` et sont chargées avec
`railinsight.config.charger_config()`. Le fichier définit la graine du projet, les chemins
des données et les paramètres de Q4 (`score_fiabilite`). Q4 utilise actuellement les
valeurs par défaut de `ParametresScore` et les contrôles de sa page, plutôt que de lire
les valeurs Q4 du fichier YAML. D'autres surcharges de configuration peuvent être
définies à l'aide de `RAILINSIGHT_CONFIG`, qui pointe vers un fichier YAML relatif à la
racine du dépôt ; les clés inconnues ou invalides déclenchent `ConfigInvalide`.

```yaml
# local.yaml
score_fiabilite:
  poids: 0.7
```

PowerShell: `$env:RAILINSIGHT_CONFIG = "local.yaml"`  
bash: `export RAILINSIGHT_CONFIG=local.yaml`

### Notebooks Jupyter

```shell
uv run jupyter lab
```

Les notebooks se trouvent dans `notebooks/`. Consultez
`notebooks/notebook_example.ipynb` pour la configuration et le chargement avec validation
du schéma. Les notebooks existants ne sont pas encore entièrement harmonisés ; vérifiez
chacun d'eux ainsi que sa méthodologie avant de comparer les résultats.

### Page d'accueil

L'accueil pose la question commune aux quatre analyses : pourquoi votre TGV
arrive-t-il en retard ? Le premier écran associe une phrase calculée sur les
12 derniers mois (« 1 TGV sur N est arrivé avec plus d'un quart d'heure de
retard ») à une carte des gares de départ. Sur la carte, la taille d'une bulle
suit le nombre de trains et sa couleur le taux de retard de plus de 15 minutes,
sur le tracé réel des lignes à grande vitesse. Les gares très proches, comme
celles de Paris, sont réunies en une bulle détaillée au survol.

Suivent trois chiffres repères avec leur évolution sur un an (retards,
annulations, liaisons suivies), un calendrier des retards mois par mois et un
sommaire des quatre analyses. Seul le service national est retenu, et les
lignes en double du fichier SNCF ne sont comptées qu'une fois. Si les données
manquent, chaque bloc affiche un message à sa place et le sommaire reste
accessible.

| Fichier | Rôle |
|---|---|
| `src/railinsight/analysis/indicateurs_reseau.py` | Taux de retard et d'annulation, fenêtres de 12 mois, gares les plus touchées |
| `src/railinsight/analysis/geometrie.py` | Extraction et simplification du tracé des LGV |
| `src/railinsight/backend/accueil.py` | Chargement des données, des coordonnées et du réseau |
| `src/railinsight/viz/accueil.py` | Carte des gares et calendrier |
| `src/railinsight/ui/pages/home.py` | Textes et mise en page |
| `scripts/telecharger_reseau_lgv.py` | Téléchargement unique du réseau LGV |

### Q1 : liaisons les moins fiables

La page propose une liaison principale commune à l'évolution et à la prévision,
avec sa fiabilité observée et son volume de trains sur toute la période.
Chaque onglet ne charge que son propre contenu et présente les contrôles qui le
concernent. Le classement reste global ; l'évolution permet de comparer jusqu'à
cinq liaisons en vue mensuelle ou annuelle, sur 12 mois, 24 mois ou tout
l'historique. La fenêtre affichée ne modifie pas les pentes calculées sur toute
la période ; une année affichée peut être partielle. Les taux annuels sont des
ratios de sommes. Les données mensuelles sélectionnées sont exportables en CSV.

L'onglet « Prévision à 3 mois » propose dès son ouverture une estimation mensuelle
de la fiabilité d'une liaison : `100 × (1 − taux d'incidents)`. Il utilise les mêmes
fonctions que la section 8 du notebook Q1, avec 48 mois récents consécutifs requis.
Une régression Ridge (tendance et saisonnalité) est comparée à la référence
« même mois de l'année précédente » sur 12 mois de validation chronologique ;
les 3 derniers mois servent de test indépendant. Le modèle retenu est ensuite
réentraîné pour prévoir les 3 mois suivant le dernier mois du jeu, pas la date du
jour. Les erreurs, la référence et un export CSV sont disponibles. La prévision
reste exploratoire, sans intervalle calibré ni estimation journalière, et
n'anticipe pas les événements exceptionnels. Les trois estimations apparaissent
en cartes, avec leur écart à la référence saisonnière. Le graphique permet de
choisir 12 mois, 24 mois ou les 48 mois disponibles et de masquer la référence.
Les valeurs détaillées et la méthode sont repliées ; un résumé de l'erreur reste
visible. Cette extension de Q1 est distincte de Q5, toujours en cours.

### Q2 : gares responsables ou victimes des retards

La page répond à une question : quand un TGV arrive en retard, le problème
est-il né dans sa gare de départ, ou l'a-t-il apporté d'ailleurs ? Les causes
publiées par la SNCF sont regroupées en trois familles : retards nés sur place
(infrastructure, gestion du trafic, matériel roulant), retards importés
(gestion en gare et réutilisation du matériel, prise en charge des voyageurs)
et retards venus de l'extérieur (météo, obstacles, malveillance).

L'analyse se déroule en cinq sections, dont chaque titre est un constat calculé
sur les données affichées :

1. la répartition des trois familles et son évolution d'année en année ;
2. les gares qui fabriquent et celles qui encaissent le plus de retards, en volume ;
3. la même comparaison rapportée au trafic, pour les gares au-dessus d'un seuil
   de retards ;
4. les gares présentes dans les deux classements ;
5. le portrait de la gare choisie par l'utilisateur, rédigé automatiquement selon
   ses réglages (profil, rang, tendance et mois le plus chargé).

Réglages : exclusion de 2020 (activée par défaut, les confinements faussant les
volumes), nombre de gares par classement (5, 10 ou 15), seuil minimal de retards
(1 000 par défaut), gare étudiée et vue par année ou par mois. Chaque changement
de réglage est journalisé.

Limites : les nombres de retards par cause sont des estimations, car la SNCF
publie des pourcentages et non des comptes. Un retard à l'arrivée est attribué
à la gare de départ de la liaison, ce qui est une hypothèse de lecture. Les
tendances ne comparent que des années complètes, et seul le service national
est étudié.

| Fichier | Rôle |
|---|---|
| `src/railinsight/analysis/causes_retards.py` | Familles de causes, classements, croisements et portrait d'une gare |
| `src/railinsight/analysis/recit_gares.py` | Rédaction des titres et des phrases à partir des chiffres |
| `src/railinsight/backend/retards_gares.py` | Chargement et agrégation par gare, par année et par mois |
| `src/railinsight/viz/retards_gares.py` | Classements, répartitions, aire empilée et évolution |
| `src/railinsight/ui/components/section_header.py` | En-tête de section partagé avec l'accueil |
| `src/railinsight/ui/pages/q2_departure_stations.py` | Textes, réglages et mise en page |

### Q4 : score de fiabilité

Q4 attribue une note de 0 à 100 aux liaisons TGV selon la période et la priorité
choisies. Les deux sens d'une liaison sont regroupés et tous les services sont
inclus. La page comporte trois onglets :

- **Le réseau** : schéma du réseau calculé, non géographique. Filtrez les liaisons
  affichées par catégorie et survolez un trait pour voir ses indicateurs.
- **Le classement** : les 5, 10 ou 15 meilleures et moins bonnes notes.
- **Le match des trajets** : comparez les indicateurs de deux liaisons puis révélez
  leurs notes.

Les pénalités d'annulation et de retard moyen à l'arrivée atteignent leur maximum
à 6 % et 12 minutes. Leur poids est égal par défaut ; la priorité choisie passe
à 75 %, l'autre à 25 %. Une liaison doit compter au moins 100 trains prévus et
avoir un retard mesuré. Ce sont des seuils d'analyse, pas une note officielle SNCF
ni une prévision. Les catégories sont : Très fiable (85–100), Fiable (70–<85),
Moyenne (55–<70), Peu fiable (40–<55), À risque (<40).

Les lignes sans train prévu, avec un nombre d'annulations invalide ou un mois ou
une gare manquante sont exclues. Les retards inférieurs à -15 minutes sont traités
comme manquants.

| Fichier | Rôle |
|---|---|
| `src/railinsight/analysis/score_fiabilite.py` | Nettoyage et calcul de la note |
| `src/railinsight/analysis/graphe_reseau.py` | Position reproductible des gares |
| `src/railinsight/backend/fiabilite.py` | Chargement de tous les services et analyse par période |
| `src/railinsight/viz/fiabilite.py` | Graphique Plotly et couleurs |
| `src/railinsight/ui/pages/q4_score_fiabilite.py` | Textes, filtres et affichage Streamlit |
| `app.py` | Inscription dans la navigation |

Le retard moyen agrégé est pondéré par le nombre de trains dont le retard est
mesuré. Pour modifier les seuils, mettre à jour `ParametresScore` et le texte
« Méthode et limites » de la page.

---

## Déploiement

Le projet est configuré pour **Streamlit Cloud**.

1. Envoyez les changements sur `main`.
2. Streamlit Cloud détecte automatiquement `app.py`.
3. Le site lit le fichier suivi par Git `data/raw/regularite-mensuelle-tgv-aqst.csv`.
   Aucune connexion à une API ni aucun secret n'est nécessaire pour charger les données.

### Données locales et chargement accéléré

- **Le site et les notebooks** utilisent le même CSV local. La barre latérale indique le
  dernier mois inclus, et non le mois en cours ni la date de récupération via une API.
- Le site met en cache les données et les calculs des pages pour tous les visiteurs.
  L'ouverture d'une nouvelle session n'efface pas les caches des autres visiteurs. La
  page d'accueil n'importe pas les bibliothèques de partitionnement.
- Vous pouvez préparer les données nettoyées avant de lancer le site :

  ```bash
  uv run python -m railinsight.backend.dataloader
  ```

  This creates `data/processed/clean_monthly.parquet`, preserving column types.
  Le site utilise ce fichier s'il est plus récent que le CSV brut et le code de nettoyage.
  Sinon, il nettoie le CSV une fois en mémoire. Q1, Q3, Q4 et la page d'accueil partagent
  cette table nettoyée ; Q2 conserve ses propres règles de nettoyage des données brutes.
  Le fichier généré est ignoré par Git et reste facultatif sur Streamlit Cloud.
- Pour mettre à jour le jeu de données, remplacez le CSV brut par un export contenant les
  mêmes colonnes SNCF, relancez si besoin la commande de préparation, puis **redémarrez
  l'application** afin d'effacer tous les calculs en mémoire. Sur Streamlit Cloud,
  validez et poussez le CSV brut mis à jour, puis redémarrez l'application. Aucun
  téléchargement automatique n'est exécuté en arrière-plan.
- Streamlit Cloud peut toujours avoir besoin de temps pour réactiver une application
  inactive ; ces changements suppriment l'attente liée à l'API, pas le démarrage à froid
  de l'hébergement.
- Il s'agit de **données agrégées mensuelles**, et non de prévisions de trains en temps réel.

---

## Contribution

- Travaillez sur une branche dédiée à la fonctionnalité, puis ouvrez une PR vers `main`.
- Vérifications CI, toutes bloquantes : lint et formatage avec ruff, présence des
  docstrings vérifiée par interrogate (≥ 80 %), tests pytest avec couverture des branches
  (≥ 90 %), audit des dépendances (pip-audit) et compilation Sphinx avec les avertissements
  traités comme des erreurs.
- Consultez `.github/pull_request_template.md` pour la liste de vérification des PR.
- Les conventions de branches et de commits, y compris les règles de nommage Python, sont
  documentées dans le [wiki du projet](https://github.com/bouharrameryem-gmail-com/railinsight/wiki/Conventions-de-d%C3%A9veloppement).