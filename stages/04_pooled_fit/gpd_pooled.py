"""
gpd_pooled.py
=============
Fit a Generalized Pareto tail to ONE pooled event x sex, choosing the threshold
automatically and honestly.

This is `stages/03_tail_fit/gpd_tail.py` pointed at a pooled distribution instead of a
single CSV, with threshold selection wired in front of it. The statistics are
imported from there rather than reimplemented -- there should only ever be one
implementation of the fit in this repo.

WHAT THIS ADDS OVER CALLING gpd_tail DIRECTLY
---------------------------------------------
1. It builds the pool (nine states, distances converted) via pool_data.
2. It selects the threshold with both methods from threshold_select, and it
   detects the failure modes that make a selection meaningless (below).
3. It caches the selection, because the honest version is slow.

WHY NOT threshold_select.compare()
----------------------------------
Historical: `compare()` was missing the two guards below, so this stage built
its own. They were ported back to stage 03 on 2026-10-09. This stage still
keeps its own `select_threshold`, because it also needs three guards that
`compare()` lacks: power saturation, an oversized mixture "tail", and the shape
plateau. The two original guards:

  * Its agreement criterion is a hardcoded `spread < 0.15` seconds. That is a
    sensible tolerance for a 100 m grid and a meaningless one for a 1600 m grid
    spanning ninety seconds, where two thresholds a second apart are practically
    identical. The criterion below is 10% of the candidate grid span, so it
    scales with the event.

  * `select_forwardstop` flags the case where every threshold is rejected, but
    NOT the case where none is. When ForwardStop rejects nothing it returns
    candidate zero -- the bottom of the grid -- and reports `note = "ok"`. That
    is not a selection, it is a fallback, and it is exactly the failure that
    produced the false 1600 m corroboration in stages/03_tail_fit/references/threshold_select.md: both methods
    returned 291.450 s, the harness announced close agreement, and both had
    simply hit the same wall.

So: agreement is only ever reported when both methods actually converged. Two
methods failing at the same boundary is not evidence about anything.

Usage
-----
    python stages/04_pooled_fit/gpd_pooled.py --event mile --sex m      # 1600 m eq.
    python stages/04_pooled_fit/gpd_pooled.py --event mile --sex f      # 1500 m eq.
    python stages/04_pooled_fit/gpd_pooled.py --event 100m --sex m --quick
    python stages/04_pooled_fit/gpd_pooled.py --event 100m --sex m --states NY
    python stages/04_pooled_fit/gpd_pooled.py --event 100m --sex m --years 2025,2026

Output: stages/04_pooled_fit/output/<region>/<years>/figures/gpd/gpd_<event>_<sex>.png
        stages/04_pooled_fit/output/_cache/thresholds.json  (selection cache)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2, genpareto, spearmanr

# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import (DEFAULT_YEARS, EVENTS, NORTHEAST, SEXES, dataset_dirs,
                       fmt_time, load_pool, parse_time, parse_years)

# The EVT machinery lives in a directory whose name contains a space, so it
# cannot be imported as a package -- put it on the path and import by module
# name. Note that importing gpd_tail runs matplotlib.use("Agg") at module level;
# everything here writes files, so that is harmless, but it is why pool_data
# keeps clear of this import.
# The one deliberate cross-stage import: this stage reuses stage 03's GPD
# machinery rather than copying it, so a fix there is a fix here.
from paths import POOLED_CACHE, TAILFIT_DIR  # noqa: E402  (src/ on sys.path)
sys.path.insert(0, str(TAILFIT_DIR))

from gpd_tail import (bootstrap, endpoint_interval,        # noqa: E402
                      exceedance_probability, fit_gpd, make_figure,
                      threshold_sweep)
from threshold_select import (forwardstop, gof_pvalue,     # noqa: E402
                              select_mixture_mle)


# One cache for every dataset. Its key fingerprints the pooled data, so a
# 2025 pool and a 2026 pool can never be served each other's threshold.
CACHE_PATH = POOLED_CACHE

# Bump whenever the selection logic changes. Without this a cached answer from
# an older, wronger version of the code silently survives a rerun -- which it
# did once already, when the drift detector was replaced and every cached
# "plateau" verdict was still the one the broken detector produced.
# v3 (2026-10-08): the key also fingerprints the DATA -- see cache_key.
SELECTION_VERSION = 3

# A mixture "tail" holding more than this share of the sample is not a tail.
MAX_TAIL_FRACTION = 0.25


# ======================================================================
# METHOD A -- SEQUENTIAL GOODNESS OF FIT
# ======================================================================

def run_forwardstop(x, candidate_us, alpha=0.05, n_sim=199, min_exceed=25,
                    rng=None, verbose=True) -> dict:
    """
    threshold_select.select_forwardstop, but returning the p-values as well.

    The library function returns only its choice, and on pooled data the choice
    is not the interesting part -- the p-value SEQUENCE is, because it is what
    reveals that the test has run out of discriminating power (see the
    saturation check below). The two functions doing the real work,
    `gof_pvalue` and `forwardstop`, are imported and reused unchanged.
    """
    rng = rng or np.random.default_rng(0)
    us, pvals, counts = [], [], []
    for u in candidate_us:
        exc = x[x > u] - u
        if len(exc) < min_exceed:
            continue
        us.append(u)
        counts.append(len(exc))
        pvals.append(gof_pvalue(exc, n_sim, rng))

    if not us:
        raise ValueError("No candidate threshold had enough exceedances.")

    us, pvals, counts = np.array(us), np.array(pvals), np.array(counts)
    k_reject = forwardstop(pvals, alpha)

    if k_reject >= len(us):
        idx, note = len(us) - 1, "all thresholds rejected"
    else:
        idx, note = k_reject, "ok"

    # --- did the test simply run out of power? -------------------------
    # The parametric bootstrap cannot return a p-value below 1/(1+n_sim), so a
    # run of values pinned at that floor means the Anderson-Darling test is
    # detecting SOME departure from the GPD with certainty. At N_u in the
    # thousands that is nearly guaranteed for real data: no parametric model is
    # exactly right, and a large enough sample will always say so.
    #
    # stages/03_tail_fit/references/threshold_select.md records the opposite trap -- "small samples pass
    # almost any test". This is its twin at the other end, and pooling nine
    # states is what walks into it: n went from about 8,000 to 28,686, and every
    # low threshold went from arguable to certainly rejected.
    floor = 1.0 / (1.0 + n_sim)
    n_at_floor = int((pvals <= floor + 1e-12).sum())
    saturated = bool(n_at_floor >= 3 and counts[0] >= 1000
                     and k_reject >= len(us) - 1)

    if verbose:
        print(f"\n  ForwardStop (alpha={alpha}, {n_sim} sims per threshold)")
        print(f"  {'u':>9} {'N_u':>7} {'p-value':>9}")
        for j, (u, n, p) in enumerate(zip(us, counts, pvals)):
            mark = "  <-- selected" if j == idx else ""
            print(f"  {fmt_time(-u):>9} {n:>7,d} {p:>9.3f}{mark}")
        print(f"  rejected the first {k_reject} of {len(us)}; {note}")

    return {"u": float(us[idx]), "u_sec": float(-us[idx]),
            "n_exceed": int(counts[idx]), "pvalue": float(pvals[idx]),
            "k_reject": int(k_reject), "n_candidates": int(len(us)),
            "n_at_floor": n_at_floor, "saturated": saturated, "note": note,
            "pvalues": [float(p) for p in pvals],
            "u_secs": [float(-u) for u in us],
            "counts": [int(c) for c in counts]}


# ======================================================================
# METHOD C -- THE SHAPE PLATEAU
# ======================================================================

def shape_sweep(x, candidate_us, min_exceed=30) -> list[dict]:
    """Refit the GPD shape at every candidate threshold, with its standard error."""
    rows = []
    for u in candidate_us:
        exc = x[x > u] - u
        nu = len(exc)
        if nu < min_exceed:
            continue
        try:
            xi, _loc, sigma = genpareto.fit(exc, floc=0)
        except Exception:
            continue
        rows.append({"u": float(u), "u_sec": float(-u), "n": int(nu),
                     "xi": float(xi), "sigma": float(sigma),
                     # Standard asymptotic result Var(xi) = (1 + xi)^2 / N_u.
                     "se": float(abs(1.0 + xi) / np.sqrt(nu))})
    return rows


def find_plateau(rows: list[dict], alpha=0.05, min_len=4) -> dict:
    """
    The lowest threshold from which the shape parameter is statistically flat.

    This is not a cosmetic feature of the stability plot -- it is the theorem's
    own signature. The GPD is threshold-stable: if the approximation holds at u
    then it holds at every higher threshold WITH THE SAME xi. So a plateau is
    what "the limit has been reached" looks like in data, and its absence means
    the limit has not been reached anywhere in the grid.

    For each candidate starting index i, ask whether xi is constant over
    candidates i..K. Weight them by inverse variance into a common value xi_bar
    and compute

        X2 = sum_{j >= i} (xi_j - xi_bar)^2 / se_j^2

    referred to a chi-square on (K - i) degrees of freedom. The lowest i that
    passes is where the plateau starts.

    TWO CAVEATS, both real.

    The xi_j are computed on NESTED samples -- the exceedances above a high
    threshold are a subset of those above a lower one -- so they are strongly
    correlated and the chi-square reference is approximate. This formalises
    reading the stability plot so the reading is reproducible; it does not make
    it rigorous.

    And the test gets EASIER to pass as the threshold rises, because se grows as
    N_u shrinks: at the top of any grid a few noisy estimates will look flat
    simply because nothing is measured precisely. That is why `sliding` below is
    reported alongside -- a monotone drift across the whole grid means there is
    no plateau at all, however flat the noisy top looks.
    """
    if len(rows) < min_len + 1:
        return {"found": False, "reason": "too few candidate thresholds"}

    xi = np.array([r["xi"] for r in rows])
    se = np.array([r["se"] for r in rows])
    K = len(rows)

    # --- is xi simply drifting? -----------------------------------------
    # An inverse-variance weighted least-squares trend of xi against log(N_u).
    #
    # Two earlier attempts at this were wrong, and both failures are worth
    # recording. Comparing only the two END estimates is useless, because the
    # highest threshold has by far the largest standard error and it swamps the
    # comparison -- on this data that measure ranked the sliding 1600 m as MORE
    # stable than the flat 100 m. And the constancy chi-square above cannot do
    # the job either: it is insensitive to ORDER, so a set of deviations that
    # all march the same way scores no worse than the same deviations shuffled.
    # Drift is precisely an ordering phenomenon, so it needs a trend test.
    #
    # log(N_u) rather than the threshold itself, because exceedance count is
    # what the estimate's precision depends on, and it spaces the candidates
    # evenly on the scale the sweep actually explores.
    w = 1.0 / se ** 2
    z = np.log([r["n"] for r in rows])
    zbar = float((w * z).sum() / w.sum())
    xibar = float((w * xi).sum() / w.sum())
    szz = float((w * (z - zbar) ** 2).sum())
    slope = float((w * (z - zbar) * (xi - xibar)).sum() / szz)
    t_slope = float(slope * np.sqrt(szz))
    drift = float(abs(slope) * (z.max() - z.min()))

    # Two bars, both deliberate. |t| > 4 rather than the conventional 2 because
    # these estimates come from nested samples and are positively correlated,
    # which inflates the apparent significance of any trend -- so the nominal t
    # is optimistic and the bar is raised to compensate. And a drift of 0.10 in
    # xi for practical significance: the endpoint depends on sigma/|xi|, so at
    # xi around -0.3 a swing of 0.10 moves the implied wall by roughly a third.
    sliding = bool(abs(t_slope) > 4.0 and drift > 0.10)

    out = {"rho": float(spearmanr(np.arange(K), xi).statistic),
           "slope": slope, "t_slope": t_slope, "drift": drift,
           "sliding": sliding, "xi_range": float(xi.max() - xi.min())}

    for i in range(K - min_len + 1):
        dof = K - i - 1
        if dof <= 0:
            break
        w = 1.0 / se[i:] ** 2
        bar = float((xi[i:] * w).sum() / w.sum())
        stat = float(((xi[i:] - bar) ** 2 * w).sum())
        if stat <= chi2.ppf(1 - alpha, dof):
            out.update({"found": True, "u_sec": rows[i]["u_sec"],
                        "u": rows[i]["u"], "n_exceed": rows[i]["n"],
                        "xi_bar": bar, "chi2": stat, "dof": dof,
                        "n_in_plateau": K - i,
                        # Starting at the very first candidate means xi is flat
                        # across the WHOLE grid, so we have not actually located
                        # where the plateau begins -- only that it begins at or
                        # below the grid's lower bound. Unlike the other two
                        # methods' edge cases this is not a failure: the
                        # bias-variance tradeoff wants the lowest valid
                        # threshold, and this is the lowest one on offer. It
                        # just means --q-lo could be lowered to check whether
                        # more data is available at the same xi.
                        "at_grid_floor": i == 0})
            return out

    out.update({"found": False,
                "reason": "xi is never statistically constant in this grid"})
    return out


# ======================================================================
# THRESHOLD SELECTION
# ======================================================================

def select_threshold(t: np.ndarray, q_lo=0.80, q_hi=0.995, n_cand=18,
                     alpha=0.05, n_sim=199, min_exceed=25, seed=0,
                     verbose=True) -> dict:
    """
    Run both selection methods on one candidate grid and judge the result.

    `t` is in SECONDS. Internally everything flips to x = -t so that the fast
    tail is an upper tail and every textbook formula applies unchanged
    (_config/evt_theory.md section 3.4).

    Returns a dict carrying each method's answer, whether each one converged,
    and which threshold to actually use.
    """
    rng = np.random.default_rng(seed)
    x = -t

    us = np.quantile(x, np.linspace(q_lo, q_hi, n_cand))
    u_secs = -us

    # Reproduce the eligibility filter select_forwardstop applies internally, so
    # that "did it land on the edge?" is asked about the grid it actually saw.
    eligible = np.array([u for u in us if int((x > u).sum()) >= min_exceed])
    if eligible.size < 3:
        raise ValueError("Fewer than three usable candidate thresholds; "
                         "widen the grid or lower min_exceed.")

    fs = run_forwardstop(x, us, alpha=alpha, n_sim=n_sim,
                         min_exceed=min_exceed, rng=rng, verbose=verbose)
    mx = select_mixture_mle(t, u_secs, min_exceed=min_exceed, verbose=verbose)
    rows = shape_sweep(x, us)
    pl = find_plateau(rows, alpha=alpha)

    # --- convergence, method A ----------------------------------------
    # Landing on either end of the grid means the sequence never turned: at the
    # bottom nothing was rejected, at the top everything was.
    at_lo = bool(np.isclose(fs["u"], eligible[0]))
    at_hi = bool(np.isclose(fs["u"], eligible[-1]))
    fs["at_edge"] = at_lo or at_hi
    if fs["saturated"]:
        fs["converged"] = False
        fs["why"] = (f"power-saturated: {fs['n_at_floor']} of "
                     f"{fs['n_candidates']} p-values sit on the bootstrap floor "
                     f"of {1/(1+n_sim):.3f}. At these sample sizes the test "
                     f"rejects every threshold, so its answer is about test "
                     f"power, not model adequacy")
    elif at_lo:
        fs["converged"] = False
        fs["why"] = ("rejected nothing -- fell back to the lowest candidate, "
                     "so this is a fallback and not a selection")
    elif at_hi:
        fs["converged"] = False
        fs["why"] = ("rejected everything -- fell back to the highest candidate")
    else:
        fs["converged"], fs["why"] = True, "ok"

    # --- convergence, method B ----------------------------------------
    # A "tail" containing a quarter of the sample is not a tail. When the
    # lognormal body fits badly the GPD half of the mixture expands to cover the
    # misfit, and the likelihood happily rewards it -- an interior optimum that
    # is nonetheless meaningless. stages/03_tail_fit/references/threshold_select.md flags this for the edge
    # case; it happens at interior optima too.
    tail_frac = mx["n_tail"] / len(t)
    mx["tail_fraction"] = float(tail_frac)
    if mx["at_edge"]:
        mx["converged"] = False
        mx["why"] = "likelihood never turned around inside the grid"
    elif tail_frac > MAX_TAIL_FRACTION:
        mx["converged"] = False
        mx["why"] = (f"the chosen 'tail' holds {tail_frac:.0%} of the sample, "
                     f"so the GPD is covering body misfit rather than a tail")
    else:
        mx["converged"], mx["why"] = True, "ok"

    # --- agreement, scale-relative ------------------------------------
    grid_span = float(abs(u_secs.max() - u_secs.min()))
    spread = float(abs(fs["u_sec"] - mx["u_sec"]))
    tol = 0.10 * grid_span
    both_ok = fs["converged"] and mx["converged"]

    # --- which threshold to use ---------------------------------------
    # Order of preference, and why. ForwardStop first when it genuinely
    # converged: it is the only method here that controls an error rate. The
    # plateau next, because threshold-stability is the theorem's own signature
    # and it degrades gracefully where the GoF test saturates. The mixture last,
    # since it is the one most easily fooled by a bad body model.
    plateau_ok = bool(pl.get("found") and not pl["sliding"])
    if fs["converged"]:
        chosen, source = fs["u_sec"], "ForwardStop"
    elif plateau_ok:
        chosen, source = pl["u_sec"], "shape plateau (ForwardStop unusable)"
    elif mx["converged"]:
        chosen, source = mx["u_sec"], "mixture MLE (other methods unusable)"
    elif pl.get("found"):
        chosen, source = pl["u_sec"], "shape plateau FALLBACK -- nothing converged"
    else:
        chosen, source = fs["u_sec"], "ForwardStop FALLBACK -- nothing converged"

    return {
        "forwardstop": {k: fs[k] for k in
                        ("u_sec", "n_exceed", "pvalue", "converged", "why",
                         "saturated", "k_reject", "n_candidates")},
        "mixture": {k: mx[k] for k in
                    ("u_sec", "n_tail", "loglik", "xi", "converged", "why",
                     "tail_fraction")},
        "plateau": pl,
        "shape_sweep": rows,
        "grid": {"q_lo": q_lo, "q_hi": q_hi, "n_cand": n_cand,
                 "span_s": grid_span,
                 "lo_s": float(u_secs.min()), "hi_s": float(u_secs.max())},
        "spread_s": spread, "tolerance_s": tol,
        # Agreement is only meaningful when there are two real answers to
        # compare. Coincident fallbacks are not corroboration.
        "agree": bool(both_ok and spread < tol),
        "both_converged": both_ok,
        "any_converged": bool(fs["converged"] or plateau_ok or mx["converged"]),
        "u_sec": float(chosen), "source": source,
    }


def _wrap(text: str, width: int) -> list[str]:
    """Minimal greedy wrap, so long explanations stay inside the report block."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def report_selection(sel: dict) -> None:
    """Print the verdict, including the reasons a method may have failed."""
    print("\n  " + "=" * 66)
    print("  THRESHOLD SELECTION")
    print("  " + "=" * 66)
    g = sel["grid"]
    print(f"  candidate grid          {fmt_time(g['lo_s'])} .. "
          f"{fmt_time(g['hi_s'])}  ({g['n_cand']} points, "
          f"span {g['span_s']:.2f} s)")
    for name, key in (("ForwardStop", "forwardstop"), ("Mixture MLE", "mixture")):
        m = sel[key]
        state = "converged" if m["converged"] else "DID NOT CONVERGE"
        print(f"  {name:<22}  u = {fmt_time(m['u_sec']):>9}   {state}")
        if not m["converged"]:
            for line in _wrap(m["why"], 62):
                print(f"  {'':<22}  {line}")

    pl = sel["plateau"]
    if pl.get("found"):
        state = "SLIDING, not a plateau" if pl["sliding"] else "converged"
        print(f"  {'Shape plateau':<22}  u = {fmt_time(pl['u_sec']):>9}   {state}")
        print(f"  {'':<22}  xi flat at {pl['xi_bar']:+.3f} over the top "
              f"{pl['n_in_plateau']} thresholds "
              f"(N_u >= {pl['n_exceed']:,})")
        if pl.get("at_grid_floor") and not pl["sliding"]:
            print(f"  {'':<22}  the plateau reaches the bottom of the grid, so "
                  f"where it BEGINS is")
            print(f"  {'':<22}  not established -- lower --q-lo to see whether "
                  f"more data sits at")
            print(f"  {'':<22}  the same xi. Not a failure: the lowest valid "
                  f"threshold is the one")
            print(f"  {'':<22}  you want, and this is the lowest on offer.")
    else:
        print(f"  {'Shape plateau':<22}  {'none':>13}   NOT FOUND")
        print(f"  {'':<22}  {pl.get('reason', '')}")
    if pl.get("sliding"):
        print(f"  {'':<22}  xi DRIFTS across the grid: weighted trend "
              f"{pl['slope']:+.4f} per log(N_u),")
        print(f"  {'':<22}  t = {pl['t_slope']:+.1f}, a change of {pl['drift']:.3f} "
              f"in xi end to end. The")
        print(f"  {'':<22}  Pickands limit is not reached anywhere in this grid, "
              f"so no choice")
        print(f"  {'':<22}  of threshold makes the GPD the right shape here.")

    print(f"  methods differ by       {sel['spread_s']:.3f} s "
          f"(tolerance {sel['tolerance_s']:.3f} s = 10% of the grid span)")
    if not sel["both_converged"]:
        print("  !! Agreement NOT assessed: at least one method failed rather")
        print("     than answered. Two methods landing on the same boundary")
        print("     would look like corroboration and would mean nothing.")
    elif sel["agree"]:
        print("  Close agreement -- treat this region as a solid choice.")
    else:
        print("  Wide disagreement. That gap IS your threshold uncertainty;")
        print("  fit at both and see how much the answer actually moves.")
    print(f"  --> using u = {fmt_time(sel['u_sec'])}   ({sel['source']})")
    if not sel["any_converged"]:
        print("  !! NO METHOD CONVERGED. The threshold below is a fallback and")
        print("     the fit that follows should be read as a description of")
        print("     this dataset, not as an estimate of a tail.")


