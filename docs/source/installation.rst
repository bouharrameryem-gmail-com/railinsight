Installation
============

Prérequis
---------

- Python 3.14 ou plus récent ;
- `uv <https://docs.astral.sh/uv/>`_, qui gère l'environnement virtuel et les
  dépendances à partir du fichier ``uv.lock``.

Installer le projet
-------------------

Depuis la racine du dépôt :

.. code-block:: shell

   uv sync

Cette commande crée l'environnement ``.venv``, installe les dépendances aux
versions exactes du fichier ``uv.lock`` et installe le paquet ``railinsight``
en mode éditable : une modification du code est prise en compte sans
réinstallation.

Vérifier l'installation
-----------------------

Les commandes suivantes sont celles que lance l'intégration continue :

.. code-block:: shell

   uv run ruff check .
   uv run ruff format --check .
   uv run interrogate -c pyproject.toml src
   uv run pytest --cov=src/railinsight --cov-fail-under=90 -q
   uv run sphinx-build -W -b html docs/source docs/build/html

Les tests n'ont besoin ni d'Internet ni des données réelles : ils utilisent des
jeux de données construits dans ``tests/``.

Données nécessaires
-------------------

L'application lit uniquement des fichiers locaux, versionnés dans le dépôt :

- ``data/raw/regularite-mensuelle-tgv-aqst.csv`` : régularité mensuelle des TGV
  par liaison, publiée par la SNCF ;
- ``data/reference/gares_coordonnees.csv`` : coordonnées GPS des gares, pour la
  carte de la page d'accueil ;
- ``data/reference/reseau_lgv.geojson`` : tracé simplifié des lignes à grande
  vitesse, publié par SNCF Réseau sous licence ODbL.