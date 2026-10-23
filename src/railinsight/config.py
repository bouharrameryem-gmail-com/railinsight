"""Project-wide paths and constants."""

from pathlib import Path

# The package lives at src/railinsight/, so three .parent calls reach the repo root.
PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

RAW_CSV_PATH = RAW_DATA_DIR / "regularite-mensuelle-tgv-aqst.csv"

CLEAN_MONTHLY_PATH = PROCESSED_DATA_DIR / "clean_monthly.parquet"
ROUTE_FEATURES_PATH = PROCESSED_DATA_DIR / "route_features.parquet"
NETWORK_MONTHLY_PATH = PROCESSED_DATA_DIR / "network_monthly.parquet"
QUALITY_REPORT_PATH = PROCESSED_DATA_DIR / "quality_report.json"
KNOWN_EVENTS_PATH = CONFIG_DIR / "known_events.csv"

DEFAULT_MIN_MONTHS: int = 24
DEFAULT_EXCLUSION: str = "known"
DEFAULT_ADJUST_DURATION: bool = False
