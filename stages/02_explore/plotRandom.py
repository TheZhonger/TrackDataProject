#!/usr/bin/env python3
"""
Plot time distributions for five track events as a grid of histograms.

Compares the legacy CA and NY boys 1600 m lists (<scrape output>/legacy/), each
with the header:  name,time,team,grade,state,date
"""

import argparse
import re
import sys
from pathlib import Path

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import EXPLORE_OUT, LEGACY

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LINKS = [LEGACY / "CA" / "m" / "1600r.csv", LEGACY / "NY" / "m" / "1600.csv"]


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

    # 1. Calculate Q1 (25th percentile) and Q3 (75th percentile)
    Q1 = np.quantile(times, 0.25)
    Q3 = np.quantile(times, 0.75)
    # 2. Calculate IQR
    IQR = Q3 - Q1
    # 3. Define lower and upper limits
    lower_bound = Q1 - 2 * IQR
    upper_bound = Q3 + 2 * IQR

    # 4. Filter out the outliers
    filtered_data = df[(times >= lower_bound) & (times <= upper_bound)]

    return np.array([float(parse_time(x)) for x in filtered_data["time"]], dtype=float)


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
def plot_one(ax, times: np.ndarray, event: int, bins="auto", density=False):
    if times.size == 0:
        ax.set_title(f"{event}m — no data")
        ax.axis("off")
        return

    ax.hist(times, bins=bins, density=density,
            color="#4C72B0", edgecolor="white", linewidth=0.6)

    mean, median, sd = times.mean(), np.median(times), times.std(ddof=1) if times.size > 1 else 0.0

    ax.axvline(mean, color="#C44E52", linestyle="--", linewidth=1.5,
               label=f"mean {seconds_formatter(mean, None)}")
    ax.axvline(median, color="#55A868", linestyle="-", linewidth=1.5,
               label=f"median {seconds_formatter(median, None)}")

    ax.set_title(f"{event}m  (n = {times.size})", fontsize=11)
    ax.set_xlabel("time")
    ax.set_ylabel("density" if density else "count")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(seconds_formatter))
    ax.legend(fontsize=8, frameon=False)

    Q1 = np.quantile(times, 0.25)
    Q3 = np.quantile(times, 0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 2 * IQR
    upper_bound = Q3 + 2.5 * IQR

    # Skew tells you which tail is long: positive = a few slow outliers.
    ax.text(0.98, 0.72, f"sd {sd:.2f}s\nlower bound: {lower_bound:.2f}\nupper bound: {upper_bound:.2f}", transform=ax.transAxes,
            ha="right", fontsize=8, color="0.35")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Histograms of race times by event.")
    p.add_argument("--bins", default="auto",
                   help="'auto' (Freedman-Diaconis vs Sturges), or an integer")
    p.add_argument("--density", action="store_true",
                   help="plot density instead of raw counts")
    p.add_argument("--out", default=EXPLORE_OUT / "ca_ny_1600_histograms.png", type=Path)
    args = p.parse_args()

    bins = int(args.bins) if str(args.bins).isdigit() else args.bins

    # CHANGE PLOT DIMENSIONS HERE ##################################################
    fig, axes = plt.subplots(2, 2, figsize=(13,13))
    flat = axes.flatten()

    for ax, event in zip(flat, LINKS):
        path = event
        plot_one(ax, load_event(path), event, bins=bins, density=True)

    for ax in flat[len(LINKS):]:
        ax.axis("off")

    fig.suptitle("Distribution of race times by event", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    #args.out.parent.mkdir(parents=True, exist_ok=True)
    #fig.savefig(args.out, dpi=300)
    #print(f"saved -> {args.out}")
    plt.show()


if __name__ == "__main__":
    main()