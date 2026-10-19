# TODO

## 1. Check that every index gets data from Yahoo Finance
Yahoo doesn't carry every Dow Jones index.
- [ ] Compare `input/DowJonesIndex_list.csv` (103 indexes) with `data/market_data/daily/` (102 files)
  - Known so far: **DJUSEH** has no data file
- [ ] For each missing index, check whether Yahoo uses a different symbol or doesn't carry it at all
- [ ] Remove or replace indexes Yahoo doesn't carry
- [ ] After a few runs, check that every file gains one row per trading day (no gaps)

## 2. Compare values with the stockCharts project (`../stockCharts`)
stockCharts is the ground truth. Only Close can be compared (its summary has no OHLC/volume).
Run: `python tools/compare_stockcharts.py <YYYY-MM-DD>`

- [x] 2026-10-16 (Fri): 102/103 identical (max diff 0.0000%); DJUSIF has no Yahoo data
- [ ] Repeat 2x/week for the next 2 weeks:
  - [ ] Tue 2026-10-20 (check Mon 10-19 data)
  - [ ] Fri 2026-10-23 (check Thu 10-22 data)
  - [ ] Tue 2026-10-27 (check Mon 10-26 data)
  - [ ] Fri 2026-10-30 (check Thu 10-29 data)

## 3. Check for missing industries
- [ ] List all Dow Jones US industries/sectors (DJUS*) and compare with `input/DowJonesIndex_list.csv`
- [ ] Compare with the industry list used in `../stockCharts`
- [ ] Add missing industries, if Yahoo has data for them (see #1)
