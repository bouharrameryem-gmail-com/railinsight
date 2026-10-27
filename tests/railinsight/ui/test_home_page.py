"""Tests for the home page via Streamlit AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

# st.page_link requires st.navigation context, so tests must run through the
# full app entrypoint (app.py) rather than home.py directly.
_ROOT = Path(__file__).parents[3]


def test_home_page_renders():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    assert not at.exception


def test_home_page_has_content():
    at = AppTest.from_file(str(_ROOT / "app.py"))
    at.run()
    # Hero is rendered as HTML (st.markdown) — page must have markdown content
    assert len(at.markdown) > 0
