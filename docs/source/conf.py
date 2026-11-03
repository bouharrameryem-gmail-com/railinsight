# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "railinsight"
copyright = "2026, RailInsight Team (Michelle, Eric, Bachelard, Meryem)"
author = "RailInsight Team (Michelle, Eric, Bachelard, Meryem)"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = []

language = "fr"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]


def formater_exemples(app, what, name, obj, options, lines):
    """Présente les exemples existants en blocs de code, sans modifier les sources."""
    titres = (
        "Usage:",
        "Example:",
        "Import each component directly from its module:",
        "How to replace this with the real backend:",
    )
    resultat = []
    for index, ligne in enumerate(lines):
        if (
            ligne in titres
            and index + 1 < len(lines)
            and lines[index + 1].startswith(" ")
        ):
            resultat.extend([ligne + ":", ""])
        elif ligne.endswith("Rule of thumb:"):
            resultat.extend([ligne, ""])
        else:
            resultat.append(ligne)
    lines[:] = resultat


def setup(app):
    """Prépare les exemples avant leur interprétation par Napoleon."""
    app.connect("autodoc-process-docstring", formater_exemples, priority=400)
