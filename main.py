"""
Entry point for DJ sector index historical data downloader + performance snapshot.

Configuration is read from input/user_data.csv.
CLI flags and presets override the file settings when provided.

Usage:
    python main.py                             # download indices + benchmarks
    python main.py --snapshot                  # download + compute + render PNG
    python main.py --snapshot-only             # compute + render from existing data
    python main.py --benchmark NDX             # use Nasdaq-100 as benchmark (default: SPX)
    python main.py --sort-by vs_bm_1d         # sort table column (default: vs_bm_5d)
    python main.py --preset daily_only
    python main.py --preset full
    python main.py --report
"""

import argparse
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from src.config import PARAMS_DIR, DB_PATH, setup_directories
from src.user_defined_data import read_user_data
from src.ticker_loader import load_tickers
from src.market_data import run_index_data_retrieval

# ── benchmark short-name → Yahoo Finance symbol ───────────────────────────────
BENCHMARK_MAP = {
    "SPX": "^GSPC",
    "NDX": "^NDX",
}

# ── presets ───────────────────────────────────────────────────────────────────
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
        description="Download DJ sector index OHLCV data and render performance snapshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Config file: input/user_data.csv  (edit to change defaults)

Presets:
  daily_only      Daily data only
  full            Daily + Weekly + Monthly
  weekly_monthly  Weekly + Monthly

