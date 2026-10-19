"""
Compare daily closes from Yahoo (data/market_data/daily) with stockCharts'
industry summary for one date.  stockCharts is the ground truth.

Usage:
    python tools/compare_stockcharts.py 2026-10-16
"""

import os
import sys

import pandas as pd

SC_DIR = os.path.join("..", "stockCharts", "output", "industry_summary")
YF_DIR = os.path.join("data", "market_data", "daily")


def main(date: str):
    sc = pd.read_csv(os.path.join(SC_DIR, f"{date}_industry_summary.csv"))
    rows = []
    for _, r in sc.iterrows():
        path = os.path.join(YF_DIR, f"{r.symbol.lstrip('$')}.csv")
        yf_close = None
        if os.path.isfile(path):
            d = pd.read_csv(path, index_col="Date")
            if date in d.index:
                yf_close = d.loc[date, "Close"]
        rows.append((r.symbol, r["last"], yf_close))

    df = pd.DataFrame(rows, columns=["symbol", "stockcharts", "yahoo"])
    df["diff_pct"] = (df.yahoo / df.stockcharts - 1) * 100

    missing = df[df.yahoo.isna()]
    compared = df.dropna()
    off = compared[compared.diff_pct.abs() >= 0.01]

    print(f"{date}: {len(compared)}/{len(df)} compared, "
          f"{len(off)} differ by >= 0.01%, max |diff| {compared.diff_pct.abs().max():.4f}%")
    if not missing.empty:
        print("  no Yahoo bar:", ", ".join(missing.symbol))
    if not off.empty:
        print(off.round(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
