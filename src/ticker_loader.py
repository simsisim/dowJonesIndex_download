import pandas as pd
from src.config import INPUT_CSV, TICKER_PREFIX_MAP


def sc_to_yf(symbol: str) -> str:
    """Convert StockCharts ticker to Yahoo Finance format.
    Example: $DJUSAV -> ^DJUSAV
    """
    for sc_prefix, yf_prefix in TICKER_PREFIX_MAP.items():
        if symbol.startswith(sc_prefix):
            return yf_prefix + symbol[len(sc_prefix):]
    return symbol


def load_tickers(csv_path: str = INPUT_CSV) -> pd.DataFrame:
    """Load ticker list and add yf_symbol column.

    The CSV has sector as the row index, symbol and name as columns.
    We reset the index so sector becomes a regular column.
    """
    df = pd.read_csv(csv_path, index_col=0)
    df.columns = df.columns.str.strip()
    df.index.name = "sector"
    df = df.reset_index()       # sector → column
    df["yf_symbol"] = df["symbol"].apply(sc_to_yf)
    return df