# ======================================================================
# CACHE
# ======================================================================

def data_fingerprint(seconds: np.ndarray) -> str:
    """Short hash of the pooled sample itself.

    The key used to describe only the SETTINGS. When the 2026-10-07 rescrape
    swapped NY girls and VT onto their 1500 m lists, the 1600 m pools changed
    underneath an unchanged key, and a plain rerun would have served the old
    pools' thresholds as if they belonged to the new data. Hashing the sorted
    times (to the centisecond, the timing resolution) makes any change in what
    is being fitted a cache miss.
    """
    v = np.round(np.sort(np.asarray(seconds, dtype=float)), 2)
    return f"{v.size}-{hashlib.sha1(v.tobytes()).hexdigest()[:10]}"


def cache_key(event, sex, states, q_lo, q_hi, n_cand, alpha, n_sim, seed,
              fingerprint) -> str:
    return (f"v{SELECTION_VERSION}|{event}|{sex}|{'-'.join(states)}|{q_lo}|{q_hi}"
            f"|{n_cand}|{alpha}|{n_sim}|{seed}|{fingerprint}")


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  (cache at {CACHE_PATH} is unreadable; ignoring it)")
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


# ======================================================================
# THE ANALYSIS
# ======================================================================

def default_queries(seconds: np.ndarray) -> list[float]:
    """
    Score each pool at its own 1st, 5th, 25th and 100th fastest marks.

    Fixed times would mean something different in each event; ranks mean the
    same thing everywhere, which is what makes the resulting return periods
    comparable across events -- the whole point of the exercise.
    """
    ranked = np.sort(seconds)
    picks = [i for i in (0, 4, 24, 99) if i < ranked.size]
    return [float(ranked[i]) for i in picks]


