#!/usr/bin/env python3
"""
Career progression of the top 100 CA boys 1600m runners, across three events.

dateRegression.py fits the leaderboard files, where each athlete appears exactly
once, so it can only ask whether the field as a whole gets faster through one
season. individualScrape.py's output has every mark every one of those athletes
has ever run, which makes a different question askable: does a given runner get
faster over four years of high school, and by how much?

--scale chooses what a rate means. The default, "percent", fits log(time), so
every slope is proportional -- "improves 3.3% per year" rather than "8.9 seconds
per year" -- which is what makes the three events comparable: 40 s/yr in a 5000m
and 9 s/yr in a 1600m sound wildly different but are similar fractions of the
race. A log slope converts exactly as (exp(slope) - 1) * 100 percent.
"--scale seconds" fits time itself and reports s/yr, as on a stopwatch.

Why log(time) rather than percent change from the previous race: differencing
consecutive marks answers a different question -- whether the rate of
improvement is itself changing -- and pays for it, since each point becomes a
difference of two noisy measurements, one slow race flatters the next change,
and a three-day gap counts the same as an eight-month one. Normalising each
athlete to their own first mark is closer, but that baseline is a single noisy
race, and dividing by it induces a spurious downward slope through regression to
the mean. Regressing log(time) gets the proportional reading from one well-posed
fit with none of that.

Each panel carries two kinds of fit, because they can disagree:

    thin lines   one straight-line fit per athlete, through only that athlete's
                 own marks -- 100 individual four-year trajectories
    bold line    one fit through every point at once, ignoring who ran what

The disagreement is the point. This roster is 64 seniors and 2 freshmen, so a
senior's freshman year sits in 2023 while a freshman's sits in 2026: the late end
of the x-axis is disproportionately underclassmen, who are slower. Every athlete
can be improving while the pooled line comes out flat or rising, purely from who
is present in which year -- Simpson's paradox, and a pooled fit on calendar dates
is the setup for it. So each panel reports both the pooled slope and the median
of the per-athlete slopes. The median answers "how fast does a runner improve";
the pooled slope is what you get if you ignore athlete identity.

Indoor marks are excluded by default: 12 of them in the 1600m and 22 in the 800m
is too thin to fit, and a banked or undersized indoor track shifts times
systematically enough that pooling them with outdoor would bias the very rate
being measured. --indoor puts them back, drawn as distinct markers.

Each panel separates two things R2 alone runs together. The *trend* is known very
precisely -- the 1600m rate is -2.96 %/yr with a 95% interval about 0.3 wide --
while any *single race* is predictable only to a few percent -- +/-8.7 s on a
4:26 1600m, even measured against that runner's own line -- because weather,
tactics, depth of field and fatigue are not in the model and never will be. R2
measures the second of those, which is why it reads a modest 0.36 even though the
slope is nailed down. Both are reported, so neither has to stand in for the
other. The interval is clustered by athlete: one runner's 25 races are not 25
independent draws, and pretending otherwise halves its width.

The pooled R2 is also diluted by mixing athletes: a fifth to a third of the
variance in log time is simply which runner it is, which date cannot explain. For
a given runner a straight line captures ~0.57, not ~0.36, so both numbers appear.

--diagnostics writes a second figure with the distributions behind those
summaries, including a residual plot that exposes the one way the straight line
is systematically wrong -- see the last caveat below.

Three caveats the figure cannot show:

  - Improvement decelerates. Residuals from each athlete's own line form a
    consistent U-shape: positive early in a career, negative in the middle,
    positive again by senior year, about 2% peak to trough. Real trajectories are
    convex, so a straight line understates freshman improvement and overstates
    senior improvement, and the fitted rate is an average over a career that
    front-loads it. This is not the artefact it could easily be mistaken for --
    a three-point fit forces its residuals to alternate in sign -- because the
    pattern strengthens rather than fades when only athletes with 20 or more
    marks are kept, where that constraint cannot bite.

  - Cross country 5000m times are not comparable across meets. Courses differ in
    terrain and true distance, so part of the XC rate is course variation rather
    than fitness. Percent puts the two track panels on equal footing; it does not
    do the same for cross country.
  - These athletes were selected *on* their senior-year 1600m. Improvement toward
    that peak is partly regression to the top, not a clean estimate of how high
    school runners progress in general.

A straight line is a deliberate simplification; real progression plateaus and has
injury gaps, which the per-athlete lines visibly smooth over.

    python plotIndividual.py
    python plotIndividual.py --scale seconds --indoor
    python plotIndividual.py --save --out progression.png
"""

