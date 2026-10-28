#!/usr/bin/env python3
"""
Plot WHEN each event's marks were set, as a grid of date histograms.

Reads the legacy NY boys files (<scrape output>/legacy/NY/m/100r.csv, 200.csv,
400.csv, 800.csv, 1600.csv), each with the header:  name,time,team,grade,state,date

Also re-exports parse_time / seconds_formatter / parseDate from src/util.py:
other scripts historically imported them from here, and still can.
"""

import argparse
import sys
from pathlib import Path

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import EXPLORE_OUT, LEGACY
from util import parseDate, parse_time, seconds_formatter  # noqa: F401  (re-exported)
from distances import event_stems, stem_label
from northeast import EVENTS as NE_EVENTS, pool_label, pooled_rows
from paths import SCRAPE_OUT

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

FRONTPATH = LEGACY / "NY" / "m"
LINKS = ["100r", "200", "400", "800", "1600"]


# ---------------------------------------------------------------------------
# 1. Read one event's dates
# ---------------------------------------------------------------------------
def load_event(path: str) -> np.ndarray:
    """Read one CSV and return its meet dates as matplotlib float days."""
    df = pd.read_csv(FRONTPATH / f"{path}.csv")
    if "date" not in df.columns:
        raise ValueError(f"{path}.csv has no 'date' column (found: {list(df.columns)})")

    dates = df["date"].map(parseDate)
    numerical_dates = mdates.date2num(dates)
    return numerical_dates


# ---------------------------------------------------------------------------
# 2. (parse_time and seconds_formatter moved to src/util.py)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Draw one histogram into one subplot
# ---------------------------------------------------------------------------
def plot_one(ax, bins, dates, event: int, density=False):

    ax.hist(dates, bins=bins, density=density,
            color="#4C72B0", edgecolor="white", linewidth=0.6)

    ax.set_title(f"{stem_label(event)}  (n = {dates.size})", fontsize=11)
    ax.set_xlabel("date")
    ax.set_ylabel("density" if density else "count")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m %d'))



# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Histograms of race times by event.")
    p.add_argument("--bins", default="auto",
                   help="'auto' (Freedman-Diaconis vs Sturges), or an integer")
    p.add_argument("--density", action="store_true",
                   help="plot density instead of raw counts")
    p.add_argument("--out", default=EXPLORE_OUT / "date_histograms.png", type=Path)
    p.add_argument("--dir", default=None, type=Path,
                   help="a <ST>/<sex>/ folder (default: legacy NY boys)")
    p.add_argument("--suffix", default="",
                   help="'r' for the restricted 2026 files; the mile slot then "
                        "follows the state's own mile event")
    p.add_argument("--title", default="Distribution of dates of event run")
    p.add_argument("--pool", choices=["northeast"], default=None,
                   help="pool all nine northeast states (src/northeast.py); "
                        "the mile goes onto 1600 m boys / 1500 m girls. "
                        "--dir and --suffix are ignored")
    p.add_argument("--year", default="2026", help="scrape year for --pool")
    p.add_argument("--sex", default="m", choices=["m", "f"], help="sex for --pool")
    p.add_argument("--save", action="store_true",
                   help="write the figure to --out instead of only showing it")
    args = p.parse_args()

    bins = int(args.bins) if str(args.bins).isdigit() else args.bins

    # CHANGE PLOT DIMENSIONS HERE ##################################################
    fig, axes = plt.subplots(2, 3, figsize=(13,13))
    flat = axes.flatten()

    edges = pd.date_range("2026-03-16", "2026-06-29", freq="W")
    # load_event reads FRONTPATH, so point it at --dir before loading anything.
    global FRONTPATH
    if args.dir is not None:
        FRONTPATH = args.dir
    links = event_stems(FRONTPATH, args.suffix) if args.suffix else LINKS
    if args.pool:
        links = [pool_label(e, args.sex) for e in NE_EVENTS]
        pooled = {pool_label(e, args.sex): pooled_rows(SCRAPE_OUT / args.year, args.sex, e)
                  for e in NE_EVENTS}
    for ax, event in zip(flat, links):
        if args.pool:
            dates = mdates.date2num(pooled[event]["date"].map(parseDate))
        else:
            dates = load_event(event)
        plot_one(ax, edges, dates, event, density=True)

    for ax in flat[len(links):]:
        ax.axis("off")

    fig.suptitle(args.title, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    if args.save:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.out, dpi=300)
        print(f"saved -> {args.out}")
    plt.show()

if __name__ == "__main__":
    main()
