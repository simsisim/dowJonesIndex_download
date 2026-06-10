import os

PARAMS_DIR = {
    "DATA_DIR":             "data",
    "LOGS_DIR":             os.path.join("data", "logs"),
    "MARKET_DATA_DIR_1d":   os.path.join("data", "market_data", "daily"),
    "MARKET_DATA_DIR_1wk":  os.path.join("data", "market_data", "weekly"),
    "MARKET_DATA_DIR_1mo":  os.path.join("data", "market_data", "monthly"),
}

# StockCharts $ prefix → Yahoo Finance ^ prefix
TICKER_PREFIX_MAP = {"$": "^"}

INPUT_CSV     = os.path.join("input", "DowJonesIndex_list.csv")
USER_DATA_CSV = os.path.join("input", "user_data.csv")


def setup_directories():
    """Create all required data directories."""
    for path in PARAMS_DIR.values():
        os.makedirs(path, exist_ok=True)
