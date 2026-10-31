# RailInsight

Streamlit web application for exploring SNCF TGV punctuality data (open data, 2018 – present).

Built as part of a data science project at Télécom Paris — analysing monthly regularity per route to answer five questions around the theme of **reliability**.

---

## Data source

**SNCF — Régularité mensuelle TGV (AQST)**
[ressources.data.sncf.com](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/)

One row = one month × one route (departure → arrival). ~13 000 rows, 2018-01 → present.
See `DATASHEET.md` for full documentation of the dataset and its limitations.

---

## Analyses

| # | Question | Author |
|---|---|---|
| 1 | Which routes are least reliable, and is this worsening over time? | Michelle |
| 2 | Which departure stations concentrate delays vs. cascade victims? | Éric |
| **3** | **Can routes be clustered by punctuality profile?** | **Bachelard** |
| 4 | Reliability score per route, mapped on the network | Meryem |
| 5 | Predicting delay > 15 / 30 min from month and route | — |

---

## Project structure

```
.
├── app.py                      # Streamlit entry point (navigation only)
├── .streamlit/config.toml      # Streamlit server/client configuration
├── data/
│   ├── raw/                    # Source CSV, never modified
│   └── processed/              # Cleaned / derived parquet files
├── models/                     # Trained model artefacts
├── notebooks/                  # Exploratory analysis (Jupyter, standalone)
├── docs/                       # Sphinx documentation
├── logs/                       # Runtime logs (debug.log, errors.log)
├── src/railinsight/
│   ├── config.py               # Paths, column mapping, constants
│   ├── exceptions.py           # Custom exceptions
│   ├── logging_config.py       # Two rotating file handlers + console
│   ├── analysis/               # Feature engineering, clustering, models
│   ├── backend/                # Business logic called by UI (no Streamlit)
│   ├── viz/                    # Plotly figure builders (reusable in notebooks)
│   ├── utils/                  # Generic helpers
│   └── ui/
│       ├── pages/              # One file per page, no business logic
│       └── components/         # Reusable Streamlit widgets
└── tests/railinsight/          # Mirrors src/railinsight/
```

### Dependency rules

```
ui → backend → analysis
         ↑          ↑
        viz        utils
```

Only `ui` may import Streamlit. `analysis` and `viz` must run in notebooks without Streamlit.

---

## Layers

### `notebooks/`
Standalone EDA notebooks — no imports from the package. Run them to explore the data.
Once an approach is validated, port the logic to `analysis/`.

### `railinsight.analysis`
Feature engineering, clustering, model training. Writes to `data/processed/` and `models/`.
No Streamlit dependency; unit-tested with pytest on small DataFrames.

### `railinsight.backend`
Loads processed data and models, computes what the UI pages display.
No Streamlit dependency; unit-tested with pytest.

### `railinsight.ui.pages`
One file per page (e.g. `punctuality_profiles.py`). Single `render()` entry point per file.
No business logic — delegate everything to `backend`. Shared widgets go in `ui.components`.

### `railinsight.viz`
Functions that take a DataFrame and return a Plotly figure.
No Streamlit import, so figures are reusable in notebooks too.

### `railinsight.utils`
Generic helpers (date parsing, formatting…). No mocks needed in tests.

---

## Local development

**Prerequisites**: Python ≥ 3.14, [uv](https://docs.astral.sh/uv/)

```shell
# Install dependencies
uv sync

# Run the app
uv run streamlit run app.py

# Lint
uv run ruff check .
uv run ruff format --check .

# Tests + coverage
uv run pytest --cov=railinsight --cov-report=term-missing
```

### Jupyter notebooks

```shell
uv run jupyter lab
```

Notebooks live in `notebooks/`. They read raw data from `data/raw/` via relative paths
and do not import the `railinsight` package.

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

The app is deployed on **Streamlit Cloud**.

1. Push to `main`.
2. Streamlit Cloud picks up `app.py` automatically.
3. Set the `RAILINSIGHT_DATA_PATH` secret if the CSV is not bundled in the repo.

---

## Contributing

- Work on a feature branch, open a PR against `main`.
- CI checks: ruff lint, docstring coverage (interrogate), pytest ≥ 90 % coverage.
- See `.github/pull_request_template.md` for the PR checklist.