Examples:
  python main.py
  python main.py --snapshot
  python main.py --snapshot --benchmark NDX --sort-by vs_bm_1d
  python main.py --snapshot-only
  python main.py --preset daily_only
  python main.py --report
        """,
    )
    parser.add_argument("--preset",        choices=PRESETS.keys())
    parser.add_argument("--report",        action="store_true",
                        help="Show data coverage summary and exit")
    parser.add_argument("--snapshot",      action="store_true",
                        help="After downloading, compute performance and render PNG")
    parser.add_argument("--snapshot-only", action="store_true",
                        help="Skip download; compute performance and render PNG from existing data")
    parser.add_argument("--benchmark",     default="SPX", choices=list(BENCHMARK_MAP.keys()),
                        help="Benchmark to compare against (default: SPX)")
    parser.add_argument("--sort-by",       default="vs_bm_5d",
                        help="Column to sort snapshot table by (default: vs_bm_5d)")
    parser.add_argument("--daily",         dest="daily_data",   action="store_true",  default=None)
    parser.add_argument("--no-daily",      dest="daily_data",   action="store_false")
    parser.add_argument("--weekly",        dest="weekly_data",  action="store_true",  default=None)
    parser.add_argument("--no-weekly",     dest="weekly_data",  action="store_false")
    parser.add_argument("--monthly",       dest="monthly_data", action="store_true",  default=None)
    parser.add_argument("--no-monthly",    dest="monthly_data", action="store_false")
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

    active = [(label, folder) for label, folder in interval_map
              if any(f.endswith(".csv") for f in os.listdir(folder))]

    if not active:
        print("No data files found yet. Run python main.py first.")
        return

    for label, folder in active:
        rows = []
        for _, t in tickers_df.iterrows():
            safe  = t["yf_symbol"].replace("^", "")
            fpath = os.path.join(folder, f"{safe}.csv")
            if os.path.isfile(fpath):
                try:
                    df    = pd.read_csv(fpath, index_col="Date", parse_dates=True)
                    count = len(df)
                    first = df.index.min().date() if count else "-"
                    last  = df.index.max().date() if count else "-"
                except Exception:
                    count, first, last = 0, "-", "-"
            else:
                count, first, last = 0, "-", "-"

            rows.append({
                "symbol": t["symbol"], "name": t["name"],
                "sector": t["sector"], "rows": count,
                "first": str(first),   "last": str(last),
            })

        report   = pd.DataFrame(rows)
        total    = len(report)
        has_data = (report["rows"] > 0).sum()

        print(f"\n{'='*72}")
        print(f"  Coverage report — {label.upper()}   "
              f"({has_data}/{total} indexes have data,  {total - has_data} missing)")
        print(f"{'='*72}")
        print(f"{'Symbol':<12} {'Rows':>5}  {'First':>12}  {'Last':>12}  Name")
        print(f"{'-'*72}")

        for _, r in report.sort_values(["sector", "symbol"]).iterrows():
            flag = "  " if r["rows"] > 0 else "!"
            print(f"{flag}{r['symbol']:<10} {r['rows']:>5}  {r['first']:>12}  {r['last']:>12}  {r['name']}")

        out_path = os.path.join(PARAMS_DIR["LOGS_DIR"], f"coverage_{label}.csv")
        report.to_csv(out_path, index=False)
        print(f"\n  Saved: {out_path}")

    failed_path = os.path.join(PARAMS_DIR["LOGS_DIR"], "failed_tickers.csv")
    if os.path.isfile(failed_path):
        failed = pd.read_csv(failed_path)
        print(f"\n  Tickers with no data on Yahoo Finance ({len(failed)}):")
        for _, r in failed.iterrows():
            print(f"    {r['sc_symbol']:<12} {r['name']}  [{r['error']}]")


# ── snapshot pipeline ─────────────────────────────────────────────────────────
def run_snapshot(benchmark_short: str, sort_by: str):
    from src.performance import compute_performance
    from src.snapshot_db import SnapshotDB
    from src.renderer import render_snapshot

    bm_yf   = BENCHMARK_MAP[benchmark_short]
    bm_safe = bm_yf.replace("^", "")           # e.g. GSPC

    tickers_df = load_tickers()
    perf_df    = compute_performance(
        tickers_df,
        benchmark=bm_safe,
        daily_dir=PARAMS_DIR["MARKET_DATA_DIR_1d"],
    )

    if perf_df.empty:
        print("  No performance data computed — check that data files exist.")
        return

    # Use the actual last trading date from the data, not the run date
    data_date = perf_df["data_date"].max()

    print(f"\n── Performance snapshot  [{benchmark_short}]  {data_date} ──")

    # Store in SQLite
    db = SnapshotDB(DB_PATH)
    db.upsert(perf_df, benchmark=benchmark_short, snapshot_date=data_date)

    # Render PNG
    render_snapshot(
        perf_df,
        benchmark=benchmark_short,
        sort_by=sort_by,
        output_dir=PARAMS_DIR["SNAPSHOTS_DIR"],
        snapshot_date=data_date,
    )


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    setup_directories()
    cfg  = read_user_data()
    args = parse_args()

    if args.report:
        coverage_report()
        return

    if args.preset:
        for key, val in PRESETS[args.preset].items():
            setattr(cfg, key, val)

    for key in ("daily_data", "weekly_data", "monthly_data"):
        val = getattr(args, key)
        if val is not None:
            setattr(cfg, key, val)

    if not args.snapshot_only:
        print(f"\nyfinance version : {yf.__version__}")
        print(f"Run date         : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Daily            : {cfg.daily_data}   (start: {cfg.start_date_daily})")
        print(f"Weekly           : {cfg.weekly_data}   (start: {cfg.start_date_weekly})")
        print(f"Monthly          : {cfg.monthly_data}  (start: {cfg.start_date_monthly})\n")

        # Download sector indices
        tickers_df = load_tickers()
        print(f"Sector indices   : {len(tickers_df)}")

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

        # Always download benchmarks (daily only — used for performance ratios)
        from src.ticker_loader import load_tickers as _load
        benchmarks_df = _load(csv_path="input/benchmarks.csv")
        print(f"Benchmarks       : {len(benchmarks_df)}")
        run_index_data_retrieval({
            "interval":   "1d",
            "folder":     PARAMS_DIR["MARKET_DATA_DIR_1d"],
            "tickers_df": benchmarks_df,
            "start_date": "1990-01-01",   # full history for benchmarks
        })

    if args.snapshot or args.snapshot_only:
        run_snapshot(
            benchmark_short=args.benchmark,
            sort_by=args.sort_by,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
