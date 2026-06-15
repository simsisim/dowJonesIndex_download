"""
SQLite store for daily performance snapshots.

One row per (snapshot_date, benchmark, symbol).
Upsert on conflict — safe to re-run the same day.

Useful queries:
    db.load_latest("GSPC")              → today's full table
    db.load_date("2026-06-14", "GSPC")  → a specific day
    db.load_history("$DJUSAF", "GSPC")  → one ticker over time (week-over-week)
"""

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

_PERF_COLS = [
    "return_1d", "return_5d", "return_1m", "return_3m", "return_6m", "return_1y",
    "vs_bm_1d",  "vs_bm_5d",  "vs_bm_1m",  "vs_bm_3m",  "vs_bm_6m",  "vs_bm_1y",
]

_ALL_COLS = [
    "snapshot_date", "data_date", "benchmark",
    "symbol", "name", "sector",
] + _PERF_COLS

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    data_date     TEXT NOT NULL,
    benchmark     TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    name          TEXT NOT NULL,
    sector        TEXT NOT NULL,
    return_1d     REAL, return_5d REAL, return_1m REAL,
    return_3m     REAL, return_6m REAL, return_1y REAL,
    vs_bm_1d      REAL, vs_bm_5d  REAL, vs_bm_1m  REAL,
    vs_bm_3m      REAL, vs_bm_6m  REAL, vs_bm_1y  REAL,
    UNIQUE(snapshot_date, benchmark, symbol)
);
"""


class SnapshotDB:

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(_CREATE_SQL)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(
        self,
        df: pd.DataFrame,
        benchmark: str,
        snapshot_date: str | None = None,
    ) -> None:
        today = snapshot_date or date.today().isoformat()

        rows = []
        for _, r in df.iterrows():
            row = {
                "snapshot_date": today,
                "data_date":     r.get("data_date", today),
                "benchmark":     benchmark,
                "symbol":        r["symbol"],
                "name":          r.get("name", ""),
                "sector":        r.get("sector", ""),
            }
            for col in _PERF_COLS:
                v = r.get(col)
                row[col] = None if (v is None or (isinstance(v, float) and __import__("math").isnan(v))) else v
            rows.append(row)

        placeholders = ", ".join(f":{c}" for c in _ALL_COLS)
        cols_sql     = ", ".join(_ALL_COLS)
        updates_sql  = ", ".join(
            f"{c}=excluded.{c}"
            for c in _ALL_COLS
            if c not in ("snapshot_date", "benchmark", "symbol")
        )
        sql = (
            f"INSERT INTO performance_snapshots ({cols_sql}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(snapshot_date, benchmark, symbol) DO UPDATE SET {updates_sql}"
        )
        with self._conn() as conn:
            conn.executemany(sql, rows)

        print(f"  DB: {len(rows)} rows upserted  [{today} / {benchmark}]")

    # ── read ──────────────────────────────────────────────────────────────────

    def load_latest(self, benchmark: str) -> pd.DataFrame:
        sql = """
            SELECT * FROM performance_snapshots
            WHERE benchmark = ?
              AND snapshot_date = (
                  SELECT MAX(snapshot_date)
                  FROM performance_snapshots
                  WHERE benchmark = ?
              )
            ORDER BY sector, symbol
        """
        with self._conn() as conn:
            return pd.read_sql_query(sql, conn, params=(benchmark, benchmark))

    def load_date(self, snapshot_date: str, benchmark: str) -> pd.DataFrame:
        sql = """
            SELECT * FROM performance_snapshots
            WHERE snapshot_date = ? AND benchmark = ?
            ORDER BY sector, symbol
        """
        with self._conn() as conn:
            return pd.read_sql_query(sql, conn, params=(snapshot_date, benchmark))

    def load_history(self, symbol: str, benchmark: str) -> pd.DataFrame:
        """Week-over-week history for a single ticker."""
        sql = """
            SELECT snapshot_date, data_date,
                   return_1d, return_5d, return_1m, return_3m, return_6m, return_1y,
                   vs_bm_1d,  vs_bm_5d,  vs_bm_1m,  vs_bm_3m,  vs_bm_6m,  vs_bm_1y
            FROM performance_snapshots
            WHERE symbol = ? AND benchmark = ?
            ORDER BY snapshot_date
        """
        with self._conn() as conn:
            return pd.read_sql_query(sql, conn, params=(symbol, benchmark))

    def available_dates(self, benchmark: str) -> list[str]:
        sql = """
            SELECT DISTINCT snapshot_date FROM performance_snapshots
            WHERE benchmark = ?
            ORDER BY snapshot_date DESC
        """
        with self._conn() as conn:
            return [r[0] for r in conn.execute(sql, (benchmark,)).fetchall()]
