# Dow Jones Sector Index — Historical Data Collector

## Scope

This project collects and stores daily OHLCV (Open, High, Low, Close, Volume) data for the **103 Dow Jones US sector indexes** listed on StockCharts.com.

These indexes cover all major GICS sectors (Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Materials, Real Estate, Technology, Utilities) broken down into sub-industry groups (e.g. Banks, Semiconductors, Airlines, Gold Mining, etc.).

**The problem this solves:** Yahoo Finance only exposes the current day's bar for these indexes — there is no historical archive available via its standard API. This script runs daily, appends one new row per index, and gradually builds up a full historical dataset over time.

---

## Data source research

The following sources were tested for historical data availability:

| Source | Result |
|---|---|
| **Yahoo Finance** | Current day only for most tickers. A few (`$DJUSTT`, `$DJUSST`) have full history. |
| **Alpha Vantage** | Empty response — these indexes are not in their catalog. |
| **STOOQ** | Not found. |
| **Tiingo** | 403 Forbidden — not available on free tier. |
| **Google Finance** | Shows indexes in the UI but data is JavaScript-rendered, no extractable API. |

These are **proprietary S&P Dow Jones Indices** — the data is licensed. Paid alternatives that may carry full history: EOD Historical Data (~$20/mo), Barchart OnDemand (~$25/mo).

---

## Project structure

```
dowJones_index/
├── input/
│   ├── DowJonesIndex_list.csv     # 103 DJ sector indexes (from StockCharts)
│   └── user_data.csv              # configuration — edit to control downloads
├── src/
│   ├── config.py                  # directory paths and constants
│   ├── ticker_loader.py           # reads input CSV, converts $TICKER → ^TICKER
│   ├── market_data.py             # download + incremental append logic
│   └── user_defined_data.py       # reads user_data.csv into a config object
├── data/
│   ├── market_data/
│   │   ├── daily/                 # one CSV per index, e.g. DJUSAV.csv
│   │   ├── weekly/                # (disabled by default — same data as daily)
│   │   └── monthly/               # (disabled by default — same data as daily)
│   └── logs/
│       ├── download.log           # run log
│       ├── failed_tickers.csv     # indexes with no data on Yahoo Finance
│       ├── coverage_daily.csv     # coverage report output
│       └── coverage_weekly.csv
├── main.py                        # entry point
├── requirements.txt
└── .github/
    └── workflows/
        └── daily_download.yml     # GitHub Actions — runs Mon-Fri at 22:00 UTC
```

---

## Ticker format

StockCharts uses a `$` prefix (e.g. `$DJUSAV`). Yahoo Finance uses `^` (e.g. `^DJUSAV`). The conversion is automatic — `input/DowJonesIndex_list.csv` uses the StockCharts format and the code converts on the fly.

---

## Configuration — `input/user_data.csv`

Edit this file to control what gets downloaded. No code changes needed.

| Variable | Default | Description |
|---|---|---|
| `daily_data` | `TRUE` | Download daily (1d) OHLCV |
| `weekly_data` | `FALSE` | Download weekly — disabled (same data as daily for these indexes) |
| `monthly_data` | `FALSE` | Download monthly — disabled (same data as daily) |
| `data_sources` | `yahoo_finance` | Sources to try in order (future: `alpha_vantage`, `eod_historical`) |
| `start_date_daily` | `2025-01-01` | Start date for first-time download of each ticker |
| `start_date_weekly` | `2025-01-01` | Start date for weekly (if enabled) |
| `start_date_monthly` | `2025-01-01` | Start date for monthly (if enabled) |

---

## How the append logic works

1. On first run for a ticker: downloads from `start_date_daily` → today, saves `data/market_data/daily/DJUSAV.csv`
2. On subsequent runs: reads the last date in the existing CSV, downloads only from `last_date + 1 day` → today, merges and deduplicates
3. If the file is already current: skips the ticker entirely
4. If Yahoo Finance returns no data: records the ticker in `data/logs/failed_tickers.csv`

CSV columns: `Date, Open, High, Low, Close, Volume` — nothing else.

---

## Running locally

```bash
# Install dependencies (once)
pip install -r requirements.txt

# Run with settings from input/user_data.csv
python main.py

# Or override with a preset
python main.py --preset daily_only     # daily only
python main.py --preset full           # daily + weekly + monthly
python main.py --preset weekly_monthly

# Or override individual flags
python main.py --daily --no-weekly

# Check data coverage (how many rows each index has)
python main.py --report
```

---

## Coverage report

`python main.py --report` prints a table showing, for each index:
- How many rows are stored
- First and last date available
- Which indexes have no data (marked with `!`)

The report is also saved to `data/logs/coverage_daily.csv` for spreadsheet use.

Example output (day 1):
```
========================================================================
  Coverage report — DAILY   (102/103 indexes have data,  1 missing)
========================================================================
Symbol        Rows         First          Last  Name
------------------------------------------------------------------------
  $DJUSAV        1    2026-06-09    2026-06-09  Media Agencies
  $DJUSBK        1    2026-06-09    2026-06-09  Banks
  $DJUSTT     5401    2004-12-20    2026-06-09  Travel & Tourism  ← full history available
  $DJUSST     6619    2000-02-14    2026-06-09  Steel             ← full history available
!$DJUSEH        0             -             -  Real Estate Holding & Development  ← no data
```

---

## GitHub Actions — automated daily schedule

The workflow in `.github/workflows/daily_download.yml` runs automatically:

| Setting | Value |
|---|---|
| Schedule | Monday – Friday |
| Time | 22:00 UTC (6:00 pm EST, after US market close) |
| Manual trigger | Available from the GitHub Actions tab (`workflow_dispatch`) |

After each run it commits the updated CSV files back to the repository, so the data accumulates in git history.

To change the run time, edit the cron expression in `daily_download.yml`:
```yaml
- cron: "0 22 * * 1-5"   # 22:00 UTC Mon-Fri
```

Common alternatives:
```
"0 21 * * 1-5"   →  21:00 UTC / 5:00 pm EST
"30 21 * * 1-5"  →  21:30 UTC / 5:30 pm EST
```

### GitHub setup (first time)

1. Push this folder to a GitHub repository
2. Make sure the repo has **write permissions** for Actions: `Settings → Actions → General → Workflow permissions → Read and write`
3. The workflow runs automatically from that point on

---

## Requirements

```
yfinance >= 0.2.40
pandas  >= 2.0.0
```

Install: `pip install -r requirements.txt`
