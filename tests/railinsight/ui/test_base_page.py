"""Tests for BasePage error handling and template method structure."""

from streamlit.testing.v1 import AppTest


class TestBasePageHappyPath:
    def test_renders_without_exception(self):
        at = AppTest.from_string(
            """
import streamlit as st
from railinsight.adapters.fake_data_provider import FakeDataProvider
from railinsight.ui.base_page import BasePage

class GoodPage(BasePage):
    @property
    def question_number(self): return 1
    @property
    def question_title(self): return "Test"
    @property
    def author(self): return "Author"
    def _render_key_figures(self): st.metric("KPI", "1")
    def _render_body(self): st.write("body content")

GoodPage(FakeDataProvider()).render()
"""
        )
        at.run()
        assert not at.exception

    def test_header_contains_rendered_content(self):
        at = AppTest.from_string(
            """
import streamlit as st
from railinsight.adapters.fake_data_provider import FakeDataProvider
from railinsight.ui.base_page import BasePage

class GoodPage(BasePage):
    @property
    def question_number(self): return 3
    @property
    def question_title(self): return "Profils"
    @property
    def author(self): return "Bachelard"
    def _render_key_figures(self): st.metric("K", "1")
    def _render_body(self): st.write("ok")

GoodPage(FakeDataProvider()).render()
"""
        )
        at.run()
        assert len(at.markdown) > 0 or len(at.write) > 0


class TestBasePageErrorHandling:
    def test_domain_error_shows_warning_not_exception(self):
        at = AppTest.from_string(
            """
import streamlit as st
from railinsight.adapters.fake_data_provider import FakeDataProvider
from railinsight.ui.base_page import BasePage
from railinsight.exceptions import InsufficientDataError

class ErrorPage(BasePage):
    @property
    def question_number(self): return 1
    @property
    def question_title(self): return "Error"
    @property
    def author(self): return "Test"
    def _render_key_figures(self): st.metric("K", "1")
    def _render_body(self): raise InsufficientDataError("Pas assez.")

ErrorPage(FakeDataProvider()).render()
"""
        )
        at.run()
        assert not at.exception
        assert len(at.warning) > 0

    def test_unexpected_error_shows_st_error(self):
        at = AppTest.from_string(
            """
import streamlit as st
from railinsight.adapters.fake_data_provider import FakeDataProvider
from railinsight.ui.base_page import BasePage

class CrashPage(BasePage):
    @property
    def question_number(self): return 1
    @property
    def question_title(self): return "Crash"
    @property
    def author(self): return "Test"
    def _render_key_figures(self): st.metric("K", "1")
    def _render_body(self): raise RuntimeError("boom")

CrashPage(FakeDataProvider()).render()
"""
        )
        at.run()
        assert not at.exception
        assert len(at.error) > 0
