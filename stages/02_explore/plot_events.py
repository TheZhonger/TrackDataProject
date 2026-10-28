#!/usr/bin/env python3
"""
Plot time distributions for five track events as a grid of histograms.

Expects CSV files named 100.csv, 200.csv, ... 1600.csv in a directory (default:
the legacy NY boys folder, <scrape output>/legacy/NY/m/), each with the header:
name,time,team,grade,state,date. Those are the files the old output100.csv ...
output1600.csv names became.

For the 2026 scrape pass --suffix r and a <ST>/<sex>/ folder: the files are
100r.csv ... 800r.csv, and the mile slot becomes whichever of 1600r / 1miler /
1500r that state runs (src/distances.event_stems), plotted as run, unconverted:

    python stages/02_explore/plot_events.py --suffix r \
        --dir stages/01_scrape/output/2026/NY/f --out .../NY_f/event_histograms.png
"""

import argparse
import re
import sys
from pathlib import Path

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import EXPLORE_OUT, LEGACY, SCRAPE_OUT
from distances import event_stems, stem_label
from northeast import EVENTS as NE_EVENTS, pool_label, pooled_rows

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EVENTS = [100, 200, 400, 800, 1600]


# ---------------------------------------------------------------------------
# 1. Turn the "time" column into a single number (seconds)
# ---------------------------------------------------------------------------
def parse_time(raw) -> float:
    """Convert '10.52', '2:05.31', or '1:02:03.4' into seconds as a float.

    Everything downstream (mean, median, binning) needs times on a single
    numeric scale. '2:05.31' and '10.52' are not comparable as strings, so we
    normalize to seconds. Unparseable entries become NaN and get dropped.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return np.nan

    s = str(raw).strip()
    # Drop annotation junk that meet results love: '10.52a', '4:31.02h', '*', '#'
    s = re.sub(r"[^0-9:.]", "", s)
    if not s:
        return np.nan

    parts = s.split(":")
    try:
        if len(parts) == 1:                       # SS.ss
            return float(parts[0])
        if len(parts) == 2:                       # MM:SS.ss
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:                       # HH:MM:SS.ss
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return np.nan
    return np.nan


def load_event(path: Path) -> np.ndarray:
    """Read one CSV and return a clean 1-D array of finite times in seconds."""
    df = pd.read_csv(path)
    if "time" not in df.columns:
        raise ValueError(f"{path.name} has no 'time' column (found: {list(df.columns)})")

    times = df["time"].map(parse_time).to_numpy(dtype=float)
    n_bad = np.count_nonzero(np.isnan(times))
    if n_bad:
        print(f"  {path.name}: dropped {n_bad} unparseable time(s)")
    return times[np.isfinite(times)]


# ---------------------------------------------------------------------------
# 2. Cosmetic helper: label the x-axis in m:ss once times exceed a minute
# ---------------------------------------------------------------------------
def seconds_formatter(x, _pos):
    if x < 60:
        return f"{x:.1f}"
    minutes, seconds = divmod(x, 60)
    return f"{int(minutes)}:{seconds:04.1f}"


# ---------------------------------------------------------------------------
# 3. Draw one histogram into one subplot
# ---------------------------------------------------------------------------
def plot_one(ax, times: np.ndarray, event, bins="auto", density=False):
    """`event` is the panel's display name, e.g. '100m' or '1 mile'."""
    if times.size == 0:
        ax.set_title(f"{event} — no data")
        ax.axis("off")
        return

    ax.hist(times, bins=bins, density=density,
            color="#4C72B0", edgecolor="white", linewidth=0.6)

    mean, median, sd = times.mean(), np.median(times), times.std(ddof=1) if times.size > 1 else 0.0

    ax.axvline(mean, color="#C44E52", linestyle="--", linewidth=1.5,
               label=f"mean {seconds_formatter(mean, None)}")
    ax.axvline(median, color="#55A868", linestyle="-", linewidth=1.5,
               label=f"median {seconds_formatter(median, None)}")

    ax.set_title(f"{event}  (n = {times.size})", fontsize=11)
    ax.set_xlabel("time")
    ax.set_ylabel("density" if density else "count")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(seconds_formatter))
    # m:ss labels are wide; past ~6 ticks they run into each other.
    ax.xaxis.set_major_locator(plt.MaxNLocator(6))
    ax.legend(fontsize=8, frameon=False)

    # Skew tells you which tail is long: positive = a few slow outliers.
    ax.text(0.98, 0.72, f"sd {sd:.2f}s", transform=ax.transAxes,
            ha="right", fontsize=8, color="0.35")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Histograms of race times by event.")
    p.add_argument("--dir", default=LEGACY / "NY" / "m", type=Path,
                   help="folder holding 100.csv ... 1600.csv")
    p.add_argument("--suffix", default="",
                   help="'r' for the restricted 2026 files (100r.csv ...); the "
                        "mile slot then follows the state's own mile event")
    p.add_argument("--title", default="Distribution of race times by event")
    p.add_argument("--pool", choices=["northeast"], default=None,
                   help="pool all nine northeast states (src/northeast.py); "
                        "the mile goes onto 1600 m boys / 1500 m girls. "
                        "--dir and --suffix are ignored")
    p.add_argument("--year", default="2026", help="scrape year for --pool")
    p.add_argument("--sex", default="m", choices=["m", "f"], help="sex for --pool")
    p.add_argument("--bins", default="auto",
                   help="'auto' (Freedman-Diaconis vs Sturges), or an integer")
    p.add_argument("--density", action="store_true",
                   help="plot density instead of raw counts")
    p.add_argument("--out", default=EXPLORE_OUT / "event_histograms_density.png", type=Path)
    args = p.parse_args()

    bins = int(args.bins) if str(args.bins).isdigit() else args.bins

    # 2 rows x 3 cols = 6 slots for 5 events; the spare gets switched off.
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    flat = axes.flatten()

    if args.pool:
        # One panel per event, all nine states stacked (src/northeast.py).
        for ax, event in zip(flat, NE_EVENTS):
            rows = pooled_rows(SCRAPE_OUT / args.year, args.sex, event)
            plot_one(ax, rows["seconds"].to_numpy(dtype=float),
                     pool_label(event, args.sex), bins=bins, density=True)
            ax.text(0.98, 0.64, f"{rows.attrs['n_fenced']} slow junk rows fenced",
                    transform=ax.transAxes, ha="right", fontsize=7, color="0.45")
        stems = []
    else:
        stems = (event_stems(args.dir, args.suffix) if args.suffix
                 else [str(e) for e in EVENTS])
    for ax, stem in zip(flat, stems):
        path = args.dir / f"{stem}.csv"
        if not path.exists():
            ax.set_title(f"{stem_label(stem)} — file missing")
            ax.axis("off")
            print(f"  missing: {path}")
            continue
        plot_one(ax, load_event(path), stem_label(stem), bins=bins, density=True)

    for ax in flat[len(EVENTS):]:
        ax.axis("off")

    fig.suptitle(args.title, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=300)
    print(f"saved -> {args.out}")
    plt.show()


if __name__ == "__main__":
    main()