def analyse(event: str, sex: str, states=None, q_lo=0.80, q_hi=0.995,
            n_cand=18, alpha=0.05, n_sim=199, n_boot=400, seed=0,
            queries=None, population=None, refit=False, make_plot=True,
            verbose=True, years=DEFAULT_YEARS, region="northeast") -> dict:
    """Build the pool, choose a threshold, fit the tail, score query times.

    `years` picks the dataset: one season, or several stacked (pool_data's
    "Pooling seasons"). Stacked seasons switch the bootstrap to resampling
    whole athletes. `region` picks the state scope ("northeast" or "us");
    `states=None` means all of it.
    """
    df, meta = load_pool(event, sex, states=states, years=years, region=region)
    states = tuple(meta["states"])
    seconds = df["seconds"].to_numpy(dtype=float)
    x = -seconds                                # into upper-tail space

    if verbose:
        print("=" * 74)
        who = "boys" if sex == "m" else "girls"
        print(f"  {meta['label']}  {who}   --  {len(meta['states'])} states pooled, "
              f"{meta['dataset']}")
        print("=" * 74)
        print(f"  athlete-seasons (n)     {meta['n']:,}")
        if len(meta["years"]) > 1:
            print(f"  distinct athletes       {meta['n_athletes']:,} "
                  f"({meta['n_multi_season']:,} in more than one season)")
        print(f"  fastest observed        {fmt_time(meta['fastest'])}")
        print(f"  median                  {fmt_time(meta['median'])}")
        for w in meta["coverage_warnings"]:
            print(f"  !! {w['tag']} under-collected ({w['n']:,} rows, expected "
                  f"~{w['expected']:,}) -- this pool is missing depth and tail")

    # ---- threshold, from cache or from scratch ------------------------
    key = cache_key(event, sex, states, q_lo, q_hi, n_cand, alpha, n_sim, seed,
                    data_fingerprint(seconds))
    cache = load_cache()
    if not refit and key in cache:
        sel = cache[key]
        if verbose:
            print(f"\n  (threshold from cache; --refit to recompute)")
            report_selection(sel)
    else:
        t0 = time.time()
        sel = select_threshold(seconds, q_lo=q_lo, q_hi=q_hi, n_cand=n_cand,
                               alpha=alpha, n_sim=n_sim, seed=seed,
                               verbose=verbose)
        sel["seconds_taken"] = round(time.time() - t0, 1)
        cache[key] = sel
        save_cache(cache)
        if verbose:
            report_selection(sel)
            print(f"  (selection took {sel['seconds_taken']} s; cached)")

    u = -sel["u_sec"]
    fit = fit_gpd(x, u, population)

    # ---- who is in the tail? ---------------------------------------------
    # A pool is a mixture, and its tail belongs to whichever components reach
    # furthest. Each state's share of the exceedances against its share of
    # the whole pool makes that concrete: a ratio above 1 means the state is
    # over-represented among the fast athletes the GPD is fitted to.
    in_tail = df["seconds"] < sel["u_sec"]
    share_n = df.groupby("state_dir").size() / len(df)
    share_t = df[in_tail].groupby("state_dir").size() / max(int(in_tail.sum()), 1)
    tail_share = (pd.DataFrame({"share_n": share_n, "share_tail": share_t})
                  .fillna(0.0).assign(ratio=lambda d: d.share_tail / d.share_n)
                  .sort_values("share_tail", ascending=False))

    # ---- bootstrap -----------------------------------------------------
    # gpd_tail.bootstrap re-selects the threshold inside every resample, which
    # is right: threshold choice is part of the estimator, and freezing it gives
    # intervals that are too narrow. Re-running the full ForwardStop 400 times
    # is not affordable, so the chosen u is expressed as its empirical quantile
    # and each resample re-derives u at that quantile. The RULE is held fixed,
    # not the value. This captures sampling variation in the threshold but not
    # variation in the selection procedure itself, so read the interval as a
    # lower bound on the true uncertainty.
    #
    # Stacked seasons resample ATHLETES, not rows (pool_data, "Pooling
    # seasons"): a repeat athlete's two marks travel together, so the interval
    # reflects how many independent people the tail really rests on.
    q_of_u = float((x <= u).mean())
    queries = list(queries) if queries else default_queries(seconds)
    groups = df["athlete"].to_numpy() if len(meta["years"]) > 1 else None
    boot = None
    if n_boot > 0:
        rng = np.random.default_rng(seed)
        boot = bootstrap(x, queries, "quantile", q_of_u, n_boot, rng, population,
                         groups=groups)

    results = {
        "event": event, "sex": sex, "label": meta["label"], "pool": meta["pool"],
        "dataset": meta["dataset"], "years": meta["years"],
        "n_athletes": meta["n_athletes"],
        "n_multi_season": meta["n_multi_season"],
        "bootstrap": "athlete clusters" if groups is not None else "rows",
        "n_states": len(meta["states"]),
        "n_before_fence": meta["n_before_fence"], "n": meta["n"],
        "rp_sensitivity": meta["rp_sensitivity"],
        "fence_s": meta["fence"], "n_fenced": meta["n_fenced"],
        "coverage_warnings": [w["tag"] for w in meta["coverage_warnings"]],
        "u_sec": fit.u_seconds, "n_exceed": fit.n_exceed, "zeta": fit.zeta,
        "xi": fit.xi, "sigma": fit.sigma,
        "endpoint_s": fit.endpoint_seconds,
        "fastest_s": meta["fastest"],
        "wall_margin_s": (meta["fastest"] - fit.endpoint_seconds
                          if fit.endpoint_seconds is not None else None),
        "selection": sel, "region": region,
        "tail_share": tail_share,
        "queries": [], "xi_ci": (np.nan, np.nan),
    }
    if boot:
        results["xi_ci"] = tuple(boot["xi_ci"])
        results["n_boot_ok"] = boot["n_ok"]

        # Interval for the implied wall. The endpoint is the headline physical
        # output of a bounded fit and the most fragile number it produces -- it
        # sits beyond every observation, and it depends on sigma/|xi|, a ratio
        # of two quantities that are themselves uncertain and correlated. A
        # point estimate on its own invites more confidence than it has earned.
        #
        # Resamples with no finite wall (xi >= 0, or a wall at or below 0 s)
        # count as "unbounded" instead of being dropped; when enough of them do,
        # the interval's fast end is -inf (gpd_tail.endpoint_interval). Before
        # 2026-10-09 they were dropped or kept as numbers like -19.5 s.
        lo, hi, unb = endpoint_interval(boot["raw"])
        if np.isfinite(hi) or np.isneginf(hi):
            results["endpoint_ci"] = (lo, hi)
            results["wall_unbounded_frac"] = unb

    ep = results["endpoint_s"]
    ep_ci = results.get("endpoint_ci")
    for t_q in queries:
        r = exceedance_probability(t_q, fit)
        row = {"time_s": t_q, "status": r["status"], "prob": r["prob"],
               "return_period": r["return_period"]}

        # Is this query so close to the fitted wall that its return period is
        # really a statement about the wall rather than about the athlete?
        #
        # For xi < 0 the survival probability collapses to zero AT the endpoint,
        # so a mark sitting just outside it gets an enormous return period that
        # moves by orders of magnitude if the endpoint moves slightly -- and the
        # endpoint is the least certain thing the model estimates. When the gap
        # to the wall is smaller than the wall's own confidence interval, the
        # number is not identified by the data and must not be compared across
        # events, which is exactly what this project wants to do with it.
        # An interval with no finite fast end has infinite width, so every
        # query counts as near the wall: nothing about the wall is identified.
        if ep is None or ep_ci is None:
            row["near_wall"] = False
        else:
            width = ep_ci[1] - ep_ci[0]          # +inf when the fast end is -inf
            row["near_wall"] = bool(not np.isfinite(width) or (t_q - ep) < width)

        if boot:
            lo, hi = boot["prob_ci"][t_q]
            row["rp_ci"] = (1 / hi if np.isfinite(hi) and hi > 0 else np.nan,
                            1 / lo if np.isfinite(lo) and lo > 0 else np.nan)
        results["queries"].append(row)

    if verbose:
        report_fit(results)

    if make_plot:
        gpd_dir = dataset_dirs(meta["years"], region)["gpd"]
        gpd_dir.mkdir(parents=True, exist_ok=True)
        who = "boys" if sex == "m" else "girls"
        path = gpd_dir / f"gpd_{meta['pool']}_{sex}.png"
        sweep = threshold_sweep(x)
        make_figure(x, fit, sweep, queries,
                    f"{meta['label']} {who}, {len(meta['states'])} states pooled, "
                    f"{meta['dataset']}",
                    path)

        # make_figure labels its x-axes in raw seconds, which is fine for a
        # sprint and unreadable for a mile -- "290, 285, 280" against "4:50,
        # 4:45, 4:40". It leaves the figure open, so relabel and re-save rather
        # than fork a copy of it into this folder.
        #
        # Panels 0, 1 and 3 carry absolute times. Panel 2 is the QQ plot, whose
        # axes are EXCESSES above the threshold -- a duration, not a clock
        # reading. Formatting those as m:ss turns a 69-second excess into
        # "1:09.00", which invites reading it as a time of day, so that panel
        # keeps plain seconds.
        if meta["median"] >= 60:
            fig = plt.gcf()
            for i, ax in enumerate(fig.axes):
                if i != 2:
                    ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_time))
            leg = fig.axes[0].get_legend()
            if leg and leg.get_texts():
                leg.get_texts()[0].set_text(f"chosen u = {fmt_time(fit.u_seconds)}")
            fig.savefig(path, dpi=140)
        plt.close("all")
        results["figure"] = str(path)

    return results


