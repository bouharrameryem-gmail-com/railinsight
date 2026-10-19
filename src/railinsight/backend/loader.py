from pathlib import Path

import pandas as pd

from railinsight.config import DATA_RAW, RAW_FILENAME


def load_raw_data() -> pd.DataFrame:
    """Load the raw SNCF dataset from a CSV file.

    Returns:
        A DataFrame containing the raw dataset.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        pd.errors.ParserError: If the CSV cannot be parsed.
    """
    path: Path = DATA_RAW / RAW_FILENAME

    if not path.is_file():
        raise FileNotFoundError(
            f"Raw data not found: {path}. "
            f"Download the SNCF dataset and save it in {DATA_RAW}."
        )

    return pd.read_csv(path, sep=";")
