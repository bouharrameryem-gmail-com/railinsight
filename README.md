# RailInsight

Streamlit web application for exploring SNCF TGV punctuality data (open data, 2018 – present).

Built as part of a data science project at Télécom Paris. The four analyses study TGV reliability from monthly route-level data.

---

## Data source

**SNCF — Régularité mensuelle TGV (AQST)**
[ressources.data.sncf.com](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/)

One row = one month × one route (departure → arrival). ~13 000 rows, 2018-01 → present.
See `DATASHEET.md` for full documentation of the dataset and its limitations.

**Reference data for the landing page map** (`data/reference/`)

- `gares_coordonnees.csv`: GPS coordinates of the TGV stations, written by hand with the station names used in the AQST dataset. Stations missing from this file are logged and left off the map.
- `reseau_lgv.geojson`: simplified track of the high-speed lines, from SNCF Réseau ([Lignes LGV et par écartement](https://ressources.data.sncf.com/explore/dataset/lignes-lgv-et-par-ecartement/), ODbL licence). Regenerate it with:

```bash
uv run python scripts/telecharger_reseau_lgv.py
```

The app only reads these files: it never calls an external API at runtime.

---

## Analyses

| # | Question | Author / status |
|---|---|---|
| 1 | Which routes are least reliable, and is this worsening over time? | Michelle |
| 2 | Which departure stations concentrate delays vs. cascade victims? | Éric |
| **3** | **Can routes be clustered by punctuality profile?** | **Bachelard** |
| 4 | Reliability score per route, mapped on the network | Meryem |

The landing page presents the four questions as one investigation, from the observation (Q1) to the verdict (Q4).

---

## Project structure

```
.
├── app.py                      # Streamlit entry point (navigation only)
├── .streamlit/config.toml      # Streamlit server/client configuration
├── config/defaut.yaml          # Validated default analysis parameters
├── data/
│   ├── raw/                    # Source CSV, never modified
│   ├── reference/              # Station coordinates and LGV network (landing page map)
│   └── processed/              # Optional prepared, cleaned Parquet data
├── models/                     # Trained model artefacts
├── notebooks/                  # Exploratory analysis (Jupyter, standalone)
├── scripts/                    # One-off data preparation scripts
├── docs/                       # Sphinx documentation (API reference)
├── logs/                       # Runtime logs (debug.log, errors.log)
├── src/railinsight/
│   ├── config.py               # Paths, column mapping, constants
│   ├── exceptions.py           # Custom exceptions
│   ├── logging_config.py       # Two rotating file handlers + console
│   ├── analysis/               # Data reading, cleaning, network indicators, Q1 reliability, Q2 causes, Q3 clustering, Q4 score
│   ├── backend/                # Validated data loading and orchestration of the landing page and Q1–Q4
│   ├── viz/                    # Reusable figure builders
│   ├── utils/                  # Generic helpers
│   └── ui/
│       ├── pages/              # One file per page, no business logic
│       └── components/         # Reusable Streamlit widgets
└── tests/railinsight/          # Mirrors src/railinsight/
```

### Architecture

```
app.py → ui → backend → analysis
              └───────→ viz
```

Streamlit belongs in the UI layer. Analysis and visualization modules should remain usable
without Streamlit.

---

## Layers

### `notebooks/`
Exploration and question-specific analyses. Older notebooks often read the raw CSV directly;
`notebook_example.ipynb` demonstrates the validated reader/configuration pattern. The Q1 notebook and Streamlit page use `charger_config()`, `lire_donnees()` and
`nettoyer_regularite()`. The notebook preserves the full exploratory analysis; the
page presents its ranking, trends, sensitivity checks and duration-adjusted results.

### `railinsight.analysis`
Feature engineering and analysis functions used by the app and notebooks.
No Streamlit dependency; covered by pytest.

### `railinsight.backend`
Loads schema-validated local data, caches it with Streamlit, and orchestrates
analysis for the UI. Unit-tested with pytest.

### `railinsight.ui.pages`
Contains the home page and the Q1–Q4 pages. Each analysis page delegates data work
to the backend and uses the shared page layout and components.
Unused demo pages and prototype components have been removed from the finished project.

### `railinsight.viz`
Functions that take a DataFrame and return a Plotly figure.
No Streamlit import, so figures are reusable in notebooks too.

### `railinsight.utils`
Generic helpers (date parsing, formatting…). No mocks needed in tests.

---

## Local development

**Prerequisites**: Python ≥ 3.14, [uv](https://docs.astral.sh/uv/)

```shell
# Install dependencies and the package in the project environment
uv sync

# Run the app
uv run streamlit ./app.py

# Lint and formatting
uv run ruff check .
uv run ruff format --check .

# Tests + branch coverage (CI requires at least 90%)
uv run pytest --tb=short -q --cov=src/railinsight --cov-report=term-missing --cov-report=xml --cov-fail-under=90

uv run sphinx-build -W -b html docs/source docs/build/html
```

### Configuration

Defaults are in `config/defaut.yaml` and loaded with `railinsight.config.charger_config()`.
The file defines the project seed, data paths, and Q4 (`score_fiabilite`) parameters.
Q4 currently uses its defaults from `ParametresScore` and its page controls, rather than
reading the Q4 values from YAML. Other configuration overrides can be set with
`RAILINSIGHT_CONFIG` pointing to a YAML file relative to the repository root; unknown or
invalid keys raise `ConfigInvalide`.

```yaml
# local.yaml
score_fiabilite:
  poids: 0.7
```

PowerShell: `$env:RAILINSIGHT_CONFIG = "local.yaml"`  
bash: `export RAILINSIGHT_CONFIG=local.yaml`

### Jupyter notebooks

```shell
uv run jupyter lab
```

Notebooks live in `notebooks/`. Follow `notebooks/notebook_example.ipynb` for configuration
and schema-validated loading. Existing notebooks are not yet fully harmonized; check each
notebook and its methodology before comparing results.

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

## Deployment

The project is configured for **Streamlit Cloud**.

1. Push to `main`.
2. Streamlit Cloud picks up `app.py` automatically.
3. The website reads the tracked `data/raw/regularite-mensuelle-tgv-aqst.csv`.
   No API connection or secret is needed to load the data.

### Local data and faster loading

- **Website and notebooks** use the same local CSV. The sidebar shows the last
  month included, not the current month or an API retrieval date.
- The website caches data and page calculations across visitors. Opening a new
  session does not clear other visitors' caches. The homepage does not import
  the clustering libraries.
- Optionally prepare the cleaned data before starting the website:

  ```bash
  uv run python -m railinsight.backend.dataloader
  ```

  This creates `data/processed/clean_monthly.parquet`, preserving column types.
  The website uses it if it is newer than the raw CSV and cleaning code.
  Otherwise it cleans the CSV once in memory. Q1, Q3, Q4 and the homepage share
  this cleaned table; Q2 keeps its own raw-data cleaning rules.
  The generated file is ignored by Git and is optional on Streamlit Cloud.
- To update the dataset, replace the raw CSV with an export using the same SNCF
  columns, rerun the preparation command if desired, then **restart the app** to
  clear all in-memory calculations. For Streamlit Cloud, commit and push the
  updated raw CSV, then reboot the app. No automatic downloads run in the background.
- Streamlit Cloud may still need time to wake an inactive app; these changes
  remove the API wait, not the hosting cold start.
- These are **monthly aggregate data**, not real-time train predictions.

---

## Contributing

- Work on a feature branch, open a PR against `main`.
- CI checks, all blocking: ruff lint and format, docstring presence with
  interrogate (≥ 80 %), pytest with branch coverage (≥ 90 %), a dependency audit
  (pip-audit) and the Sphinx build with warnings treated as errors.
- See `.github/pull_request_template.md` for the PR checklist.
- Branch and commit conventions, including Python naming rules, are documented in the
  [project wiki](https://github.com/bouharrameryem-gmail-com/railinsight/wiki/Conventions-de-d%C3%A9veloppement).