import argparse
import sys
from collections import namedtuple
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import EXPLORE_OUT, INDIVIDUAL
from util import seconds_formatter

DEFAULT_CSV = INDIVIDUAL / "168546-m-1600m.csv"

# Each panel names an event *and* the season types it accepts. Exact names
# matter: matching the substring "800" also catches 'Javelin - 800g', and
# '1600 Meters' exists under Outdoor, Indoor and Cross Country alike.
# Indoor is off by default and --indoor widens any panel that already takes
# Outdoor; see the module docstring for why.
#
# Which set to use follows the roster being plotted: a 1600m leaderboard yields
# distance runners, a 100m leaderboard sprinters who never race cross country.
# Adding a roster type is one entry here rather than a code change.
EVENT_SETS = {
    "distance": [
        ("1600m",    "1600 Meters", {"Outdoor"}),
        ("800m",     "800 Meters",  {"Outdoor"}),
        ("5000m XC", "5000 Meters", {"Cross Country"}),
    ],
    "sprint": [
        ("100m", "100 Meters", {"Outdoor"}),
        ("200m", "200 Meters", {"Outdoor"}),
        ("400m", "400 Meters", {"Outdoor"}),
    ],
}
DEFAULT_EVENT_SET = "distance"


def _same(v):
    return v


# What a "rate" means. Everything that differs between the two modes lives here,
# so no function downstream has to branch on which one is active.
Scale = namedtuple("Scale", "forward inverse unit rate")

SCALES = {
    # Proportional: fit log(time), so the slope is a fraction per unit time and
    # the three events compare directly. The conversion is exact rather than the
    # small-slope approximation that treats a log slope as a percentage outright.
    "percent": Scale(np.log, np.exp, "%/yr", lambda slope: (np.exp(slope) - 1) * 100),
    # Absolute: fit time itself. The slope is seconds per year, as on a stopwatch.
    "seconds": Scale(_same, _same, "s/yr", _same),
}
DEFAULT_SCALE = "percent"

# Physically impossible marks, which are athletic.net entries that lost a colon:
# a '4.51' 1600m and a '2.13' 800m, both the same athlete at the same 2023 meet.
# On the distance events these bounds drop exactly those two rows and nothing
# else. The sprint bounds are calibrated against the leaderboard files already on
# disk -- legacy/CA/m/100.csv runs 10.12-17.24 before an 841-second junk entry,
# legacy/NY/m/200.csv 21.07-35.94, legacy/NY/m/400.csv 46.99-83.08 -- and then given
# room above, since a bio reaches back to middle school and runs slower than any
# leaderboard does.
BOUNDS = {
    "1600 Meters": (200, 600), "800 Meters": (100, 300), "5000 Meters": (700, 1800),
    "100 Meters": (9.5, 25), "200 Meters": (19, 50), "400 Meters": (44, 120),
}

# High school only. Athletic.net bios reach back to youth club meets -- there is a
# 3:47 800m in here from roughly age 9 -- and that early steep improvement would
# anchor every slope while answering a different question.
GRADES = (9, 12)

# Below this an athlete's line is noise. They still get scatter points.
MIN_MARKS = 3

