"""Central provider factory for the frontend.

All pages get their DataProvider from get_provider().
To swap the backend (fake → real), change only this module.

st.cache_resource is used because the provider is a long-lived singleton,
shared across all user sessions for the lifetime of the server process.
It is different from st.cache_data (which caches DataFrames per set of args
and can be cleared per user). Rule of thumb:
  - st.cache_resource  → objects (DB connections, ML models, singletons)
  - st.cache_data      → data (DataFrames, JSON results of computations)
"""

import streamlit as st

from railinsight.interfaces.data_protocols import DataProvider


@st.cache_resource
def get_provider() -> DataProvider:
    """Return the shared DataProvider instance (created once per server process).

    Returns:
        A BackendAdapter (or FakeDataProvider in tests) satisfying DataProvider.
    """
    from railinsight.adapters.backend_adapter import BackendAdapter

    return BackendAdapter()
