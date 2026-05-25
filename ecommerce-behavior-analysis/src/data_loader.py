"""
Data Loader — unified interface for loading and caching project datasets.
"""

import pandas as pd
from pathlib import Path
import hashlib
import pickle
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, data_dir: str = "data", cache_dir: str = ".cache"):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _cache_path(self, filename: str) -> Path:
        key = hashlib.md5(filename.encode()).hexdigest()
        return self.cache_dir / f"{key}.pkl"

    def _load(self, filename: str, **kwargs) -> pd.DataFrame:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Data file not found: {path}\n"
                f"Run `python data/generate_sample_data.py` to generate sample data."
            )

        cache = self._cache_path(filename)
        file_mtime = path.stat().st_mtime

        if cache.exists():
            with open(cache, "rb") as f:
                cached = pickle.load(f)
            if cached.get("mtime") == file_mtime:
                logger.debug(f"Cache hit: {filename}")
                return cached["df"]

        logger.info(f"Loading {filename}...")
        df = pd.read_csv(path, **kwargs)
        with open(cache, "wb") as f:
            pickle.dump({"mtime": file_mtime, "df": df}, f)
        return df

    def customers(self) -> pd.DataFrame:
        return self._load("customers.csv", parse_dates=["signup_date"])

    def transactions(self) -> pd.DataFrame:
        return self._load("transactions.csv", parse_dates=["order_date"])

    def sessions(self) -> pd.DataFrame:
        return self._load("sessions.csv", parse_dates=["session_date"])
