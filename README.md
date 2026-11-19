 # RailInsight

Streamlit web application for exploring SNCF TGV punctuality data (open data, 2018 – present).

Built as part of a data science project at Télécom Paris. The four analyses study TGV reliability from monthly route-level data.

---

## Data source

**SNCF — Régularité mensuelle TGV (AQST)**
[ressources.data.sncf.com](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/)

One row = one month × one route (departure → arrival). ~13 000 rows, 2018-01 → present.
See `DATASHEET.md` for full documentation of the dataset and its limitations.

---

## Analyses

| # | Question | Author / status |
|---|---|---|
| 1 | Which routes are least reliable, and is this worsening over time? | Michelle |
| 2 | Which departure stations concentrate delays vs. cascade victims? | Éric |
| **3** | **Can routes be clustered by punctuality profile?** | **Bachelard** |
| 4 | Reliability score per route, mapped on the network | Meryem |

---

## Project structure

```
.
├── app.py                      # Streamlit entry point (navigation only)
├── .streamlit/config.toml      # Streamlit server/client configuration
├── config/defaut.yaml          # Validated default analysis parameters
├── data/
│   ├── raw/                    # Source CSV, never modified
│   └── processed/              # Optional prepared, cleaned Parquet data
├── models/                     # Trained model artefacts
├── notebooks/                  # Exploratory analysis (Jupyter, standalone)
├── docs/                       # Sphinx documentation (scaffold)
├── logs/                       # Runtime logs (debug.log, errors.log)
├── src/railinsight/
│   ├── config.py               # Paths, column mapping, constants
│   ├── exceptions.py           # Custom exceptions
│   ├── logging_config.py       # Two rotating file handlers + console
│   ├── analysis/               # Data reading, cleaning, Q1 reliability, Q2 causes, Q3 clustering, Q4 score
│   ├── backend/                # Validated data loading and Q1–Q4 orchestration
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
uv run streamlit run app.py

# Lint
uv run ruff check .
uv run ruff format --check .

# Tests + branch coverage (CI requires at least 90%)
uv run pytest --tb=short -q --cov=src/railinsight --cov-report=term-missing --cov-report=xml --cov-fail-under=90
```

### Configuration

Defaults are in `config/defaut.yaml` and loaded with `railinsight.config.charger_config()`.
The current file defines the project seed, data paths, and Q4 (`score_fiabilite`) parameters.
To override selected values, set `RAILINSIGHT_CONFIG` to a YAML file relative to the repository
root; unknown or invalid keys raise `ConfigInvalide`.

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

### Q4 : score de fiabilité

La page affiche le schéma du réseau du notebook `notebooks/Q4_score_fiabilite.ipynb`.
Une seule page avec trois onglets : réseau complet, classements et match de
deux liaisons. Le dessin n'est pas une carte géographique.

La période et la priorité du voyageur actualisent toutes les notes. Par défaut,
annulations et retards comptent autant ; choisir une priorité donne un poids de
75 % à ce critère et de 25 % à l'autre. Le backend existant est inchangé.

Dans « Le réseau », survoler le milieu d'un trait affiche les indicateurs ;
le filtre « Quelles liaisons afficher ? » permet de choisir une ou plusieurs
couleurs/catégories. Il ne change ni les notes, ni les positions des gares,
ni les classements et le match. Une sélection vide ou sans liaison affiche
un message explicite. Cliquer sur la légende masque aussi une catégorie.
Le volet « Code source simplifié » montre un exemple du dessin du réseau,
sans les détails au survol, à partir des données et notes déjà préparées.
« Le classement » présente les
meilleures et les moins bonnes notes. « Le match des trajets » permet de comparer
les indicateurs de deux liaisons avant de révéler leurs notes.

| Fichier | Rôle |
|---|---|
| `src/railinsight/analysis/score_fiabilite.py` | Nettoyage et calcul de la note |
| `src/railinsight/analysis/graphe_reseau.py` | Position reproductible des gares |
| `src/railinsight/backend/fiabilite.py` | Chargement de tous les services et analyse par période |
| `src/railinsight/viz/fiabilite.py` | Graphique Plotly et couleurs |
| `src/railinsight/ui/pages/q4_score_fiabilite.py` | Textes, filtres et affichage Streamlit |
| `app.py` | Inscription dans la navigation |

La note reprend par défaut les réglages du notebook : poids égaux, plafond de 6 %
d'annulations, plafond de 12 minutes de retard et minimum de 100 trains par liaison.
Le retard agrégé est pondéré par le nombre de trains dont le retard est connu.

Différences de nettoyage : les annulations invalides et les lignes sans mois ou
gare sont écartées ; un retard inférieur à -15 minutes devient manquant.
Une liaison sans retard mesuré n'est pas notée. Les anomalies de nettoyage
sont journalisées.

Pour adapter la présentation, modifier la page ; pour adapter les seuils, modifier
`ParametresScore` et mettre à jour le texte « Méthode et limites ».

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
- CI checks: ruff lint and format, pytest and a dependency audit (pip-audit). The ≥ 90 %
  coverage gate is non-blocking and the docstring check (interrogate) is currently disabled.
- See `.github/pull_request_template.md` for the PR checklist.
- Branch and commit conventions, including Python naming rules, are documented in the
  [project wiki](https://github.com/bouharrameryem-gmail-com/railinsight/wiki/Conventions-de-d%C3%A9veloppement).
