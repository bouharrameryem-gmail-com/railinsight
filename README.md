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
