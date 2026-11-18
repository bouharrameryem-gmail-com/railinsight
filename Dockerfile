# Étape 1 : construction du virtualenv 
FROM python:3.14-slim AS builder

# uv copié depuis son image officielle (image plus léger qu'avec une installation pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Manifestes de dépendances en premier cache Docker préservé si le code change
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Virtualenv avec dépendances de production uniquement, à partir du lockfile exact
RUN uv sync --frozen --no-dev

# Étape 2 : image d'exécution minimale
FROM python:3.14-slim AS runtime

WORKDIR /app

# Virtualenv et code source issus du builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Fichiers de l'application
COPY app.py ./
COPY .streamlit/ ./.streamlit/
COPY config/ ./config/

# Port d'écoute ; peut être surchargé via -e PORT=xxxx ou docker-compose
ENV PORT=8501

EXPOSE $PORT

# Forme shell requise pour que $PORT soit évalué au démarrage du conteneur
CMD /app/.venv/bin/streamlit run app.py \
    --server.port $PORT \
    --server.address 0.0.0.0