# A high school career is four years. A few athletic.net bios are merged
# profiles holding two different runners under one athlete id -- one here
# reaches back to 2013, another carries both grade 7 and grade 13 in 2021 -- and
# the grade filter cannot separate them, because both runners pass through
# grades 9-12. Anchoring a five-season window on each athlete's final season
# drops the older runner's marks. Without it a lone 2018 6:10 anchors the left
# end of the 1600m panel and drags the pooled fit across an eight-year span.
CAREER_SEASONS = 4

# A few genuinely slow marks -- a 7:29 1600m at a small dual meet -- would
# otherwise squeeze the bulk of the data into the bottom third of the panel. The
# y-axis stops at this percentile instead, and the panel says how many points
# that puts above the top edge, so the clipping is stated rather than hidden.
YLIM_PCT = 99.5

SCATTER = "#4C72B0"     # same palette dateRegression.py uses
POOLED = "#C44E52"
INDOOR = "#DD8452"


# ---------------------------------------------------------------------------
# 1. Load and select
# ---------------------------------------------------------------------------
def load(path):
    """Read the scraped panel once, with the two columns that need coercing."""
    df = pd.read_csv(path, dtype={"athlete_id": str})
    for col in ("event", "season_type", "seconds", "date"):
        if col not in df.columns:
            raise SystemExit(f"{path} has no '{col}' column (found: {list(df.columns)})")

    df["dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["grade_n"] = pd.to_numeric(df["season_grade"], errors="coerce")

    # Every athlete here competed in 2026, so their career window ends at their
    # last season across all events, not just this panel's.
    last = df.groupby("athlete_id")["season_year"].transform("max")
    df["in_career"] = df["season_year"] >= last - CAREER_SEASONS
    return df


def select(df, event, season_types):
    """One panel's rows: the event, its season types, high school, plausible.

    Returns the kept frame and a count of what each guard rejected, so main()
    can report the drops rather than let them happen silently.
    """
    lo, hi = BOUNDS[event]
    hit = (df["event"] == event) & df["season_type"].isin(season_types)
    usable = hit & df["seconds"].notna() & df["dt"].notna() \
        & df["grade_n"].between(*GRADES)

    plausible = df["seconds"].between(lo, hi)
    kept = df[usable & plausible & df["in_career"]]
    return kept.sort_values("dt").reset_index(drop=True), {
        "bounds": int((usable & ~plausible).sum()),
        "career": int((usable & plausible & ~df["in_career"]).sum()),
    }


def to_days(dates, origin):
    """Dates as float days from a common origin, which the fits regress on."""
    return (dates - origin).dt.days.to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# 2. Fit
# ---------------------------------------------------------------------------
def fit(days, seconds, scale):
    """Fit the scale's view of time against days, and report a yearly rate.

    Structurally fit_event() from dateRegression.py:92, with two changes: the
    response goes through scale.forward, so "percent" fits log(time) and the
    three events become comparable, and the rate is annualised, since this spans
    four years of a career rather than one season.

    R2 is measured in whichever space the fit lives in, so the two modes' R2 are
    not the same quantity and should not be compared across --scale.
    """
    X = days.reshape(-1, 1)
    y = scale.forward(seconds)
    model = LinearRegression().fit(X, y)
    slope_year = float(model.coef_[0]) * 365.25
    return model, {
        "n": len(y),
        "slope_year": slope_year,
        "rate": scale.rate(slope_year),
        "r2": r2_score(y, model.predict(X)),
    }


def pooled_ci(days, seconds, athlete_ids, scale, alpha=0.05):
    """95% interval for the pooled slope, clustered by athlete, in scale units.

    Races by one runner are not independent draws -- a single athlete supplies
    twenty-odd correlated observations -- and plain OLS standard errors treat
    them as though they were, which halves the interval. The sandwich estimator
    below sums score contributions per athlete rather than per race.

    statsmodels would give this directly but is not installed here, and a dozen
    lines of numpy is not worth a new dependency for one number.
    """
    y = scale.forward(seconds)
    X = np.column_stack([np.ones_like(days), days])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta

    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    for a in np.unique(athlete_ids):
        m = athlete_ids == a
        score = X[m].T @ resid[m]
        meat += np.outer(score, score)

    se = np.sqrt(np.diag(bread @ meat @ bread))[1]
    z = 1.959963984540054                      # two-sided 95%, no scipy needed
    return (scale.rate((beta[1] - z * se) * 365.25),
            scale.rate((beta[1] + z * se) * 365.25))


def athlete_fits(d, origin, scale, min_marks=MIN_MARKS):
    """Per-athlete fits: one line's endpoints and rate for each athlete.

    Endpoints span only that athlete's own first-to-last mark. Extending them
    across the whole axis would draw a 2019 prediction for a runner whose first
    race was in 2023. Predictions come back through scale.inverse, so the lines
    are in real seconds whichever space they were fitted in.
    """
    lines = []
    for _, g in d.groupby("athlete_id", sort=False):
        # Two marks on one day give a vertical span and a meaningless slope.
        if len(g) < min_marks or g["dt"].nunique() < 2:
            continue
        days = to_days(g["dt"], origin)
        sec = g["seconds"].to_numpy(dtype=float)
        model, stats = fit(days, sec, scale)
        span = np.array([[days.min()], [days.max()]])

        # Residuals against the athlete's own line, which is what "how close does
        # a runner stay to their trend" means. Kept per athlete so the panel can
        # report a median rather than one number pooled over unequal careers.
        resid = scale.forward(sec) - model.predict(days.reshape(-1, 1))
        lines.append({
            "x": [g["dt"].min(), g["dt"].max()],
            "y": scale.inverse(model.predict(span)),
            "rate": stats["rate"],
            "r2": stats["r2"],
            "resid": resid,
            "career": ((days - days.min()) / (days.max() - days.min())),
            "median_sec": float(np.median(sec)),
        })
    return lines


def summarise(d, lines, stats, ci, scale):
    """Everything a panel reports, gathered in the units it will be printed in.

    'scatter' is the spread of a race around the athlete's *own* line, not around
    the pooled one -- it answers "how repeatable is this runner", which is the
    question R2 gets asked and cannot answer.
    """
    rates = np.array([ln["rate"] for ln in lines]) if lines else np.array([np.nan])
    r2s = np.array([ln["r2"] for ln in lines]) if lines else np.array([np.nan])
    resid = np.concatenate([ln["resid"] for ln in lines]) if lines else np.array([np.nan])
    median_sec = float(d["seconds"].median())

    # In percent mode residuals are in log units, where a small value is already
    # a fraction; in seconds mode they are seconds and need no conversion.
    sd = float(np.std(resid))
    scatter_sec = sd * median_sec if scale.unit == "%/yr" else sd

    return {
        "median_rate": float(np.median(rates)),
        "iqr": (float(np.percentile(rates, 25)), float(np.percentile(rates, 75))),
        "improving": int((rates < 0).sum()),
        "ci": ci,
        "r2_pooled": stats["r2"],
        "r2_athlete": float(np.median(r2s)),
        "scatter": sd * 100 if scale.unit == "%/yr" else sd,
        "scatter_sec": scatter_sec,
        "median_sec": median_sec,
        "n_fits": len(lines),
    }


# ---------------------------------------------------------------------------
# 3. Draw one panel
# ---------------------------------------------------------------------------
def plot_one(ax, d, lines, model, stats, s, label, scale):
    indoor = d["season_type"] == "Indoor"
    ax.scatter(d.loc[~indoor, "dt"], d.loc[~indoor, "seconds"],
               s=5, alpha=0.25, color=SCATTER, edgecolors="none", zorder=1)
    if indoor.any():
        # Marked apart because a banked or undersized indoor track shifts marks
        # systematically -- these are not interchangeable with outdoor races.
        ax.scatter(d.loc[indoor, "dt"], d.loc[indoor, "seconds"],
                   s=22, alpha=0.9, color=INDOOR, edgecolors="white",
                   linewidth=0.5, marker="D", zorder=3,
                   label=f"indoor (n = {int(indoor.sum())})")

    for i, line in enumerate(lines):
        ax.plot(line["x"], line["y"], color=SCATTER, alpha=0.28, linewidth=0.8,
                zorder=2, label="per-athlete fit" if i == 0 else None)

    # Sampled rather than drawn end to end: coming back through scale.inverse
    # makes the log fit slightly convex in seconds, and one code path beats
    # branching on which scale is active.
    start, end = d["dt"].min(), d["dt"].max()
    grid = np.linspace(0.0, float((end - start).days), 100)
    ax.plot(start + pd.to_timedelta(grid, unit="D"),
            scale.inverse(model.predict(grid.reshape(-1, 1))),
            color=POOLED, linewidth=2.6, zorder=4, label="pooled fit")

    top = float(np.percentile(d["seconds"], YLIM_PCT))
    bottom = float(d["seconds"].min())
    pad = 0.03 * (top - bottom)
    ax.set_ylim(bottom - pad, top + pad)
    clipped = int((d["seconds"] > top + pad).sum())

    ax.set_title(f"{label}   (n = {stats['n']:,}, {d['athlete_id'].nunique()} athletes)",
                 fontsize=11)
    ax.set_xlabel("date run")
    ax.set_ylabel("time")
    ax.yaxis.set_major_formatter(seconds_formatter)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    ax.grid(alpha=0.15, linewidth=0.6)

    # Scatter leads in seconds: "+/-11.5 s on a 1600m" is a number a coach can
    # act on, where "R2 = 0.36" is not. The two R2s sit last, together, so the
    # gap between them reads as the dilution it is.
    ax.annotate(f"per athlete: {s['median_rate']:+.2f} {scale.unit}"
                f"   IQR [{s['iqr'][0]:+.2f}, {s['iqr'][1]:+.2f}]\n"
                f"pooled: {stats['rate']:+.2f} {scale.unit}"
                f"   95% CI [{s['ci'][0]:+.2f}, {s['ci'][1]:+.2f}]\n"
                f"single race: +/-{s['scatter_sec']:.1f} s"
                + (f"  (+/-{s['scatter']:.1f}%)\n" if scale.unit == "%/yr" else "\n")
                +
                f"R2 {s['r2_pooled']:.2f} pooled / {s['r2_athlete']:.2f} per athlete"
                f"    {s['n_fits']} fits"
                + (f", {clipped} off axis" if clipped else ""),
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=8, va="bottom",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, linewidth=0))
    ax.legend(loc="upper right", fontsize=8, framealpha=0.85)


