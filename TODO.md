# TODO

## 1. Check that every index gets data from Yahoo Finance
Yahoo doesn't carry every Dow Jones index.
- [x] 2026-10-19: compared `input/DowJonesIndex_list.csv` (103 indexes) with `data/market_data/daily/` (102 files).
      Only **DJUSEH** has no data file.
- [x] 2026-10-19: Yahoo has no data for DJUSEH or DJUSIF under any symbol variant tried
      (`^X`, `X`, `^X.X`, Yahoo search). Decision: keep both in the list as they are.
- [x] 2026-10-27: all 104 files have the same 7 trading days (10-16 .. 10-26), no gaps
- [x] 2026-10-30: all 104 files current through 10-29, no gaps (10 days since 10-16)

## 2. Compare values with the stockCharts project (`../stockCharts`)
stockCharts is the ground truth. Only Close can be compared (its summary has no OHLC/volume).
Run: `python tools/compare_stockcharts.py <YYYY-MM-DD>`

- [x] 2026-10-16 (Fri): 102/103 identical (max diff 0.0000%); DJUSIF has no Yahoo data
- [x] Repeat 2x/week for the next 2 weeks:
  - [x] Tue 2026-10-20 (check Mon 10-19 data): 102/103 identical (max diff 0.0000%)
  - [x] Fri 2026-10-23 (check Thu 10-22 data): 102/103 identical (max diff 0.0000%)
  - [x] Tue 2026-10-27 (check Mon 10-26 data): 102/103 identical (max diff 0.0000%)
  - [x] Fri 2026-10-30 (check Thu 10-29 data): 102/103 identical (max diff 0.0000%)

## 3. Check for missing industries
- [x] 2026-10-19: stockCharts (ground truth) has 103 industries in 11 sectors; ours has 103.
      102 match. Differences: DJUSIF only in stockCharts, DJUSEH only in ours
      (stockCharts dropped it after 2026-07-21). Decision: keep the list as it is.
