"""
gpd_tail.py
===========
Extreme-value analysis of ONE track event, using the Pickands-Balkema-de Haan
theorem.

The idea in three lines:
  1. Keep only performances faster than a high threshold u.
  2. Fit a Generalized Pareto Distribution (GPD) to the amounts they beat u by.
  3. Convert any query time into an unconditional probability + return period.

Input : one CSV with columns  name, time, team, grade, state, date
Output: a printed report and a 2x2 diagnostic figure.

Usage : edit the CONFIG block below, then  `python gpd_tail.py`
        or override the file from the shell:
        `python stages/03_tail_fit/gpd_tail.py stages/01_scrape/output/legacy/NY/m/800.csv`
        The figure is written to stages/03_tail_fit/output/.

SIGN CONVENTION
---------------
EVT is written for UPPER tails (big = extreme). In running, SMALL = extreme.
So the script works internally on  x = -seconds.  Every fast time becomes a
large x, the fast tail becomes an upper tail, and all the textbook formulas
apply unchanged. Anything shown to you is converted back to seconds.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # file output only; drop this line for a GUI window
import matplotlib.pyplot as plt
from scipy.stats import genpareto

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import LEGACY, TAILFIT_OUT


# ======================================================================
# CONFIG  -- everything you'd normally want to change lives here
# ======================================================================

EVENT_FILE  = LEGACY / "NY" / "m" / "100r.csv"   # which event to run inference on
EVENT_LABEL = "100m"           # cosmetic, used in plot titles

# Times you want scored. Seconds, or "M:SS.ss" strings for distance events.
# QUERY_TIMES = [10.31, 10.50, 10.75]
QUERY_TIMES = ["10.95", "11.2"]

# How to place the threshold u.
#   "quantile" -> THRESHOLD_VALUE is a fraction, e.g. 0.98 = fastest 2%
#   "count"    -> THRESHOLD_VALUE is a number of exceedances, e.g. 150
#   "absolute" -> THRESHOLD_VALUE is a time in seconds, e.g. 11.00
THRESHOLD_MODE  = "absolute"
THRESHOLD_VALUE = 11.583

# Collapse each athlete to their single best mark. The GPD derivation assumes
# independent observations; one sprinter with 20 races in the file is 20
# correlated rows that inflate how common elite times look.
DEDUPE_ATHLETES = True

# If the CSV is a truncated top-N ranking li o contested the event. Leave None
# to use the row count. See the notes at the bottom of this file -- this single
# setting is the difference between a meaningful probability and a meaningless
# one.
POPULATION_SIZE = None

N_BOOTSTRAP = 800               # 0 disables confidence intervals
RANDOM_SEED = 0
MAKE_PLOTS  = True
FIGURE_PATH = TAILFIT_OUT / f"gpd_diagnostics{EVENT_LABEL}.png"   # this stage's output/


# ======================================================================
# 1. READING AND CLEANING
# ======================================================================

# Matches "10.31", "1:52.34", "4:15", "10.31a", "  9.98h  ".
# Group 1 = optional minutes before a colon, group 2 = seconds.
# The trailing [a-zA-Z]* soaks up timing-method suffixes (a = auto, h = hand).
_TIME_RE = re.compile(r"^\s*(?:(\d+):)?(\d+(?:\.\d+)?)\s*[a-zA-Z]*\s*$")


def parse_time(raw) -> float:
    """Turn a messy time cell into a float number of seconds, or NaN."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if np.isfinite(raw) else np.nan

    # Deliberately NOT stripping commas: "2:05,4" would silently become 174.0
    # instead of 125.4. A NaN you can see beats a wrong number you can't.
    s = str(raw).strip()
    if not s:
        return np.nan

    m = _TIME_RE.match(s)
    if m is None:
        return np.nan

    minutes, seconds = m.groups()
    total = float(seconds)
    if minutes is not None:
        total += 60.0 * int(minutes)
    return total


