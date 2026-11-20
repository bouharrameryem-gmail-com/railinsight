Utilisation
===========

Lancer l'application
--------------------

.. code-block:: shell

   uv run streamlit run app.py

L'application s'ouvre dans le navigateur, par défaut à l'adresse
``http://localhost:8501``.

Parcourir l'enquête
-------------------

La page d'accueil pose la question commune : pourquoi votre TGV arrive-t-il en
retard ? Elle présente le taux de retard des 12 derniers mois, une carte des
gares de départ, l'évolution mois par mois et un sommaire des quatre pages.

.. list-table::
   :header-rows: 1
   :widths: 10 40 50

   * - Page
     - Question
     - Ce que l'on y fait
   * - Q1
     - Quelles liaisons sont les moins fiables, et est-ce que ça empire ?
     - Classer les liaisons, suivre leur évolution et prévoir les trois mois
       suivants.
   * - Q2
     - Le retard naît-il dans la gare de départ, ou arrive-t-il d'ailleurs ?
     - Comparer les gares qui fabriquent et celles qui encaissent les retards,
       puis lire le portrait d'une gare choisie.
   * - Q3
     - Quels profils de ponctualité se dessinent ?
     - Regrouper les liaisons selon leur régularité.
   * - Q4
     - Quelle note de fiabilité mérite chaque liaison ?
     - Noter les liaisons, les placer sur le réseau et en comparer deux.

Chaque page explique sa méthode et ses limites dans un volet « Méthode et
limites ».

Adapter les paramètres
----------------------

Les paramètres par défaut sont dans ``config/defaut.yaml``. Pour en changer
quelques-uns sans modifier ce fichier, placer les valeurs voulues dans un autre
fichier YAML et indiquer son chemin dans la variable ``RAILINSIGHT_CONFIG`` :

.. code-block:: powershell

   $env:RAILINSIGHT_CONFIG = "local.yaml"

Une clé inconnue ou une valeur invalide lève l'exception ``ConfigInvalide``,
dont le message nomme la clé en cause.

Mettre à jour les données
-------------------------

1. Remplacer ``data/raw/regularite-mensuelle-tgv-aqst.csv`` par un export récent
   du jeu AQST, avec les mêmes colonnes.
2. Si le tracé des lignes doit être rafraîchi, relancer :

   .. code-block:: shell

      uv run python scripts/telecharger_reseau_lgv.py

3. Redémarrer l'application, pour vider les calculs gardés en mémoire.

Consulter les journaux
----------------------

L'application écrit ses journaux dans le dossier ``logs/`` :

- ``debug.log`` : tous les messages, dont les réglages modifiés par
  l'utilisateur ;
- ``errors.log`` : les erreurs seulement.

Les deux fichiers tournent automatiquement : au-delà de leur taille maximale,
l'ancien contenu passe dans ``debug.log.1``, ``errors.log.1``, et ainsi de suite.