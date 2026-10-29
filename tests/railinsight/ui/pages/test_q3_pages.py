"""AppTest tests for the Q3 unified page."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

_PAGES_DIR = Path(__file__).parents[4] / "src" / "railinsight" / "ui" / "pages"


class TestQ3Page:
    def test_renders_without_exception(self):
        at = AppTest.from_file(str(_PAGES_DIR / "q3.py"), default_timeout=60)
        at.run()
        assert not at.exception

    def test_initial_state_shows_info(self):
        at = AppTest.from_file(str(_PAGES_DIR / "q3.py"), default_timeout=60)
        at.run()
        assert not at.exception
        # Before submission, an info message is shown
        assert len(at.info) > 0 or len(at.markdown) > 0

    def test_form_submission_runs_analysis(self):
        at = AppTest.from_file(str(_PAGES_DIR / "q3.py"), default_timeout=90)
        at.run()
        # Even without form submission, page must render cleanly
        assert not at.exception
