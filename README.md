# RailInsight

Streamlit application and data analysis of SNCF TGV punctuality (open data).

## Project structure


```
.
├── app.py                      # Streamlit entrypoint (navigation only)
├── .streamlit/config.toml      # Streamlit server/client configuration
├── data/
│   ├── raw/                    # Source datasets, never modified
│   └── processed/              # Cleaned / derived datasets
├── models/                     # Trained model files produced by analysis
├── notebooks/                  # Exploratory analysis (Jupyter)
├── docs/                       # Sphinx documentation
├── logs/                       # Runtime logs
├── src/railinsight/
│   ├── config.py               # Paths, settings
│   ├── exceptions.py           # Project-specific exceptions
│   ├── logging_config.py       # Logging setup
│   ├── analysis/               # Data analysis: cleaning, statistics, model training
│   ├── backend/                # Application business logic used by the UI
│   ├── viz/                    # Figure builders (Plotly)
│   ├── utils/                  # Generic helpers
│   └── ui/
│       ├── pages/              # Streamlit pages
│       └── components/         # Reusable Streamlit widgets
└── tests/railinsight/          # Mirrors src/railinsight/
```

## Layers

Dependencies flow one way: `ui → backend → analysis`, with `viz` and `utils` usable everywhere.
Only the `ui` package imports Streamlit.

### `notebooks/` and `railinsight.analysis`

* Explore the data in `notebooks/`
* Move reusable code (cleaning, feature engineering, model training/evaluation) into `analysis`
* Writes cleaned data to `data/processed/` and trained models to `models/`
* Does not import Streamlit; tested with pytest on small DataFrames

### `railinsight.backend`

* Business logic of the application: loads processed data and models, computes what the pages display
* Does not import Streamlit; tested with pytest

### `railinsight.ui.pages`

* One file per page, suffix `_page.py`
* No business logic: delegate to `backend`, shared widgets to `ui.components`
* Tested with Streamlit `AppTest` and mocked backend

### `railinsight.ui.components`

* Reusable UI widgets, encapsulate `st.session_state` handling
* Tested with Streamlit `AppTest`

### `railinsight.viz`

* Functions returning Plotly figures from DataFrames
* Does not import Streamlit, so figures are reusable in notebooks

### `railinsight.utils`

* Generic helpers, tested with pytest without mocks

## Local development

```shell
uv sync
```

```shell
uv run streamlit run app.py
```

```shell
uv run ruff check .
```

```shell
uv run ruff format --check .
```

```shell
uv run pytest
```
