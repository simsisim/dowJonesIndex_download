import pandas as pd
from dataclasses import dataclass, field


@dataclass
class DownloadConfig:
    # Intervals
    daily_data:   bool = True
    weekly_data:  bool = True
    monthly_data: bool = False

    # Source priority list (tried in order)
    data_sources: list = field(default_factory=lambda: ["yahoo_finance"])

    # Start dates for full-history downloads
    start_date_daily:   str = "1990-01-01"
    start_date_weekly:  str = "1990-01-01"
    start_date_monthly: str = "1990-01-01"


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def read_user_data(file_path: str = "input/user_data.csv") -> DownloadConfig:
    """Read key-value config CSV; lines starting with # are comments."""
    cfg = DownloadConfig()

    try:
        df = pd.read_csv(file_path, comment="#", header=None,
                         names=["variable", "value", "description"])
        df = df.dropna(subset=["variable"])
        df["variable"] = df["variable"].str.strip()
        df["value"]    = df["value"].astype(str).str.strip()

        for _, row in df.iterrows():
            var, val = row["variable"], row["value"]

            if var == "daily_data":
                cfg.daily_data = _parse_bool(val)
            elif var == "weekly_data":
                cfg.weekly_data = _parse_bool(val)
            elif var == "monthly_data":
                cfg.monthly_data = _parse_bool(val)
            elif var == "data_sources":
                cfg.data_sources = [s.strip() for s in val.split(",") if s.strip()]
            elif var == "start_date_daily":
                cfg.start_date_daily = val
            elif var == "start_date_weekly":
                cfg.start_date_weekly = val
            elif var == "start_date_monthly":
                cfg.start_date_monthly = val

    except FileNotFoundError:
        print(f"Config file not found: {file_path} — using defaults")
    except Exception as e:
        print(f"Error reading config: {e} — using defaults")

    return cfg
