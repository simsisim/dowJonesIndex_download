"""
Download and incrementally append OHLCV data for DJ sector indexes from Yahoo Finance.
Mirrors the pattern used in downloadData_v1/src/get_marketData.py.
"""

import os
import time
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from src.config import PARAMS_DIR

log = logging.getLogger(__name__)


class IndexDataRetriever:
    """
    Downloads OHLCV data for a list of index tickers from Yahoo Finance.
    Supports incremental updates: only new rows are fetched after first download.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: dict with keys:
                interval    - '1d', '1wk', or '1mo'
                folder      - output directory for CSV files
                tickers_df  - DataFrame with columns [symbol, yf_symbol, sector, name]
                start_date  - start date string for first-time download (e.g. '1990-01-01')
        """
        self.config = config
        self.interval = config["interval"]
        self.folder = config["folder"]
        self.tickers_df = config["tickers_df"]
        self.start_date = config.get("start_date", "1990-01-01")
        self.failed: list[dict] = []
        self.successful: list[str] = []

    # ── core helpers ──────────────────────────────────────────────────────────

    def _file_path(self, yf_symbol: str) -> str:
        safe = yf_symbol.replace("^", "")   # e.g. ^DJUSAV → DJUSAV.csv
        return os.path.join(self.folder, f"{safe}.csv")

    def _latest_file_date(self, file_path: str):
        """Return most recent date stored in an existing CSV, or None."""
        if not os.path.isfile(file_path):
            return None
        try:
            df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
            if df.empty:
                return None
            idx = df.index.max()
            return idx.date() if hasattr(idx, "date") else pd.to_datetime(str(idx)).date()
        except Exception as e:
            log.warning(f"Could not read {file_path}: {e}")
            return None

    def _latest_yf_date(self, yf_symbol: str):
        """Fetch the most recent available date from Yahoo Finance."""
        try:
            row = yf.Ticker(yf_symbol).history(period="1d")
            if row.empty:
                return None
            idx = row.index[0]
            return idx.date() if hasattr(idx, "date") else pd.to_datetime(str(idx)).date()
        except Exception as e:
            log.warning(f"Could not fetch latest date for {yf_symbol}: {e}")
            return None

    # ── download one ticker ───────────────────────────────────────────────────

    def _update_one(self, yf_symbol: str, sc_symbol: str, name: str, sector: str):
        file_path = self._file_path(yf_symbol)
        latest_yf = self._latest_yf_date(yf_symbol)

        if latest_yf is None:
            self.failed.append({"sc_symbol": sc_symbol, "yf_symbol": yf_symbol,
                                 "sector": sector, "name": name, "error": "no data on YF"})
            return

        latest_file = self._latest_file_date(file_path)

        if latest_file is not None and latest_file >= latest_yf:
            self.successful.append(yf_symbol)
            return

        start_date = self.start_date if latest_file is None else \
                     (latest_file + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        try:
            ticker_obj = yf.Ticker(yf_symbol)
            new_data = ticker_obj.history(start=start_date, end=end_date,
                                          interval=self.interval)
        except Exception as e:
            self.failed.append({"sc_symbol": sc_symbol, "yf_symbol": yf_symbol,
                                 "sector": sector, "name": name, "error": str(e)})
            return

        # Flatten MultiIndex columns (yfinance sometimes returns these)
        if isinstance(new_data.columns, pd.MultiIndex):
            new_data.columns = new_data.columns.get_level_values(0)

        new_data.index.name = "Date"

        # Keep only OHLCV
        ohlcv = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in new_data.columns]
        new_data = new_data[ohlcv]

        if new_data.empty:
            self.successful.append(yf_symbol)
            return

        # Merge with existing data
        if os.path.isfile(file_path):
            existing = pd.read_csv(file_path, index_col="Date", parse_dates=True)
            existing = existing[[c for c in ohlcv if c in existing.columns]]
            merged = pd.concat([existing, new_data])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged.sort_index(inplace=True)
        else:
            merged = new_data

        merged.to_csv(file_path)
        self.successful.append(yf_symbol)

    # ── public entry point ────────────────────────────────────────────────────

    def update_all(self):
        total = len(self.tickers_df)

        for i, (_, row) in enumerate(self.tickers_df.iterrows(), 1):
            self._update_one(
                yf_symbol=row["yf_symbol"],
                sc_symbol=row["symbol"],
                name=row.get("name", ""),
                sector=row.get("sector", ""),
            )
            time.sleep(0.2)
            if i % 50 == 0:
                time.sleep(10)

        self._save_failed()
        print(f"  {self.interval}: {len(self.successful)}/{total} OK"
              + (f"  —  {len(self.failed)} FAILED (see logs/failed_tickers.csv)" if self.failed else ""))

    def _save_failed(self):
        failed_path = os.path.join(PARAMS_DIR["LOGS_DIR"], "failed_tickers.csv")
        if self.failed:
            pd.DataFrame(self.failed).to_csv(failed_path, index=False)
            log.warning(f"{len(self.failed)} failed tickers saved to {failed_path}")
        elif os.path.isfile(failed_path):
            os.remove(failed_path)


def run_index_data_retrieval(config: dict):
    retriever = IndexDataRetriever(config)
    retriever.update_all()
