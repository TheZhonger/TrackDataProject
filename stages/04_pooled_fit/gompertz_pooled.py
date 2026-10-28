"""
gompertz_pooled.py
==================
The national Gompertz tail model on 2025 and 2026 together: one fit per event
x sex, with its threshold chosen by ForwardStop and its uncertainty from an
athlete-cluster bootstrap.

THE MODEL (stages/03_tail_fit/tail_models.py)
---------------------------------------------
Work on x = -seconds, so faster is larger. Above a threshold u the excess
y = x - u has survival

    P(Y > y) = exp( -c * (e^(y/b) - 1) ),

and the unconditional share of athlete-seasons at time t or faster is
S(t) = zeta * P(Y > -t - u), with zeta = N_u / n counted, not modelled. The
return period of t is 1/S(t): "one athlete-season in N runs this fast".

Two physical readings. b (seconds) is the scale over which the tail's hazard
grows by a factor e: every b seconds faster, the per-second rate of athletes
thinning out multiplies by 2.7. c sets how fast that starts at u. There is no
wall -- the tail is unbounded but thins out faster than any exponential --
which is what the record test found the data wants (pooled_method.md §12-13).

THE THRESHOLD
-------------
ForwardStop (threshold_select.select_forwardstop, model="gompertz"): reject
low thresholds where an Anderson-Darling test says the Gompertz does not fit
the excesses, take the first one it does not reject. Where nothing is
rejected it uses the top 5% (fallback_u), not the lowest candidate: the
lowest-candidate fallback was too heavy at the record (§13.2). Same grid,
alpha and simulation count as the GPD's in run_all. The test's input is
jittered by +-0.005 s first: times are recorded to 0.01 s, and in a national
pool the resulting ties alone make the test reject everywhere.

STACKED SEASONS
---------------
Each row is an athlete-season. One athlete running both seasons is two rows
of one person, so the bootstrap resamples whole athletes (the cluster
bootstrap of gpd_tail.bootstrap(..., groups=)); resampling rows would treat
the two seasons of one runner as independent and give intervals too narrow.
Each resample re-takes u at the selected quantile level and refits.

    python stages/04_pooled_fit/gompertz_pooled.py [--n-boot 200] [--sex m,f] [--refit-fs]

Writes output/national/2025-2026/gompertz/ (dataset id us-2025-2026): gompertz.md, gompertz_fit.csv,
gompertz_queries.csv, gompertz_boot.csv (every bootstrap draw's u, zeta, c, b,
for gompertz_query.py), gompertz_forwardstop.csv, gompertz_tail_{m,f}.png
"""

from __future__ import annotations

import argparse
import sys
import zlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator
from scipy.stats import gamma

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from plot_pooled import (BLUE, INK, INK_SOFT, ORANGE, REFERENCE, SURFACE,
                         style_axis)
from pool_data import EVENTS, SEXES, load_pool, pool_name
from paths import POOLED_GOMPERTZ, TAILFIT_DIR  # src/

sys.path.insert(0, str(TAILFIT_DIR))
from tail_models import fit_tail  # noqa: E402
from threshold_select import dequantize, select_forwardstop  # noqa: E402

YEARS = (2025, 2026)
DATASET = "us-2025-2026"
FS_GRID = np.linspace(0.80, 0.995, 18)      # run_all's q_lo, q_hi, n_cand
FS_ALPHA, FS_NSIM, FS_MIN_EXCEED = 0.05, 199, 25
FS_FALLBACK_Q = 0.95                        # "nothing rejected" -> top 5%
FS_RESOLUTION = 0.01                        # de-tie ForwardStop's input
QUERY_RANKS = (1, 5, 25, 100)
SEASON_C = {2025: BLUE, 2026: ORANGE}       # fixed slots, as in density_plots


def out_dir():
    return POOLED_GOMPERTZ


# ---------------------------------------------------------------------------
# threshold
# ---------------------------------------------------------------------------
def select_u(x: np.ndarray, key: str, cache: dict) -> dict:
    """ForwardStop on the Gompertz for one pool; cached by pool key."""
    if key in cache:
        return cache[key]
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    # Ties at 0.01 s make the A-D test reject a continuous model at every
    # threshold in big pools; jitter the TEST input only (dequantize).
    x = dequantize(x, FS_RESOLUTION, rng)
    us = np.quantile(x, FS_GRID)
    r = select_forwardstop(x, us, alpha=FS_ALPHA, n_sim=FS_NSIM,
                           min_exceed=FS_MIN_EXCEED, rng=rng, verbose=False,
                           model="gompertz",
                           fallback_u=float(np.quantile(x, FS_FALLBACK_Q)))
    # The quantile level of the chosen u, so every bootstrap resample can
    # re-take u at the same level (the "re-select u" rule, as in gpd_pooled).
    q_level = float(np.mean(x <= r["u"]))
    outcome = ("ok" if r["note"] == "ok" else
               "nothing rejected -> top 5%" if r["note"].startswith("nothing")
               else "all rejected -> highest candidate")
    cache[key] = {"key": key, "u_sec": r["u_sec"], "q_level": q_level,
                  "n_exceed": r["n_exceed"], "outcome": outcome,
                  "k_reject": r["k_reject"], "n_candidates": len(r["us"]),
                  "pvalues": " ".join(f"{p:.3f}" for p in r["pvalues"])}
    return cache[key]


