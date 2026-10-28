#!/usr/bin/env python3
"""
Linear regression of race time against meet date, one model per event.

Asks a single question: do times get faster as the outdoor season progresses?
X is the date the race was run, Y is the finish time in seconds.

By default the fit uses only the TOP_N fastest performances per event. The raw
files are leaderboards with a long junk tail (a 30.33 "100m"), and those few
rows swing the slope hard -- see --sweep, which prints slope and R2 across a
range of cutoffs. Note the slope is genuinely sensitive to the cutoff in both
directions: keeping the tail lets outliers steepen it, while cutting deeper
truncates on the dependent variable and attenuates it toward zero. Treat the
cutoff as part of the question being asked, not as mere cleaning.

Expects CSV files named 100r.csv, 200.csv, ... in the legacy NY boys folder
(<scrape output>/legacy/NY/m/), each with the
header:  name,time,team,grade,state,date
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, root_mean_squared_error

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import EXPLORE_OUT, LEGACY
from util import parseDate, parse_time, seconds_formatter
from distances import event_stems, stem_label
from northeast import EVENTS as NE_EVENTS, pool_label, pooled_rows
from paths import SCRAPE_OUT

FRONTPATH = LEGACY / "NY" / "m"
LINKS = ["100r", "200", "400", "800", "1600"]

# Same window plotByDate.py bins over: the NY outdoor season. It holds >99.5%
# of every file; the handful of Jan/Feb/Jul/Aug rows outside it are off-season
# or mis-scraped meets that would be high-leverage outliers on a linear fit.
WINDOW_START = pd.Timestamp("2026-03-16")
WINDOW_END = pd.Timestamp("2026-06-29")

# Default depth of field. 1000 drops the junk tail outright (the slowest 100m
# left is 11.71s, versus 30.33s with the tail kept) while still holding 57-72
# distinct meet dates per event and the full late-March-to-late-June span, so
# the fit keeps its early-season leverage. It is also uniform across events,
# which makes the five slopes comparable at roughly equal depth of field.
TOP_N = 1000

# Cutoffs --sweep reports over. None means "no cutoff, use everything".
SWEEP_NS = [250, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, None]


# ---------------------------------------------------------------------------
# 1. Load one event into (days-since-season-start, seconds)
# ---------------------------------------------------------------------------
def load_event(event: str):
    """Return one event's in-season rows as a frame sorted fastest-first.

    Columns are 'date' and 'seconds'. Sorting here lets callers take the top N
    with .head(n) without re-sorting per cutoff.
    """
    df = pd.read_csv(FRONTPATH / f"{event}.csv")
    for col in ("date", "time"):
        if col not in df.columns:
            raise ValueError(f"{event}.csv has no '{col}' column (found: {list(df.columns)})")
    return clean_frame(df["date"], df["time"].map(parse_time))


def clean_frame(raw_dates, times):
    """In-season (date, seconds) rows, fastest first. Shared by the per-file
    and the --pool paths so both apply the same season window."""
    # parseDate returns None for anything it cannot read; coerce to NaT and drop
    # rather than crashing on it.
    dates = pd.to_datetime(raw_dates.map(parseDate), errors="coerce")

    keep = dates.notna() & times.notna() & (dates >= WINDOW_START) & (dates <= WINDOW_END)
    clean = pd.DataFrame({"date": dates[keep], "seconds": times[keep]})
    return clean.sort_values("seconds").reset_index(drop=True)


def to_xy(frame):
    """Split a loaded frame into the (n, 1) day offsets sklearn wants and y."""
    X = (frame["date"] - WINDOW_START).dt.days.to_numpy(dtype=float).reshape(-1, 1)
    y = frame["seconds"].to_numpy(dtype=float)
    return X, y


def take_top(frame, top_n):
    """Keep the top_n fastest rows; top_n of None means keep everything."""
    return frame if top_n is None else frame.head(top_n)


# ---------------------------------------------------------------------------
# 2. Fit one event
# ---------------------------------------------------------------------------
def fit_event(X, y):
    """Fit time ~ date and return the model plus its summary stats."""
    model = LinearRegression().fit(X, y)
    pred = model.predict(X)
    slope_day = float(model.coef_[0])
    return model, {
        "n": len(y),
        "slope_day": slope_day,
        "slope_week": slope_day * 7,
        "intercept": float(model.intercept_),   # predicted time on WINDOW_START
        "r2": r2_score(y, pred),
        "rmse": root_mean_squared_error(y, pred),
    }


# ---------------------------------------------------------------------------
# 3. Draw one scatter + fit line into one subplot
# ---------------------------------------------------------------------------
def plot_one(ax, edges, dates, y, model, stats, event: str):
    # Point count swings from a few hundred to ~8k depending on --top, so scale
    # the alpha with it: dense clouds need transparency to show structure, thin
    # ones disappear at the same setting.
    alpha = float(np.clip(350 / max(stats["n"], 1), 0.1, 0.6))
    ax.scatter(dates, y, s=4, alpha=alpha, color="#4C72B0", edgecolors="none")

    span = np.array([[0.0], [(WINDOW_END - WINDOW_START).days]])
    ax.plot([WINDOW_START, WINDOW_END], model.predict(span),
            color="#C44E52", linewidth=2)

    ax.set_title(f"{stem_label(event)}  (n = {stats['n']})", fontsize=11)
    ax.set_xlabel("date")
    ax.set_ylabel("time")
    ax.set_xlim(WINDOW_START, WINDOW_END)
    ax.set_xticks(edges)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m %d"))
    ax.yaxis.set_major_formatter(seconds_formatter)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

    ax.annotate(f"{stats['slope_week']:+.3f} s/week\nR2 = {stats['r2']:.3f}",
                xy=(0.03, 0.03), xycoords="axes fraction",
                fontsize=9, va="bottom",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, linewidth=0))


# ---------------------------------------------------------------------------
# 4. Cutoff sensitivity report
# ---------------------------------------------------------------------------
def sweep(frames):
    """Print slope and R2 across a range of top-N cutoffs, per event.

    The point is to make the cutoff's influence visible rather than hide it
    behind one default: the slope moves monotonically with N, so no single
    cutoff is 'the' answer.
    """
    for event, frame in frames.items():
        print(f"\n=== {event}  (in-season n = {len(frame)}) ===")
        header = (f"{'top N':>6}  {'used':>6}  {'slowest':>8}  "
                  f"{'s/week':>9}  {'R2':>7}  {'dates':>5}")
        print(header)
        print("-" * len(header))
        for n in SWEEP_NS:
            sub = take_top(frame, n)
            if len(sub) < 30:               # too few rows for the fit to mean anything
                continue
            X, y = to_xy(sub)
            _, stats = fit_event(X, y)
            print(f"{str(n) if n else 'all':>6}  {len(sub):>6}  {y.max():>8.2f}  "
                  f"{stats['slope_week']:>9.4f}  {stats['r2']:>7.4f}  "
                  f"{sub['date'].nunique():>5}")


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------
def parse_top(raw):
    """--top accepts an integer or 'all'."""
    if str(raw).lower() == "all":
        return None
    n = int(raw)
    if n < 30:
        raise argparse.ArgumentTypeError("--top needs at least 30 rows to fit")
    return n


def main():
    p = argparse.ArgumentParser(description="Linear regression of race time on meet date.")
    p.add_argument("--top", default=TOP_N, type=parse_top,
                   help=f"fit only the N fastest times per event, or 'all' "
                        f"(default: {TOP_N})")
    p.add_argument("--sweep", action="store_true",
                   help="report slope and R2 across a range of --top cutoffs, then exit")
    p.add_argument("--out", default=EXPLORE_OUT / "date_regression.png", type=Path)
    p.add_argument("--dir", default=None, type=Path,
                   help="a <ST>/<sex>/ folder (default: legacy NY boys)")
    p.add_argument("--suffix", default="",
                   help="'r' for the restricted 2026 files; the mile slot then "
                        "follows the state's own mile event")
    p.add_argument("--title", default=None)
    p.add_argument("--pool", choices=["northeast"], default=None,
                   help="pool all nine northeast states (src/northeast.py); "
                        "the mile goes onto 1600 m boys / 1500 m girls. "
                        "--dir and --suffix are ignored")
    p.add_argument("--year", default="2026", help="scrape year for --pool")
    p.add_argument("--sex", default="m", choices=["m", "f"], help="sex for --pool")
    p.add_argument("--save", action="store_true",
                   help="write the figure to --out instead of only showing it")
    args = p.parse_args()

    # load_event reads FRONTPATH, so point it at --dir before loading anything.
    global FRONTPATH
    if args.dir is not None:
        FRONTPATH = args.dir
    links = event_stems(FRONTPATH, args.suffix) if args.suffix else LINKS
    if args.pool:
        # --top now ranks across all nine states: on a 10k-29k pool the default
        # 1000 is the elite 3-10%, not a whole state's field.
        links = [pool_label(e, args.sex) for e in NE_EVENTS]
        frames = {}
        for e, lab in zip(NE_EVENTS, links):
            rows = pooled_rows(SCRAPE_OUT / args.year, args.sex, e)
            frames[lab] = clean_frame(rows["date"], rows["seconds"])
    else:
        frames = {event: load_event(event) for event in links}

    if args.sweep:
        sweep(frames)
        return

    # CHANGE PLOT DIMENSIONS HERE ##################################################
    fig, axes = plt.subplots(2, 3, figsize=(13, 13))
    flat = axes.flatten()

    edges = pd.date_range("2026-03-16", "2026-06-29", freq="W")

    label = "all times" if args.top is None else f"top {args.top} times"
    header = f"{'event':>6}  {'n':>5}  {'s/day':>9}  {'s/week':>9}  {'intercept':>10}  {'R2':>6}  {'RMSE':>7}"
    print(f"fitting {label} per event\n")
    print(header)
    print("-" * len(header))

    for ax, event in zip(flat, links):
        sub = take_top(frames[event], args.top)
        X, y = to_xy(sub)
        model, stats = fit_event(X, y)
        plot_one(ax, edges, sub["date"], y, model, stats, event)
        print(f"{event:>6}  {stats['n']:>5}  {stats['slope_day']:>9.5f}  "
              f"{stats['slope_week']:>9.4f}  {stats['intercept']:>10.3f}  "
              f"{stats['r2']:>6.4f}  {stats['rmse']:>7.3f}")

    print(f"\nintercept = predicted time (s) on {WINDOW_START.date()}")
    print("slopes move with the cutoff -- run --sweep to see by how much")

    for ax in flat[len(links):]:
        ax.axis("off")

    fig.suptitle(args.title or f"Race time vs. date run, with linear fit ({label})",
                 fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    if args.save:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.out, dpi=300)
        print(f"saved -> {args.out}")
    plt.show()


if __name__ == "__main__":
    main()
