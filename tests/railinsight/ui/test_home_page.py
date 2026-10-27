"""Tests for the home page via Streamlit AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

# Relative path resolution in AppTest is relative to the calling file.
# We use an absolute path to be independent of where pytest is launched from.
_PAGES_DIR = Path(__file__).parents[3] / "src" / "railinsight" / "ui" / "pages"


def test_home_page_renders():
    at = AppTest.from_file(str(_PAGES_DIR / "home.py"))
    at.run()
    assert not at.exception


def test_home_page_has_content():
    at = AppTest.from_file(str(_PAGES_DIR / "home.py"))
    at.run()
    # Hero is rendered as HTML (st.markdown) — page must have markdown content
    assert len(at.markdown) > 0