# ---------------------------------------------------------------------------
# 4. Diagnostics figure
# ---------------------------------------------------------------------------
def plot_diagnostics(panels, scale, title=""):
    """Three rows of fit quality, one column per event.

    The main figure can only carry summary numbers. These are the distributions
    behind them, and the third row is the one that earns the flag: it shows the
    straight line failing in a specific, repeatable way.
    """
    fig, axes = plt.subplots(3, len(panels), figsize=(17, 12))

    for col, (label, d, lines, s) in enumerate(panels):
        r2s = np.array([ln["r2"] for ln in lines])
        rates = np.array([ln["rate"] for ln in lines])

        ax = axes[0, col]
        ax.hist(r2s, bins=20, color=SCATTER, edgecolor="white", linewidth=0.6)
        ax.axvline(np.median(r2s), color=POOLED, linewidth=2,
                   label=f"median {np.median(r2s):.2f}")
        ax.axvline(s["r2_pooled"], color="#555", linewidth=2, linestyle="--",
                   label=f"pooled {s['r2_pooled']:.2f}")
        ax.set_title(f"{label}: how well a line fits one athlete", fontsize=10)
        ax.set_xlabel("R2 of that athlete's own fit")
        ax.set_ylabel("athletes")
        ax.legend(fontsize=8)

        ax = axes[1, col]
        ax.hist(rates, bins=20, color=SCATTER, edgecolor="white", linewidth=0.6)
        ax.axvline(np.median(rates), color=POOLED, linewidth=2,
                   label=f"median {np.median(rates):+.2f}")
        ax.axvline(0, color="#555", linewidth=1.5, linestyle=":",
                   label=f"{len(rates) - s['improving']} not improving")
        ax.set_title(f"{label}: spread of improvement", fontsize=10)
        ax.set_xlabel(f"rate ({scale.unit})")
        ax.set_ylabel("athletes")
        ax.legend(fontsize=8)

        # Residuals against position through each athlete's own career. A correct
        # straight line leaves no pattern here; a U-shape means trajectories are
        # convex, i.e. improvement decelerates.
        ax = axes[2, col]
        career = np.concatenate([ln["career"] for ln in lines])
        resid = np.concatenate([ln["resid"] for ln in lines])
        shown = resid * 100 if scale.unit == "%/yr" else resid
        ax.scatter(career, shown, s=3, alpha=0.12, color=SCATTER, edgecolors="none")

        edges = np.linspace(0, 1, 9)
        mids = (edges[:-1] + edges[1:]) / 2
        binned = [shown[(career >= a) & (career < b)].mean() for a, b in zip(edges[:-1], edges[1:])]
        ax.plot(mids, binned, color=POOLED, linewidth=2.4, marker="o",
                markersize=4, label="binned mean")
        ax.axhline(0, color="#555", linewidth=1.2, linestyle=":")
        ax.set_ylim(np.percentile(shown, 1), np.percentile(shown, 99))
        ax.set_title(f"{label}: is a straight line the right shape?", fontsize=10)
        ax.set_xlabel("position through that athlete's career")
        ax.set_ylabel("residual (%)" if scale.unit == "%/yr" else "residual (s)")
        ax.legend(fontsize=8)

    for ax in axes.flatten():
        ax.grid(alpha=0.15, linewidth=0.6)
    fig.suptitle(f"Fit diagnostics - {title}: how well a straight line describes a career",
                 fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return fig


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Career progression of the top 100, per event, with per-athlete fits.")
    p.add_argument("--csv", default=DEFAULT_CSV, type=Path,
                   help=f"scraped performance panel (default: {DEFAULT_CSV})")
    p.add_argument("--min-marks", default=MIN_MARKS, type=int,
                   help=f"marks needed before an athlete gets a line (default: {MIN_MARKS})")
    p.add_argument("--scale", default=DEFAULT_SCALE, choices=sorted(SCALES),
                   help="'percent' fits log(time) and reports %%/yr, which compares "
                        "across events; 'seconds' fits time and reports s/yr "
                        f"(default: {DEFAULT_SCALE})")
    p.add_argument("--events", default=DEFAULT_EVENT_SET, choices=sorted(EVENT_SETS),
                   help="which three panels to draw, matching the roster's discipline "
                        f"(default: {DEFAULT_EVENT_SET})")
    p.add_argument("--title", help="figure title (default: derived from the CSV name)")
    p.add_argument("--indoor", action="store_true",
                   help="include indoor marks (default: outdoor and cross country only)")
    p.add_argument("--diagnostics", action="store_true",
                   help="also draw the fit-quality figure (per-athlete R2 and rate "
                        "distributions, and a residual check on the straight line)")
    p.add_argument("--out", default=EXPLORE_OUT / "individual_progression.png", type=Path)
    p.add_argument("--save", action="store_true",
                   help="write the figure to --out instead of only showing it")
    args = p.parse_args()

    scale = SCALES[args.scale]
    events = EVENT_SETS[args.events]
    title = args.title or args.csv.stem
    df = load(args.csv)

    # CHANGE PLOT DIMENSIONS HERE ##################################################
    fig, axes = plt.subplots(1, 3, figsize=(17, 6))

    unit = scale.unit
    header = (f"{'panel':>9}  {'n':>6}  {'bad':>3}  {'merged':>6}  {'ath':>4}  "
              f"{'fits':>5}  {'median ' + unit:>11}  {'pooled ' + unit:>11}  "
              f"{'95% CI':>16}  {'R2 pool':>7}  {'R2 ath':>6}  {'scatter':>8}  "
              f"{'median':>7}")
    print(f"grades {GRADES[0]}-{GRADES[1]}, >={args.min_marks} marks for a line, "
          f"--scale {args.scale}, indoor {'on' if args.indoor else 'off'}\n")
    print(header)
    print("-" * len(header))

    panels = []
    for ax, (label, event, seasons) in zip(axes.flatten(), events):
        if args.indoor and "Outdoor" in seasons:
            seasons = seasons | {"Indoor"}
        d, drops = select(df, event, seasons)
        if d.empty:
            raise SystemExit(f"no rows for {event} {sorted(seasons)}")

        origin = d["dt"].min()
        days = to_days(d["dt"], origin)
        sec = d["seconds"].to_numpy(dtype=float)
        model, stats = fit(days, sec, scale)
        ci = pooled_ci(days, sec, d["athlete_id"].to_numpy(), scale)
        lines = athlete_fits(d, origin, scale, args.min_marks)
        s = summarise(d, lines, stats, ci, scale)
        plot_one(ax, d, lines, model, stats, s, label, scale)
        panels.append((label, d, lines, s))

        ci_txt = f"[{ci[0]:+.2f}, {ci[1]:+.2f}]"
        scatter_txt = f"+/-{s['scatter_sec']:.1f}s"
        print(f"{label:>9}  {stats['n']:>6,}  {drops['bounds']:>3}  {drops['career']:>6}  "
              f"{d['athlete_id'].nunique():>4}  {len(lines):>5}  "
              f"{s['median_rate']:>11.2f}  {stats['rate']:>11.2f}  "
              f"{ci_txt:>16}  {s['r2_pooled']:>7.3f}  {s['r2_athlete']:>6.3f}  "
              f"{scatter_txt:>8}  {seconds_formatter(s['median_sec'], None):>7}")

    print("\nnegative = getting faster. 'median' is the middle per-athlete rate;")
    print("'pooled' ignores athlete identity and so also absorbs the roster's")
    print("grade mix, which is why both are reported.")
    print("\nThe CI and the scatter answer different questions. The CI is how well")
    print("the trend is known -- it is narrow, so the improvement rate is real.")
    print("The scatter is how well one race can be predicted -- it is wide, because")
    print("weather, tactics and depth of field are not in the model. R2 measures the")
    print("second, which is why it reads modest while the CI stays tight. 'R2 ath' is")
    print("the median over per-athlete fits; 'R2 pool' is diluted by athlete identity.")
    if args.scale == "percent":
        print("Rates are proportional, so the panels compare directly; multiply by")
        print("the median time to read one back in seconds per year.")

    fig.suptitle(f"High school career progression - {title}  ({args.scale})", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    if args.save:
        # savefig will not create the directory, and --out routinely points at a
        # subfolder of output/ (e.g. output/individual/) that does not exist yet.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.out, dpi=300)
        print(f"\nsaved -> {args.out}")

    if args.diagnostics:
        diag = plot_diagnostics(panels, scale, title)
        if args.save:
            # Same stem as the main figure, so the pair stays together on disk.
            path = args.out.with_name(f"{args.out.stem}_diagnostics{args.out.suffix}")
            diag.savefig(path, dpi=300)
            print(f"saved -> {path}")

    plt.show()


if __name__ == "__main__":
    main()