# ---------------------------------------------------------------------------
# cluster bootstrap
# ---------------------------------------------------------------------------
def cluster_members(groups: np.ndarray) -> list[np.ndarray]:
    """Row indices per athlete -- the same construction as gpd_tail.bootstrap."""
    _, inv = np.unique(np.asarray(groups), return_inverse=True)
    order = np.argsort(inv, kind="stable")
    return np.split(order, np.flatnonzero(np.diff(inv[order])) + 1)


def bootstrap_fits(x, members, q_level, n_boot, rng) -> list:
    fits = []
    for _ in range(n_boot):
        picks = rng.integers(0, len(members), size=len(members))
        xb = x[np.concatenate([members[k] for k in picks])]
        try:
            fits.append(fit_tail(xb, np.quantile(xb, q_level), "gompertz"))
        except ValueError:
            continue
    return fits


def ci(v) -> tuple[float, float]:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    return tuple(np.percentile(v, [2.5, 97.5])) if v.size >= 20 else (np.nan, np.nan)


# ---------------------------------------------------------------------------
# one pool
# ---------------------------------------------------------------------------
def analyse(event, sex, n_boot, rng, cache) -> tuple[dict, list, dict]:
    df, meta = load_pool(event, sex, years=YEARS, region="us")
    t_all = df["seconds"].to_numpy(dtype=float)
    x = -t_all
    t = np.sort(t_all)
    key = f"us|{event}|{sex}|{'-'.join(map(str, YEARS))}"
    sel = select_u(x, key, cache)
    # Fit at the RAW data's quantile at the selected level -- the same rule
    # every bootstrap resample uses. (ForwardStop's u comes from the jittered
    # data; on raw data with 0.01 s ties, a threshold that lands on a tied
    # value includes or excludes that whole block, and mixing the two rules
    # put the point estimate outside its own bootstrap interval.)
    u = float(np.quantile(x, sel["q_level"]))
    fit = fit_tail(x, u, "gompertz")
    members = cluster_members(df["athlete"].to_numpy())
    boots = bootstrap_fits(x, members, sel["q_level"], n_boot, rng)

    row = {"event": pool_name(event, sex), "sex": sex, "n": int(x.size),
           "n_athletes": len(members), "u_sec": fit.u_seconds,
           "top_pct": 100 * fit.zeta, "N_u": fit.n_exceed,
           "fs_outcome": sel["outcome"], "fs_k_reject": sel["k_reject"],
           "c": fit.params["c"], "b": fit.params["b"],
           "c_lo": ci([f.params["c"] for f in boots])[0],
           "c_hi": ci([f.params["c"] for f in boots])[1],
           "b_lo": ci([f.params["b"] for f in boots])[0],
           "b_hi": ci([f.params["b"] for f in boots])[1],
           "n_boot_ok": len(boots)}
    # Per-season n: the base for "athletes this fast in one season" in
    # gompertz_query.py (a return period divided into one season's field).
    for y in YEARS:
        row[f"n_{y}"] = int((df["year"].to_numpy() == y).sum())

    qrows = []
    for k in QUERY_RANKS:
        q = float(t[k - 1])
        rp_b = [float(f.return_period(q)) for f in boots]
        lo, hi = ci(rp_b)
        qrows.append({"event": row["event"], "sex": sex, "kind": f"rank {k}",
                      "time_s": q, "rp": float(fit.return_period(q)),
                      "rp_lo": lo, "rp_hi": hi,
                      # in-sample: athletes the fit expects this fast vs k
                      "pred_over_actual": x.size * float(fit.prob(q)) / k})

    # Each season's record, scored by the stacked fit with that season's n:
    # z = n_y * S(record_y) ~ Exp(1) if the model is right. In sample (the
    # record helped fit the model), so this is a consistency check only.
    records = {}
    for y in YEARS:
        ty = np.sort(t_all[df["year"].to_numpy() == y])
        rec, n_y = float(ty[0]), ty.size
        z = n_y * float(fit.prob(rec))
        zb = np.array([n_y * float(f.prob(rec)) for f in boots])
        zb = zb[np.isfinite(zb)]
        records[y] = rec
        qrows.append({"event": row["event"], "sex": sex, "kind": f"{y} record",
                      "time_s": rec, "rp": float(fit.return_period(rec)),
                      "rp_lo": ci([float(f.return_period(rec)) for f in boots])[0],
                      "rp_hi": ci([float(f.return_period(rec)) for f in boots])[1],
                      "pred_over_actual": z, "n_season": n_y,
                      "p_plugin": float(gamma.cdf(z, 1)),
                      "p_predictive": float(gamma.cdf(zb, 1).mean()) if zb.size else np.nan})
    plot = {"t": t, "fit": fit, "boots": boots, "records": records}
    # Every draw's own (u, zeta, c, b): enough to rebuild its return period at
    # any time, so gompertz_query.py can give a joint interval. The c and b
    # intervals in gompertz_fit.csv are marginal, and c and b are correlated,
    # so they cannot be combined into an interval for a return period.
    plot["draws"] = [{"event": row["event"], "sex": sex, "draw": i,
                      "u_sec": f.u_seconds, "zeta": f.zeta,
                      "c": f.params["c"], "b": f.params["b"]}
                     for i, f in enumerate(boots)]
    return row, qrows, plot