def load_event(path: str, dedupe: bool = True) -> tuple[pd.DataFrame, dict]:
    """Load one event CSV and return a frame with a clean `seconds` column."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "time" not in df.columns:
        raise ValueError(f"{path} has no 'time' column. Found: {list(df.columns)}")

    n_raw = len(df)
    df["seconds"] = df["time"].map(parse_time)

    df = df.dropna(subset=["seconds"])
    df = df[df["seconds"] > 0]
    n_parsed = len(df)

    n_deduped = n_parsed
    if dedupe and "name" in df.columns:
        # Key on name plus whatever else identifies a person, so two different
        # athletes who happen to share a name aren't merged into one.
        keys = ["name"] + [c for c in ("team", "state") if c in df.columns]
        df = df.sort_values("seconds").drop_duplicates(subset=keys, keep="first")
        n_deduped = len(df)

    stats = {"n_raw": n_raw, "n_parsed": n_parsed, "n_final": n_deduped}
    return df.reset_index(drop=True), stats


# ======================================================================
# 2. THRESHOLD AND FIT
# ======================================================================

def choose_threshold(x: np.ndarray, mode: str, value: float) -> float:
    """Return the threshold u, expressed in x-space (x = -seconds)."""
    if mode == "quantile":
        return float(np.quantile(x, value))
    if mode == "count":
        k = int(value)
        if k >= len(x):
            raise ValueError(f"Asked for {k} exceedances but only {len(x)} points exist.")
        # The (k+1)-th largest value, so that exactly k points sit strictly above u.
        return float(np.partition(x, -(k + 1))[-(k + 1)])
    if mode == "absolute":
        return float(-value)      # user supplies a TIME; flip it into x-space
    raise ValueError(f"Unknown THRESHOLD_MODE: {mode!r}")


@dataclass
class GPDFit:
    u: float          # threshold, x-space
    xi: float         # shape parameter
    sigma: float      # scale parameter
    n_exceed: int     # N_u
    n_total: int      # n (or POPULATION_SIZE)
    zeta: float       # N_u / n, the base rate of clearing the threshold

    @property
    def u_seconds(self) -> float:
        return -self.u

    @property
    def endpoint_seconds(self) -> float | None:
        """
        For xi < 0 the GPD has a hard right endpoint at u - sigma/xi. Converted
        back to seconds this is the fastest time the fitted tail considers
        possible. Returns None when xi >= 0 (no finite limit).
        """
        if self.xi >= 0:
            return None
        return -(self.u - self.sigma / self.xi)


def fit_gpd(x: np.ndarray, u: float, n_total: int | None = None) -> GPDFit:
    """
    Maximum-likelihood fit of a GPD to the excesses above u.

    `floc=0` pins the location parameter at zero. This is essential: the excesses
    y = x - u are measured from the threshold, so zero is where they start by
    construction. Letting scipy also fit a location would double-count the
    threshold and give nonsense.
    """
    excesses = x[x > u] - u
    n_exceed = len(excesses)
    if n_exceed < 10:
        raise ValueError(f"Only {n_exceed} exceedances above u. Lower the threshold.")

    n = int(n_total) if n_total else len(x)
    xi, _loc, sigma = genpareto.fit(excesses, floc=0)
    return GPDFit(u=u, xi=float(xi), sigma=float(sigma),
                  n_exceed=n_exceed, n_total=n, zeta=n_exceed / n)


# ======================================================================
# 3. TURNING THE FIT INTO A PROBABILITY
# ======================================================================

def exceedance_probability(t_query: float, fit: GPDFit) -> dict:
    """
    Unconditional probability that a random athlete runs t_query or faster:

        P(X > u + y) = (N_u / n) * [1 + xi*y/sigma] ^ (-1/xi)
                        ^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        base rate   GPD conditional survival, sf() in scipy

    The base rate is counted, not modelled -- there's plenty of data right at
    the threshold. The GPD does the extrapolation past it.
    """
    x_q = -t_query
    y = x_q - fit.u

    if y < 0:
        # Slower than the threshold. The GPD makes no claim down here, so fall
        # back to the raw empirical proportion and flag it.
        return {"time": t_query, "prob": np.nan, "return_period": np.nan,
                "status": "below threshold"}

    endpoint = fit.endpoint_seconds
    if endpoint is not None and t_query < endpoint:
        # Faster than the fitted hard limit -> model probability is exactly 0.
        return {"time": t_query, "prob": 0.0, "return_period": np.inf,
                "status": f"beyond fitted limit of {endpoint:.3f}s"}

    p = float(fit.zeta * genpareto.sf(y, fit.xi, loc=0, scale=fit.sigma))
    return {"time": t_query, "prob": p,
            "return_period": (1.0 / p if p > 0 else np.inf),
            "status": "ok"}


def bootstrap(x, query_times, mode, value, n_boot, rng, n_total=None,
              groups=None) -> dict:
    """
    Resample the whole dataset with replacement, redo threshold selection AND
    refit each time, and collect the spread of results.

    Re-selecting the threshold inside the loop (rather than holding u fixed) is
    deliberate: threshold choice is itself estimated from the data, so freezing
    it would report an interval that is too narrow.

    `groups` (optional, one label per element of x) switches to a CLUSTER
    bootstrap: draw whole groups with replacement and keep every row of each.
    Use it when rows are not independent -- stage 04 stacks two seasons, and
    one athlete's 2025 and 2026 marks are two rows of one person. Resampling
    rows would treat them as two independent draws and understate the
    spread; resampling athletes carries the dependence into every resample.
    Resample sizes then vary a little around n, which is part of the
    honest uncertainty. With groups=None the draws are exactly the old ones.
    """
    n = len(x)
    draws = {"xi": [], "sigma": [], "u_sec": []}
    probs = {t: [] for t in query_times}

    if groups is not None:
        # Row indices grouped by cluster, built once: `members[k]` holds the
        # rows of the k-th group.
        _, inv = np.unique(np.asarray(groups), return_inverse=True)
        order = np.argsort(inv, kind="stable")
        members = np.split(order, np.flatnonzero(np.diff(inv[order])) + 1)
        x = np.asarray(x)

    for _ in range(n_boot):
        if groups is None:
            xb = rng.choice(x, size=n, replace=True)
        else:
            picks = rng.integers(0, len(members), size=len(members))
            xb = x[np.concatenate([members[k] for k in picks])]
        try:
            ub = choose_threshold(xb, mode, value)
            fb = fit_gpd(xb, ub, n_total)
        except Exception:
            continue

        draws["xi"].append(fb.xi)
        draws["sigma"].append(fb.sigma)
        draws["u_sec"].append(fb.u_seconds)
        for t in query_times:
            probs[t].append(exceedance_probability(t, fb)["prob"])

    def ci(vals):
        v = np.asarray([a for a in vals if np.isfinite(a)], dtype=float)
        if v.size < 20:
            return (np.nan, np.nan)
        return tuple(np.percentile(v, [2.5, 97.5]))

    return {"n_ok": len(draws["xi"]),
            "xi_ci": ci(draws["xi"]),
            "sigma_ci": ci(draws["sigma"]),
            "u_ci": ci(draws["u_sec"]),
            "prob_ci": {t: ci(v) for t, v in probs.items()},
            "raw": draws}


def endpoint_interval(raw: dict, level: float = 0.95) -> tuple:
    """
    Percentile interval for the implied wall, in seconds, from bootstrap draws.

    The wall is u + sigma/xi (seconds; xi < 0 makes the second term negative).
    Two kinds of draw have NO finite wall:
      * xi >= 0 -- the resampled tail is unbounded;
      * xi slightly below 0 -- sigma/|xi| is so large the "wall" lands at or
        below 0 s, which is the same statement in physical units.
    Both are evidence that the data cannot rule out "no wall". The old code
    dropped the first kind and kept the second as numbers (an 800 m wall CI of
    -19.5 s). Dropping them conditions on the answer -- it keeps only the
    resamples that agree there is a wall -- so here both count as -inf
    ("arbitrarily fast is allowed") and the percentiles are taken on the
    extended line.

    Returns (lo, hi, frac_unbounded). lo is -inf when at least (1-level)/2 of
    the draws are unbounded: then the interval has no finite fast end, and the
    honest report is "unbounded". (nan, nan, nan) when fewer than 20 draws.
    """
    xi = np.asarray(raw["xi"], dtype=float)
    if xi.size < 20:
        return (np.nan, np.nan, np.nan)
    sg = np.asarray(raw["sigma"], dtype=float)
    us = np.asarray(raw["u_sec"], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        wall = np.where(xi < 0, us + sg / xi, -np.inf)
    wall = np.where(wall > 0, wall, -np.inf)
    alpha = (1 - level) / 2
    # method="lower"/"higher" keep -inf from being interpolated into nan.
    lo = float(np.quantile(wall, alpha, method="lower"))
    hi = float(np.quantile(wall, 1 - alpha, method="higher"))
    return (lo, hi, float(np.isneginf(wall).mean()))


# ======================================================================
# 4. THRESHOLD DIAGNOSTICS
# ======================================================================

def threshold_sweep(x: np.ndarray, q_lo=0.80, q_hi=0.995, n_steps=40):
    """
    Fit the GPD at many candidate thresholds and record what happens.

    Two things get computed at each candidate u:

    Mean excess, e(u) = average of (x - u) over points above u.
        If the GPD holds from u upward, e(u) is a straight line in u. Curvature
        means the approximation has not kicked in yet.

    Shape estimate xi_hat, plus its standard error.
        The GPD is threshold-stable: if the fit is valid at u it stays valid at
        every higher threshold WITH THE SAME xi. So xi_hat should flatten out
        once you are high enough. SE uses the standard asymptotic result
        Var(xi_hat) = (1 + xi)^2 / N_u.
    """
    us = np.quantile(x, np.linspace(q_lo, q_hi, n_steps))
    rows = []
    for u in us:
        exc = x[x > u] - u
        nu = len(exc)
        if nu < 15:
            continue
        row = {"u": u, "u_sec": -u, "n": nu,
               "mean_excess": exc.mean(),
               "me_se": exc.std(ddof=1) / np.sqrt(nu)}
        try:
            xi, _, sig = genpareto.fit(exc, floc=0)
            row["xi"] = xi
            row["xi_se"] = abs(1.0 + xi) / np.sqrt(nu)
            row["sigma_star"] = sig - xi * u      # modified scale, also stable
        except Exception:
            row["xi"] = row["xi_se"] = row["sigma_star"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ======================================================================
# 5. PLOTS
# ======================================================================

def make_figure(x, fit, sweep, query_times, label, path):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
    fig.suptitle(f"GPD tail analysis - {label}", fontsize=14)

    # ---- (0,0) MEAN RESIDUAL LIFE ------------------------------------
    # Look for the leftmost point where the curve straightens out. That is the
    # lowest threshold where the GPD approximation is credible.
    ax = axes[0, 0]
    ax.plot(sweep["u_sec"], sweep["mean_excess"], color="#333", lw=1.4)
    ax.fill_between(sweep["u_sec"],
                    sweep["mean_excess"] - 1.96 * sweep["me_se"],
                    sweep["mean_excess"] + 1.96 * sweep["me_se"],
                    color="#888", alpha=0.25)
    ax.axvline(fit.u_seconds, color="#c0392b", ls="--", lw=1.2,
               label=f"chosen u = {fit.u_seconds:.2f}s")
    ax.invert_xaxis()          # faster (= more extreme) on the right
    ax.set_xlabel("Threshold time, s  (more extreme to the right)")
    ax.set_ylabel("Mean excess beyond threshold, s")
    ax.set_title("Mean residual life: look for the straight stretch")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    # ---- (0,1) SHAPE PARAMETER STABILITY -----------------------------
    ax = axes[0, 1]
    ax.plot(sweep["u_sec"], sweep["xi"], color="#1f4e79", lw=1.4)
    ax.fill_between(sweep["u_sec"],
                    sweep["xi"] - 1.96 * sweep["xi_se"],
                    sweep["xi"] + 1.96 * sweep["xi_se"],
                    color="#1f4e79", alpha=0.18)
    ax.axhline(0, color="#666", lw=0.8, ls=":")
    ax.axvline(fit.u_seconds, color="#c0392b", ls="--", lw=1.2)
    ax.invert_xaxis()
    ax.set_xlabel("Threshold time, s  (more extreme to the right)")
    ax.set_ylabel(r"$\hat{\xi}$")
    ax.set_title(r"Shape stability: pick the lowest u where $\hat{\xi}$ goes flat")
    ax.grid(alpha=0.25)

    # ---- (1,0) QQ PLOT -----------------------------------------------
    # Does the fitted GPD actually describe the excesses? Points on the
    # diagonal = yes. Systematic bending at the top right = the model is
    # mis-describing the most extreme performances, which are the ones you care
    # about most.
    ax = axes[1, 0]
    exc = np.sort(x[x > fit.u] - fit.u)
    nu = len(exc)
    plot_pos = (np.arange(1, nu + 1) - 0.5) / nu
    theo = genpareto.ppf(plot_pos, fit.xi, loc=0, scale=fit.sigma)
    ax.plot(theo, exc, "o", ms=3.5, alpha=0.6, color="#1f4e79")
    lim = [0, max(theo[np.isfinite(theo)].max(), exc.max()) * 1.03]
    ax.plot(lim, lim, "-", color="#c0392b", lw=1.2)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("GPD model quantile, s")
    ax.set_ylabel("Observed excess, s")
    ax.set_title("QQ plot: points should sit on the red line")
    ax.grid(alpha=0.25)

    # ---- (1,1) TAIL FIT ON A LOG SCALE -------------------------------
    # Log y is what makes this readable: probabilities span many orders of
    # magnitude out in the tail, and on a linear axis everything interesting
    # would be flattened against zero.
    ax = axes[1, 1]
    exc_x = np.sort(x[x > fit.u])                    # ascending in x
    ranks = np.arange(len(exc_x), 0, -1)             # how many are >= this one
    emp_p = ranks / fit.n_total                      # empirical survival
    ax.semilogy(-exc_x, emp_p, "o", ms=3.5, alpha=0.55,
                color="#444", label="observed")

    # Model curve. For xi < 0 the GPD dies at a finite endpoint; stop just
    # short of it, otherwise sf() returns 0 and the log axis blows up.
    span = exc_x.max() - fit.u
    top = fit.u + 2.2 * span
    if fit.xi < 0:
        top = min(top, fit.u - fit.sigma / fit.xi - 1e-9)
    grid = np.linspace(fit.u, top, 400)
    ax.semilogy(-grid, fit.zeta * genpareto.sf(grid - fit.u, fit.xi, 0, fit.sigma),
                "-", color="#c0392b", lw=1.6, label="fitted GPD")

    for t in query_times:
        ax.axvline(t, color="#2e8b57", ls=":", lw=1.1)
        ax.annotate(f"{t:g}", (t, ax.get_ylim()[0]), rotation=90,
                    fontsize=8, color="#2e8b57",
                    va="bottom", ha="right", xytext=(-2, 4),
                    textcoords="offset points")

    # When xi < 0 the fitted curve dives to ~0 at the endpoint, which would
    # stretch a log axis down to 1e-14 and squash everything readable into the
    # top centimetre. Floor the axis two decades below the rarest real point.
    ax.set_ylim(bottom=emp_p.min() / 100, top=fit.zeta * 2)

    ax.invert_xaxis()
    ax.set_xlabel("Time, s  (faster to the right)")
    ax.set_ylabel("P(run this time or faster)")
    ax.set_title("Tail fit and extrapolation")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, which="both")

    fig.tight_layout(rect=(0, 0, 1, 0.965))
    Path(path).parent.mkdir(parents=True, exist_ok=True)   # savefig won't create it
    fig.savefig(path, dpi=140)
    print(f"\nFigure written to {path}")


# ======================================================================
# 6. MAIN
# ======================================================================

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else EVENT_FILE
    rng = np.random.default_rng(RANDOM_SEED)

    df, load_stats = load_event(path, dedupe=DEDUPE_ATHLETES)
    seconds = df["seconds"].to_numpy(dtype=float)
    x = -seconds                                    # into upper-tail space

    queries = [parse_time(t) for t in QUERY_TIMES]

    u = choose_threshold(x, THRESHOLD_MODE, THRESHOLD_VALUE)
    fit = fit_gpd(x, u, POPULATION_SIZE)

    print("=" * 66)
    print(f"  {EVENT_LABEL}   ({path})")
    print("=" * 66)
    print(f"  rows read              {load_stats['n_raw']:,}")
    print(f"  parsed to seconds      {load_stats['n_parsed']:,}")
    print(f"  after athlete dedupe   {load_stats['n_final']:,}")
    print(f"  population used (n)    {fit.n_total:,}"
          + ("  [POPULATION_SIZE override]" if POPULATION_SIZE else ""))
    print(f"  fastest observed       {seconds.min():.3f} s")
    print(f"  median                 {np.median(seconds):.3f} s")

    print("\n  --- GPD fit ---")
    print(f"  threshold u            {fit.u_seconds:.3f} s")
    print(f"  exceedances N_u        {fit.n_exceed:,}")
    print(f"  base rate N_u/n        {fit.zeta:.5f}")
    print(f"  shape  xi              {fit.xi:+.4f}")
    print(f"  scale  sigma           {fit.sigma:.4f}")
    if fit.endpoint_seconds is not None:
        print(f"  implied hard limit     {fit.endpoint_seconds:.3f} s   "
              f"(xi < 0; treat as very uncertain)")
    else:
        print("  implied hard limit     none (xi >= 0, unbounded tail)")

    if fit.xi < -0.5:
        # Smith (1985): for xi < -0.5 the MLE loses its usual large-sample
        # properties -- the standard errors and CIs below are not trustworthy,
        # and the fit is being driven hard by the single fastest observation.
        print("  !! xi < -0.5: maximum likelihood is non-regular here. Standard")
        print("     errors are unreliable and the endpoint estimate is being")
        print("     pinned by the fastest one or two marks. Try a lower threshold.")

    boot = None
    if N_BOOTSTRAP > 0:
        boot = bootstrap(x, queries, THRESHOLD_MODE, THRESHOLD_VALUE,
                         N_BOOTSTRAP, rng, POPULATION_SIZE)
        lo, hi = boot["xi_ci"]
        print(f"  xi 95% CI              [{lo:+.4f}, {hi:+.4f}]"
              f"   ({boot['n_ok']}/{N_BOOTSTRAP} resamples converged)")

    print("\n  --- query times ---")
    hdr = f"  {'time':>9}  {'P(<= t)':>12}  {'1 in':>14}  {'-log10 P':>9}"
    if boot:
        hdr += f"  {'95% CI on 1 in':>26}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for t in queries:
        r = exceedance_probability(t, fit)
        if r["status"] != "ok":
            print(f"  {t:9.3f}  {r['status']:>12}")
            continue
        line = (f"  {t:9.3f}  {r['prob']:12.3e}  {r['return_period']:14,.0f}"
                f"  {-np.log10(r['prob']):9.2f}")
        if boot:
            plo, phi = boot["prob_ci"][t]
            if np.isfinite(plo) and plo > 0 and np.isfinite(phi) and phi > 0:
                line += f"  {1/phi:11,.0f} - {1/plo:11,.0f}"
            else:
                line += f"  {'unstable':>26}"
        print(line)

    if MAKE_PLOTS:
        sweep = threshold_sweep(x)
        make_figure(x, fit, sweep, queries, EVENT_LABEL, FIGURE_PATH)


if __name__ == "__main__":
    main()
