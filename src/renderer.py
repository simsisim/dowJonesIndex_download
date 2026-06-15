"""
Render a dark-theme performance table as a PNG using matplotlib.

Columns:
    Symbol/BM | Sector | Name | [1D% | vs BM%] | [5D% | vs BM%] | ...

Only periods with at least one non-null value across all rows are shown.
Green/red cell coloring scales with magnitude (capped at ±10 % = full intensity).

Output:
    snapshots/Snapshot_YYYY-MM-DD_HH-MM-SS.png   (timestamped)
    snapshots/latest.png                          (always overwritten)
"""

import math
import os
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

from .config import PARAMS_DIR

# ── palette ───────────────────────────────────────────────────────────────────
_BG_DARK   = "#0d1117"
_BG_TABLE  = "#161b22"
_BG_HEADER = "#21262d"
_FG_TEXT   = "#e6edf3"
_FG_DIM    = "#8b949e"
_BORDER    = "#30363d"

# Period definitions in display order
_PERIODS = [
    ("1d",  "1D"),
    ("5d",  "5D"),
    ("1m",  "1M"),
    ("3m",  "3M"),
    ("6m",  "6M"),
    ("1y",  "1Y"),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _cell_color(val, cap: float = 10.0):
    """RGBA background for a % value. Intensity scales 0→cap %."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return mcolors.to_rgba(_BG_TABLE)
    intensity = min(abs(val) / cap, 1.0) * 0.75
    if val > 0:
        return (0.0, 0.55, 0.2, intensity)
    if val < 0:
        return (0.75, 0.1, 0.1, intensity)
    return mcolors.to_rgba(_BG_TABLE)


def _fmt(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def _col_has_data(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns and df[col].notna().any()


# ── main renderer ─────────────────────────────────────────────────────────────

def render_snapshot(
    df: pd.DataFrame,
    benchmark: str = "SPX",
    sort_by: str = "vs_bm_5d",
    output_dir: str | None = None,
    snapshot_date: str | None = None,
) -> str:
    """
    Render *df* as a dark-theme PNG table and return the output path.

    df must contain: symbol, sector, name
    and any subset of return_{period} / vs_bm_{period} columns.
    """
    if output_dir is None:
        output_dir = PARAMS_DIR.get("SNAPSHOTS_DIR", "snapshots")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Determine which periods have data
    available = [
        (key, label)
        for key, label in _PERIODS
        if _col_has_data(df, f"return_{key}") or _col_has_data(df, f"vs_bm_{key}")
    ]

    # Sort rows
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False, na_position="last")
    df = df.reset_index(drop=True)

    # Build flat column list
    col_headers = ["Symbol / BM", "Sector", "Name"]
    val_cols: list[str] = []
    for key, label in available:
        col_headers.append(f"{label} %")
        col_headers.append(f"vs {benchmark} %")
        val_cols.append(f"return_{key}")
        val_cols.append(f"vs_bm_{key}")

    n_rows = len(df)
    n_cols = 3 + len(val_cols)

    # Build cell data and colors
    cell_text:   list[list[str]]   = []
    cell_colors: list[list[tuple]] = []

    neutral = mcolors.to_rgba(_BG_TABLE)

    for _, row in df.iterrows():
        sym  = str(row.get("symbol", "")).lstrip("$^")
        sect = str(row.get("sector", ""))
        name = str(row.get("name", ""))

        texts  = [f"{sym} / {benchmark}", sect, name]
        colors = [neutral, neutral, neutral]

        for col in val_cols:
            val = row.get(col)
            if isinstance(val, float) and math.isnan(val):
                val = None
            texts.append(_fmt(val))
            colors.append(_cell_color(val))

        cell_text.append(texts)
        cell_colors.append(colors)

    # ── figure sizing ─────────────────────────────────────────────────────────
    # Fixed-width columns (inches): symbol, sector, name, then value cols
    col_w = [2.0, 2.2, 3.0] + [1.05] * len(val_cols)
    fig_w = sum(col_w) + 0.3
    row_h = 0.26
    fig_h = 0.6 + n_rows * row_h + 0.5          # title + rows + footer

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(_BG_DARK)
    ax.set_facecolor(_BG_DARK)
    ax.axis("off")

    col_w_norm = [w / sum(col_w) for w in col_w]

    tbl = ax.table(
        cellText=cell_text,
        colLabels=col_headers,
        cellColours=cell_colors,
        colWidths=col_w_norm,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)

    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(_BORDER)
        cell.set_linewidth(0.35)
        cell.set_height(row_h / fig_h)

        if r == 0:
            cell.set_facecolor(_BG_HEADER)
            cell.set_text_props(color=_FG_TEXT, fontweight="bold", fontsize=6.8)
        else:
            if c < 3:
                # text columns: left-align
                cell.set_text_props(color=_FG_TEXT, fontsize=6.8, ha="left")
                cell._loc = "left"
            else:
                cell.set_text_props(color=_FG_TEXT, fontsize=7.0, fontweight="bold")

    # ── title & footnote ──────────────────────────────────────────────────────
    ts_label = snapshot_date or datetime.now().strftime("%Y-%m-%d")
    fig.text(
        0.01, 0.985,
        f"DJ US Industry Performance  |  Benchmark: {benchmark}  |  {ts_label}"
        f"  |  sorted by: {sort_by}",
        color=_FG_TEXT, fontsize=8.5, fontweight="bold", va="top",
    )
    fig.text(
        0.01, 0.008,
        "vs BM % = relative return: (1 + ind) / (1 + bm) − 1   "
        "|  — = insufficient history",
        color=_FG_DIM, fontsize=5.5, va="bottom",
    )

    # ── save ──────────────────────────────────────────────────────────────────
    latest   = os.path.join(output_dir, "latest.png")

    plt.savefig(latest, dpi=150, bbox_inches="tight", facecolor=_BG_DARK)
    plt.close(fig)

    print(f"  Snapshot saved: {latest}")
    return latest
