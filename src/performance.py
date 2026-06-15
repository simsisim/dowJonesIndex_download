"""
Compute absolute and relative (vs benchmark) % returns from daily CSVs.

Lookback periods (trading days):
    1d=1, 5d=5, 1m=21, 3m=63, 6m=126, 1y=252

A period is skipped (None) when either the sector index or the benchmark
has fewer rows than required on their common trading dates.

vs_bm % formula: ((1 + ind_return) / (1 + bm_return) - 1) × 100
"""

import os

import pandas as pd

from .config import PARAMS_DIR

PERIODS = [
    ("1d",   1),
    ("5d",   5),
    ("1m",  21),
    ("3m",  63),
    ("6m", 126),
    ("1y", 252),
]


def _load_close(folder: str, safe_symbol: str) -> pd.Series | None:
    path = os.path.join(folder, f"{safe_symbol}.csv")
    if not os.path.isfile(path):
        return None
    try:
        df = pd.read_csv(path, index_col="Date")
        # Normalize index to tz-naive date (handles mixed UTC offsets like -04:00/-05:00)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None).normalize()
        return df["Close"].sort_index().dropna()
    except Exception:
        return None


def compute_performance(
    tickers_df: pd.DataFrame,
    benchmark: str = "GSPC",
    daily_dir: str | None = None,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
        symbol, name, sector, data_date,
        return_1d … return_1y   (abs % return of the index)
        vs_bm_1d  … vs_bm_1y   (relative % vs benchmark)

    Columns are None when insufficient history exists.
    """
    if daily_dir is None:
        daily_dir = PARAMS_DIR["MARKET_DATA_DIR_1d"]

    bm_series = _load_close(daily_dir, benchmark)
    if bm_series is None or bm_series.empty:
        raise FileNotFoundError(
            f"Benchmark '{benchmark}' not found in {daily_dir}. "
            "Run the downloader with benchmarks first."
        )

    rows = []
    for _, t in tickers_df.iterrows():
        safe = t["yf_symbol"].replace("^", "")
        ind_series = _load_close(daily_dir, safe)
        if ind_series is None or ind_series.empty:
            continue

        common = ind_series.index.intersection(bm_series.index).sort_values()
        if len(common) < 2:
            continue

        ind = ind_series.loc[common]
        bm  = bm_series.loc[common]

        row: dict = {
            "symbol":    t["symbol"],
            "name":      t.get("name", ""),
            "sector":    t.get("sector", ""),
            "data_date": common[-1].strftime("%Y-%m-%d"),
        }

        for label, n in PERIODS:
            if len(common) > n:
                ind_ret = ind.iloc[-1] / ind.iloc[-(n + 1)] - 1
                bm_ret  = bm.iloc[-1]  / bm.iloc[-(n + 1)]  - 1
                row[f"return_{label}"] = round(ind_ret * 100, 2)
                row[f"vs_bm_{label}"]  = round(((1 + ind_ret) / (1 + bm_ret) - 1) * 100, 2)
            else:
                row[f"return_{label}"] = None
                row[f"vs_bm_{label}"]  = None

        rows.append(row)

    return pd.DataFrame(rows)
