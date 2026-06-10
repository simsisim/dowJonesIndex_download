"""
Entry point for DJ sector index historical data downloader.

Configuration is read from input/user_data.csv.
CLI flags and presets override the file settings when provided.

Usage:
    python main.py                        # uses input/user_data.csv
    python main.py --preset daily_only
    python main.py --preset full
    python main.py --daily --no-weekly
"""

import argparse
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from src.config import PARAMS_DIR, setup_directories
from src.user_defined_data import read_user_data
from src.ticker_loader import load_tickers
from src.market_data import run_index_data_retrieval


# ── presets (override user_data.csv when --preset is given) ──────────────────
PRESETS = {
    "daily_only": {
        "daily_data":   True,
        "weekly_data":  False,
        "monthly_data": False,
    },
    "full": {
        "daily_data":   True,
        "weekly_data":  True,
        "monthly_data": True,
    },
    "weekly_monthly": {
        "daily_data":   False,
        "weekly_data":  True,
        "monthly_data": True,
    },
}


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Download DJ sector index OHLCV data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Config file: input/user_data.csv  (edit to change defaults)

Presets:
  daily_only      Daily data only
  full            Daily + Weekly + Monthly
  weekly_monthly  Weekly + Monthly

Examples:
  python main.py
  python main.py --preset daily_only
  python main.py --daily --no-weekly
        """,
    )
    parser.add_argument("--preset", choices=PRESETS.keys())
    parser.add_argument("--report", action="store_true", help="Show data coverage summary and exit")
    parser.add_argument("--daily",      dest="daily_data",   action="store_true",  default=None)
    parser.add_argument("--no-daily",   dest="daily_data",   action="store_false")
    parser.add_argument("--weekly",     dest="weekly_data",  action="store_true",  default=None)
    parser.add_argument("--no-weekly",  dest="weekly_data",  action="store_false")
    parser.add_argument("--monthly",    dest="monthly_data", action="store_true",  default=None)
    parser.add_argument("--no-monthly", dest="monthly_data", action="store_false")
    return parser.parse_args()


# ── coverage report ───────────────────────────────────────────────────────────
def coverage_report():
    setup_directories()
    tickers_df = load_tickers()

    interval_map = [
        ("daily",   PARAMS_DIR["MARKET_DATA_DIR_1d"]),
        ("weekly",  PARAMS_DIR["MARKET_DATA_DIR_1wk"]),
        ("monthly", PARAMS_DIR["MARKET_DATA_DIR_1mo"]),
    ]

    # Only report intervals that have at least one file
    active = [(label, folder) for label, folder in interval_map
              if any(f.endswith(".csv") for f in os.listdir(folder))]

    if not active:
        print("No data files found yet. Run python main.py first.")
        return

    for label, folder in active:
        rows = []
        for _, t in tickers_df.iterrows():
            safe    = t["yf_symbol"].replace("^", "")
            fpath   = os.path.join(folder, f"{safe}.csv")
            if os.path.isfile(fpath):
                try:
                    df = pd.read_csv(fpath, index_col="Date", parse_dates=True)
                    count     = len(df)
                    first     = df.index.min().date() if count else "-"
                    last      = df.index.max().date() if count else "-"
                except Exception:
                    count, first, last = 0, "-", "-"
            else:
                count, first, last = 0, "-", "-"

            rows.append({
                "symbol":  t["symbol"],
                "name":    t["name"],
                "sector":  t["sector"],
                "rows":    count,
                "first":   str(first),
                "last":    str(last),
            })

        report = pd.DataFrame(rows)
        total   = len(report)
        has_data = (report["rows"] > 0).sum()
        no_data  = total - has_data

        print(f"\n{'='*72}")
        print(f"  Coverage report — {label.upper()}   "
              f"({has_data}/{total} indexes have data,  {no_data} missing)")
        print(f"{'='*72}")
        print(f"{'Symbol':<12} {'Rows':>5}  {'First':>12}  {'Last':>12}  Name")
        print(f"{'-'*72}")

        for _, r in report.sort_values(["sector", "symbol"]).iterrows():
            flag = "  " if r["rows"] > 0 else "!"
            print(f"{flag}{r['symbol']:<10} {r['rows']:>5}  {r['first']:>12}  {r['last']:>12}  {r['name']}")

        # Save to CSV
        out_path = os.path.join(PARAMS_DIR["LOGS_DIR"], f"coverage_{label}.csv")
        report.to_csv(out_path, index=False)
        print(f"\n  Saved: {out_path}")

    # Failed tickers
    failed_path = os.path.join(PARAMS_DIR["LOGS_DIR"], "failed_tickers.csv")
    if os.path.isfile(failed_path):
        failed = pd.read_csv(failed_path)
        print(f"\n  Tickers with no data on Yahoo Finance ({len(failed)}):")
        for _, r in failed.iterrows():
            print(f"    {r['sc_symbol']:<12} {r['name']}  [{r['error']}]")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    setup_directories()

    # Load config from CSV
    cfg = read_user_data()

    args = parse_args()

    if args.report:
        coverage_report()
        return

    if args.preset:
        for key, val in PRESETS[args.preset].items():
            setattr(cfg, key, val)

    # CLI flags override preset
    for key in ("daily_data", "weekly_data", "monthly_data"):
        val = getattr(args, key)
        if val is not None:
            setattr(cfg, key, val)

    # Print effective config
    print(f"\nyfinance version : {yf.__version__}")
    print(f"Run date         : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Data sources     : {cfg.data_sources}")
    print(f"Daily            : {cfg.daily_data}   (start: {cfg.start_date_daily})")
    print(f"Weekly           : {cfg.weekly_data}   (start: {cfg.start_date_weekly})")
    print(f"Monthly          : {cfg.monthly_data}  (start: {cfg.start_date_monthly})\n")

    # 6. Load tickers
    tickers_df = load_tickers()
    print(f"Tickers: {len(tickers_df)}")

    # 7. Run downloads
    interval_map = [
        ("daily_data",   "1d",  PARAMS_DIR["MARKET_DATA_DIR_1d"],  cfg.start_date_daily),
        ("weekly_data",  "1wk", PARAMS_DIR["MARKET_DATA_DIR_1wk"], cfg.start_date_weekly),
        ("monthly_data", "1mo", PARAMS_DIR["MARKET_DATA_DIR_1mo"], cfg.start_date_monthly),
    ]

    for cfg_key, interval, folder, start_date in interval_map:
        if getattr(cfg, cfg_key):
            run_index_data_retrieval({
                "interval":   interval,
                "folder":     folder,
                "tickers_df": tickers_df,
                "start_date": start_date,
            })

    print("Done.")


if __name__ == "__main__":
    main()