def report_fit(r: dict) -> None:
    """Print the fit the way gpd_tail.py prints it, plus the pooled extras."""
    print("\n  --- GPD fit ---")
    print(f"  threshold u             {fmt_time(r['u_sec'])}")
    print(f"  exceedances N_u         {r['n_exceed']:,}")
    print(f"  base rate N_u/n         {r['zeta']:.5f}")
    print(f"  shape  xi               {r['xi']:+.4f}")
    lo, hi = r["xi_ci"]
    if np.isfinite(lo):
        print(f"  xi 95% CI               [{lo:+.4f}, {hi:+.4f}]"
              f"   ({r.get('n_boot_ok', 0)} resamples converged)")
    print(f"  scale  sigma            {r['sigma']:.4f}")

    if r["endpoint_s"] is not None:
        lo, hi = r.get("endpoint_ci", (np.nan, np.nan))
        ci = (f"   95% CI [{fmt_time(lo)}, {fmt_time(hi)}]"
              if np.isfinite(lo) and np.isfinite(hi) else "")
        if np.isneginf(lo):
            # Too many resamples had no finite wall for the interval to have a
            # fast end: the data cannot rule out "no wall at all".
            ci = (f"   95% CI [unbounded, {fmt_time(hi)}]  "
                  f"({r['wall_unbounded_frac']:.0%} of resamples had no wall)")
        print(f"  implied hard limit      {fmt_time(r['endpoint_s'])}   "
              f"({r['wall_margin_s']:+.2f} s vs the fastest athlete){ci}")

        # A wall sitting just under the fastest observed mark means two very
        # different things depending on how much data is behind it, so the
        # warning has to know which case it is in.
        if r["wall_margin_s"] is not None and r["wall_margin_s"] < 1.0:
            if r["n_exceed"] < 200:
                print("  !! The implied wall sits barely under the fastest mark")
                print("     in the pool, on only "
                      f"{r['n_exceed']} exceedances. That is a fit")
                print("     held up by one or two athletes rather than by the")
                print("     shape of a tail. Lower the threshold.")
            else:
                # Not a red flag. For xi < 0 the sample maximum converges to the
                # endpoint as n grows, so with tens of thousands of athletes the
                # fastest observed mark SHOULD already sit close to the fitted
                # wall. The endpoint remains the most fragile thing the model
                # produces -- it is an extrapolation of tail shape past all the
                # data -- which is what the interval above is for.
                print("     A small margin is expected here, not alarming: with")
                print(f"     xi < 0 and {r['n_exceed']:,} exceedances the sample")
                print("     maximum has largely converged to the endpoint. Read")
                print("     the wall as the model's most fragile output all the")
                print("     same -- it extrapolates past every observation.")
    else:
        print("  implied hard limit      none (xi >= 0, unbounded tail)")

    if r["xi"] < -0.5:
        # Smith (1985): below -0.5 the MLE is non-regular, so the standard
        # errors and asymptotic intervals are invalid rather than merely wide.
        print("  !! xi < -0.5: maximum likelihood is non-regular here. Standard")
        print("     errors are unreliable and the endpoint is being pinned by")
        print("     the fastest one or two marks. Try a lower threshold.")

    print("\n  --- query times ---")
    print(f"  {'time':>10}  {'P(<= t)':>12}  {'1 in':>14}  "
          f"{'-log10 P':>9}  {'95% CI on 1 in':>26}")
    print("  " + "-" * 78)
    for q in r["queries"]:
        if q["status"] != "ok" or not np.isfinite(q["prob"]) or q["prob"] <= 0:
            print(f"  {fmt_time(q['time_s']):>10}  {q['status']:>12}")
            continue
        line = (f"  {fmt_time(q['time_s']):>10}  {q['prob']:12.3e}  "
                f"{q['return_period']:14,.0f}  {-np.log10(q['prob']):9.2f}")
        ci = q.get("rp_ci")
        if ci and np.isfinite(ci[0]) and np.isfinite(ci[1]):
            line += f"  {ci[0]:11,.0f} - {ci[1]:11,.0f}"
        else:
            line += f"  {'unstable':>26}"
        if q.get("near_wall"):
            line += "  <-- AT THE WALL"
        print(line)

    if any(q.get("near_wall") for q in r["queries"]):
        print("\n  Rows marked AT THE WALL sit closer to the fitted endpoint than")
        print("  the endpoint's own confidence interval is wide. Their return")
        print("  periods are statements about where the wall landed, not about")
        print("  the athlete, and they must NOT be compared across events.")


