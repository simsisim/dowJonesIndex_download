# TODO

## 1. Check that every index gets data from Yahoo Finance
Yahoo doesn't carry every Dow Jones index.
- [ ] Compare `input/DowJonesIndex_list.csv` (103 indexes) with `data/market_data/daily/` (102 files)
  - Known so far: **DJUSEH** has no data file
- [ ] For each missing index, check whether Yahoo uses a different symbol or doesn't carry it at all
- [ ] Remove or replace indexes Yahoo doesn't carry
- [ ] After a few runs, check that every file gains one row per trading day (no gaps)

## 2. Compare values with the stockCharts project (`../stockCharts`)
- [ ] Pick a few dates and indexes and compare Close (and OHLC) values between the two projects
- [ ] Note any differences: rounding, timing (end-of-day vs. intraday), or wrong symbol mapping
- [ ] Decide which source to trust when they disagree

## 3. Check for missing industries
- [ ] List all Dow Jones US industries/sectors (DJUS*) and compare with `input/DowJonesIndex_list.csv`
- [ ] Compare with the industry list used in `../stockCharts`
- [ ] Add missing industries, if Yahoo has data for them (see #1)