# ---------------------------------------------------------------------------
# figure
# ---------------------------------------------------------------------------
def _mss(v, _p=None):
    return f"{int(v // 60)}:{int(round(v % 60)):02d}" if v >= 60 else f"{v:g}"


def figure_tail(plots: dict, sex: str, path, dpi: int) -> None:
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(3.4 * len(EVENTS), 3.8))
    for ax, ev in zip(axes, EVENTS):
        P = plots[ev]
        t, fit, boots = P["t"], P["fit"], P["boots"]
        n = t.size
        style_axis(ax)
        k = fit.n_exceed
        # empirical survival above u: the k-th fastest has S = k/n
        ax.step(t[:k], np.arange(1, k + 1) / n, where="post", color=INK_SOFT,
                lw=1.0, label="data (both seasons)")
        grid = np.linspace(t[0] - 0.02 * (fit.u_seconds - t[0]), fit.u_seconds, 300)
        if boots:
            S = np.array([f.prob(grid) for f in boots], dtype=float)
            lo, hi = np.nanpercentile(S, [2.5, 97.5], axis=0)
            ax.fill_between(grid, lo, hi, color=REFERENCE, alpha=0.25, lw=0,
                            label="95% bootstrap band")
        ax.plot(grid, fit.prob(grid), color=INK, lw=2, label="Gompertz fit")
        for y, rec in P["records"].items():
            ax.axvline(rec, color=SEASON_C[y], lw=1.4, ls="--", label=f"{y} record")
        ax.set_yscale("log")
        ax.set_ylim(0.3 / n, None)
        ax.xaxis.set_major_locator(MaxNLocator(5))
        if t[0] >= 60:
            ax.xaxis.set_major_formatter(FuncFormatter(_mss))
        ax.set_title(f"{pool_name(ev, sex)}: top {100 * fit.zeta:.1f}% "
                     f"(N_u = {fit.n_exceed:,})", fontsize=9.5, color=INK)
        ax.set_xlabel("time", fontsize=8, color=INK_SOFT)
    axes[0].set_ylabel("share of athlete-seasons\nat this time or faster",
                       fontsize=9, color=INK_SOFT)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, frameon=False, fontsize=8)
    fig.suptitle(f"National {'boys' if sex == 'm' else 'girls'}, 2025 + 2026 stacked: "
                 "Gompertz tail above the ForwardStop threshold", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# write-up (read by Daren: ASD-STE100 style)
# ---------------------------------------------------------------------------
def _rp(v) -> str:
    return f"{v:,.0f}" if np.isfinite(v) else "-"


def _t(s) -> str:
    return f"{int(s // 60)}:{s % 60:05.2f}" if s >= 60 else f"{s:.2f}"


def write_md(F: pd.DataFrame, Q: pd.DataFrame, n_boot: int) -> None:
    L = ["# National Gompertz model, 2025 + 2026", ""]
    L.append("Generated by `gompertz_pooled.py`. The two national seasons are "
             "stacked. Each row of the data is one athlete-season.")
    L.append("")
    L.append("**The model.** Above the threshold u, the share of athlete-seasons "
             "at time t or faster is S(t) = ζ · exp(−c·(e^(y/b) − 1)). Here "
             "y = u − t is how far t is faster than u, and ζ = N_u / n. "
             "The return period is 1/S(t): one athlete-season in N.")
    L.append("")
    L.append("**The threshold.** ForwardStop selects u (Anderson–Darling test, "
             "α = 0.05, 18 thresholds from the top 20% to the top 0.5%). If it "
             "rejects nothing, u is the top 5%. Before the test, each time is "
             "spread by ±0.005 s. Times have only hundredths, and the ties "
             "otherwise make the test reject everything in a large pool.")
    L.append("")
    L.append(f"**Uncertainty.** {n_boot} bootstrap resamples of complete athletes. "
             "One athlete in both seasons stays together. Each resample takes u "
             "again at the same quantile level.")
    L.append("")
    L.append("## Fits")
    L.append("")
    L.append("| pool | n | ForwardStop | threshold | N_u | c (95% CI) | b, s (95% CI) |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in F.iterrows():
        L.append(f"| {r['event']} {r['sex']} | {r['n']:,} | {r['fs_outcome']} "
                 f"| {_t(r['u_sec'])} (top {r['top_pct']:.1f}%) | {r['N_u']:,} "
                 f"| {r['c']:.3f} ({r['c_lo']:.3f}–{r['c_hi']:.3f}) "
                 f"| {r['b']:.3f} ({r['b_lo']:.3f}–{r['b_hi']:.3f}) |")
    L.append("")
    L.append("b is a time scale. For every b seconds faster, the rate at which "
             "athletes become fewer increases by a factor of e (2.7).")
    L.append("")
    L.append("## Return periods (one athlete-season in N)")
    L.append("")
    L.append("| pool | mark | time | 1 in N | 95% CI | expected ÷ actual |")
    L.append("|---|---|---|---|---|---|")
    for _, r in Q[Q["kind"].str.startswith("rank")].iterrows():
        L.append(f"| {r['event']} {r['sex']} | {r['kind']} | {_t(r['time_s'])} "
                 f"| {_rp(r['rp'])} | {_rp(r['rp_lo'])}–{_rp(r['rp_hi'])} "
                 f"| {r['pred_over_actual']:.2f} |")
    L.append("")
    L.append("## Each season's record under the stacked model (in sample)")
    L.append("")
    L.append("z = n_season · S(record) is the number of athletes that the model "
             "expects at the record or faster. If the model is correct, z follows "
             "Exp(1): the median is 0.69 and the 95% range is 0.025–3.69. The "
             "record was part of the fit, so this is a consistency check only.")
    L.append("")
    L.append("| pool | season | record | 1 in N | z | plug-in p | predictive p |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in Q[Q["kind"].str.endswith("record")].iterrows():
        L.append(f"| {r['event']} {r['sex']} | {r['kind'][:4]} | {_t(r['time_s'])} "
                 f"| {_rp(r['rp'])} | {r['pred_over_actual']:.2f} "
                 f"| {r['p_plugin']:.3f} | {r['p_predictive']:.3f} |")
    L.append("")
    L.append("Figures: `gompertz_tail_m.png`, `gompertz_tail_f.png`.")
    (out_dir() / "gompertz.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  wrote {out_dir() / 'gompertz.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="National stacked Gompertz fits.")
    ap.add_argument("--n-boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sex", default="m,f")
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--refit-fs", action="store_true",
                    help="ignore the cached ForwardStop selections")
    args = ap.parse_args()
    out_dir().mkdir(parents=True, exist_ok=True)
    cache_path = out_dir() / "gompertz_forwardstop.csv"
    cache = {}
    if cache_path.exists() and not args.refit_fs:
        cache = {r["key"]: r for r in pd.read_csv(cache_path).to_dict("records")}
    rng = np.random.default_rng(args.seed)
    rows, qrows, draws = [], [], []
    for sex in args.sex.split(","):
        plots = {}
        for ev in EVENTS:
            print(f"  {pool_name(ev, sex)} {sex}", flush=True)
            row, q, plots[ev] = analyse(ev, sex, args.n_boot, rng, cache)
            rows.append(row)
            qrows += q
            draws += plots[ev]["draws"]
            pd.DataFrame(list(cache.values())).to_csv(cache_path, index=False)
        figure_tail(plots, sex, out_dir() / f"gompertz_tail_{sex}.png", args.dpi)
    F, Q = pd.DataFrame(rows), pd.DataFrame(qrows)
    F.to_csv(out_dir() / "gompertz_fit.csv", index=False)
    Q.to_csv(out_dir() / "gompertz_queries.csv", index=False)
    pd.DataFrame(draws).to_csv(out_dir() / "gompertz_boot.csv", index=False)
    write_md(F, Q, args.n_boot)


if __name__ == "__main__":
    main()