# ======================================================================
# MAIN
# ======================================================================

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Pooled GPD tail fit.")
    ap.add_argument("--event", default="100m", choices=sorted(EVENTS))
    ap.add_argument("--sex", default="m", choices=list(SEXES))
    ap.add_argument("--region", default="northeast", choices=["northeast", "us"])
    ap.add_argument("--states", default=None,
                    help="comma-separated subset of the region (default: all of it)")
    ap.add_argument("--years", default="2026",
                    help="season(s): 2026, 2025, or 2025,2026 (stacked)")
    ap.add_argument("--q-lo", type=float, default=0.80,
                    help="lowest candidate threshold, as a quantile of the tail")
    ap.add_argument("--q-hi", type=float, default=0.995)
    ap.add_argument("--n-cand", type=int, default=18)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--n-sim", type=int, default=199,
                    help="parametric bootstrap sims per candidate threshold")
    ap.add_argument("--n-boot", type=int, default=400,
                    help="bootstrap resamples for CIs; 0 disables")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--population", type=int, default=None,
                    help="override n when the pool is not the full population")
    ap.add_argument("--query", default=None,
                    help="comma-separated times to score, seconds or M:SS.ss")
    ap.add_argument("--refit", action="store_true",
                    help="ignore the cached threshold and reselect")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="coarse and fast: for smoke tests, not for results")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.quick:
        args.n_sim, args.n_cand, args.n_boot = 49, 10, 100

    states = (tuple(s.strip().upper() for s in args.states.split(",") if s.strip())
              if args.states else None)
    queries = None
    if args.query:
        queries = [parse_time(q) for q in args.query.split(",")]
        queries = [q for q in queries if np.isfinite(q)]

    analyse(args.event, args.sex, states=states, q_lo=args.q_lo, q_hi=args.q_hi,
            n_cand=args.n_cand, alpha=args.alpha, n_sim=args.n_sim,
            n_boot=args.n_boot, seed=args.seed, queries=queries,
            population=args.population, refit=args.refit,
            make_plot=not args.no_plot, years=parse_years(args.years),
            region=args.region)


if __name__ == "__main__":
    main()
