"""
gompertz_fit_quality.py
=======================
How good is the national Gompertz model (2025 + 2026 stacked) as a description
of the fast tail? Four views, from the shape of the whole tail to the record.

1. QQ PLOT -- is the SHAPE right above u?
   Sort the N_u excesses (how far each mark is faster than u, in seconds).
   The i-th smallest should sit near the model's quantile at (i - 0.5)/N_u.
   Points on the diagonal = right shape. A 95% band from 200 samples drawn
   from the fitted model shows how far from the diagonal pure chance goes.

2. EXPECTED / ACTUAL BY RANK -- are the COUNTS right, mark by mark?
   For each distinct time t in the tail, compare the athletes the model
   expects at t or faster, n*S(t), with the count c that actually were. Under
   a correct model n*S(t) ~ Gamma(c, 1) (the record yardstick, generalised),
   so the 95% band for the ratio is Gamma(c,1)/c: about x0.025-x3.7 at the
   record, about +-20% at c = 100, +-6% at c = 1000. Times are recorded to
   0.01 s, so many athletes share a time; using distinct times and their
   cumulative counts handles the ties, and S is evaluated at t + 0.005 s
   because a mark recorded as t is anywhere up to 0.005 s slower in truth.

3. A FORMAL TEST, READ HONESTLY.
   Anderson-Darling on the de-tied excesses, parametric-bootstrap p-value (the
   ForwardStop test at the chosen u). With N_u in the thousands this test
   detects misfits far too small to matter for scoring, so a small p is
   context, not a verdict; views 1, 2 and 4 measure the SIZE of the misfit.

4. OUT OF SAMPLE.
   Fit 2025 alone and score 2026's counts (and the reverse), at the quantile
   level the stacked fit uses. Same ratio and band as view 2. Plus the record
   test across Census divisions (record_check.py part D, rule gompertz-fs5),
   summarised from its CSV, not re-run.

Reads the fits from gompertz_pooled.py (gompertz_fit.csv and its ForwardStop
cache) and refits at the same raw quantile, so the numbers are those fits.

    python stages/04_pooled_fit/gompertz_fit_quality.py [--n-sim 200] [--seed 0]

Writes output/national/2025-2026/gompertz/: fit_quality.md, fit_quality.csv,
fit_quality_{qq,ratio,oos}_{m,f}.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gamma

# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from plotstyle import (BLUE, INK, INK_SOFT, ORANGE, REFERENCE, SURFACE,  # noqa: E402
                       style_axis)
from pool_data import EVENTS, SEXES, load_pool, pool_name  # noqa: E402
from paths import POOLED_RECORDS, TAILFIT_DIR  # noqa: E402

sys.path.insert(0, str(TAILFIT_DIR))
from tail_models import fit_gompertz_excess, fit_tail  # noqa: E402
from threshold_select import dequantize, gof_pvalue  # noqa: E402

import gompertz_pooled as gp  # noqa: E402  (same stage: the fits under review)

HALF_TICK = 0.005            # half the 0.01 s timing resolution
MIN_COUNT = 10               # ratios below this count are all noise (band > x2)
SEASON_C = {2025: BLUE, 2026: ORANGE}

# Verdict rules, fixed here so the report can state them. "in" = in-sample
# share of tail times (count >= MIN_COUNT) inside the 95% band (a correct
# model gives 0.96-1.00 on simulations). "oos" = how far the real
# out-of-sample typical error exceeds the error a CORRECT model shows for the
# same pool (oos_null), in percentage points. Relative to that yardstick, not
# a fixed %, because a small pool's correct-model error is itself ~10%
# (first version used a fixed 10% and called the 800 m boys "fair" for its size).
GOOD = {"in": 0.90, "oos": 0.03}
FAIR = {"in": 0.70, "oos": 0.08}


# ---------------------------------------------------------------------------
# the pieces
# ---------------------------------------------------------------------------
def ratio_curve(fit, t: np.ndarray, n: int):
    """
    Expected / actual at every distinct time in the tail of season t.
    Returns (counts c, ratio n*S/c, band lo, band hi) over distinct times
    at or faster than u, fastest first.
    """
    tail = np.sort(t[t <= fit.u_seconds])
    times, idx = np.unique(tail, return_index=True)
    c = np.r_[idx[1:], tail.size].astype(float)        # cumulative count at <= time
    expect = n * np.nan_to_num(fit.prob(np.minimum(times + HALF_TICK, fit.u_seconds)),
                               nan=0.0)
    lo, hi = gamma.ppf(0.025, c) / c, gamma.ppf(0.975, c) / c
    return c, expect / c, lo, hi


def qq_data(fit, x: np.ndarray, n_sim: int, rng):
    """
    Detrended QQ: the gap (data quantile - model quantile) of the excesses at
    each plotting position (i-0.5)/N, and a 95% band for that gap.

    The band is a parametric bootstrap of the WHOLE procedure, because two
    shortcuts both failed a check on simulated, correctly specified tails
    rounded to 0.01 s:
      * continuous draws from the fitted model held 79-84% of the points --
        they ignore that marks are rounded, that u sits on a rounded value and
        that marks tied AT u are left out;
      * also rounding the draws held 60-91% -- the fitted parameters carry
        estimation error, and a band around one fitted curve ignores it.
    So each simulated sample is drawn from the fit, turned into times, rounded,
    cut at u, REFITTED, and its gap measured against its own refit -- the same
    steps the data went through. Excesses are de-tied by +-0.005 s first
    (threshold_select.dequantize), data and simulations alike.
    """
    def gaps(exc_rounded):
        c, b = fit_gompertz_excess(exc_rounded)
        e = np.sort(np.abs(dequantize(exc_rounded, gp.FS_RESOLUTION, rng)))
        pp = (np.arange(1, e.size + 1) - 0.5) / e.size
        q = b * np.log1p(-np.log(1 - pp) / c)          # Gompertz excess quantile
        return q, e - q

    y = x[x > fit.u] - fit.u
    N = y.size
    model, gap = gaps(y)
    M = int(N * 1.3) + 50            # spare draws: some round onto u and drop out
    sims = np.empty((n_sim, N))
    for i in range(n_sim):
        t_sim = np.round(fit.u_seconds - fit.isf_excess(rng.random(M)), 2)
        e = (-t_sim[-t_sim > fit.u] - fit.u)[:N]
        sims[i] = gaps(e)[1] if e.size == N else np.nan
    lo, hi = np.nanpercentile(sims, [2.5, 97.5], axis=0)
    return model, gap, lo, hi


def summarise_ratio(c, r, lo, hi) -> dict:
    """
    share_in_band and median_abs_dev over counts >= MIN_COUNT; worst_ratio only
    over counts >= 100. On simulated, correctly specified tails the worst ratio
    at counts >= 10 still reached x0.69-x1.33 (the band at c = 10 is
    x0.48-x1.71), so a worst ratio that low in the tail says nothing; from
    c = 100 the band is about +-20% and the worst ratio is informative.
    """
    m = c >= MIN_COUNT
    m100 = c >= 100
    inside = (r >= lo) & (r <= hi)
    worst = r[m100][np.argmax(np.abs(np.log(r[m100])))] if m100.any() else np.nan
    return {"share_in_band": float(inside[m].mean()) if m.any() else np.nan,
            "worst_ratio": float(worst),
            "median_abs_dev": float(np.median(np.abs(r[m] - 1))) if m.any() else np.nan}


def oos_null(fit, years: np.ndarray, t: np.ndarray, q_level: float, rng,
             reps: int = 20) -> float:
    """
    The out-of-sample "typical error" a CORRECT model would show for this pool.

    Two seasons are drawn from the stacked fit itself, at the real seasons'
    sizes: each season's marks slower than u are kept as they are, and its
    marks faster than u are replaced by draws from the Gompertz (rounded to
    0.01 s, like real times). Then one season is fitted at q_level and scored
    on the other, as in view 4. With no real difference between seasons, any
    error left is fit noise plus count noise -- the yardstick for the real
    out-of-sample number.
    """
    devs = []
    for _ in range(reps):
        sim = {}
        for y in (2025, 2026):
            ty = t[years == y]
            slow = ty[ty > fit.u_seconds]
            k = ty.size - slow.size
            fast = np.round(fit.u_seconds - fit.isf_excess(rng.random(k)), 2)
            sim[y] = np.r_[fast, slow]
        for a, b in ((2025, 2026), (2026, 2025)):
            fa = season_fit(sim[a], q_level)
            devs.append(summarise_ratio(*ratio_curve(fa, sim[b], sim[b].size))["median_abs_dev"])
    return float(np.mean(devs))


def season_fit(t_season: np.ndarray, q_level: float):
    x = -t_season
    return fit_tail(x, float(np.quantile(x, q_level)), "gompertz")


# ---------------------------------------------------------------------------
# one pool
# ---------------------------------------------------------------------------
def analyse(event, sex, F_row, cache, n_sim, rng) -> tuple[dict, dict]:
    df, _ = load_pool(event, sex, years=gp.YEARS, region="us")
    t = df["seconds"].to_numpy(dtype=float)
    x = -t
    key = f"us|{event}|{sex}|{'-'.join(map(str, gp.YEARS))}"
    q_level = float(cache[key]["q_level"])
    fit = fit_tail(x, float(np.quantile(x, q_level)), "gompertz")
    # The fit under review must be the one gompertz_pooled reported.
    for k in ("c", "b"):
        if abs(fit.params[k] / F_row[k] - 1) > 1e-6:
            raise SystemExit(f"{event} {sex}: {k} {fit.params[k]} != {F_row[k]}")

    model, gap, qlo, qhi = qq_data(fit, x, n_sim, rng)
    probes = {}
    for p in (0.5, 0.9, 0.99, 0.999):
        i = min(int(p * gap.size), gap.size - 1)
        probes[p] = (float(gap[i]), bool(qlo[i] <= gap[i] <= qhi[i]))

    c, r, lo, hi = ratio_curve(fit, t, t.size)
    ins = summarise_ratio(c, r, lo, hi)

    years = df["year"].to_numpy()
    oos_curves, oos_dev = {}, []
    for a, b in ((2025, 2026), (2026, 2025)):
        fa = season_fit(t[years == a], q_level)
        tb = t[years == b]
        cb, rb, lob, hib = ratio_curve(fa, tb, tb.size)
        oos_curves[(a, b)] = (cb, rb, lob, hib)
        oos_dev.append(summarise_ratio(cb, rb, lob, hib))

    exc = dequantize(x, gp.FS_RESOLUTION, rng)
    exc = exc[exc > fit.u] - fit.u
    p_ad = gof_pvalue(exc, 199, rng, "gompertz")

    oos_med = float(np.mean([d["median_abs_dev"] for d in oos_dev]))
    share = ins["share_in_band"]
    oos_null_dev = oos_null(fit, years, t, q_level, rng)
    oos_excess = oos_med - oos_null_dev
    if share >= GOOD["in"] and oos_excess <= GOOD["oos"]:
        verdict = "good"
    elif share >= FAIR["in"] and oos_excess <= FAIR["oos"]:
        verdict = "fair"
    else:
        verdict = "poor"

    row = {"event": pool_name(event, sex), "sex": sex, "n": t.size,
           "u_sec": fit.u_seconds, "N_u": fit.n_exceed,
           **{f"qq_gap_{int(p * 1000)}": g for p, (g, _) in probes.items()},
           **{f"qq_in_band_{int(p * 1000)}": ok for p, (_, ok) in probes.items()},
           "in_share_in_band": ins["share_in_band"], "in_worst_ratio": ins["worst_ratio"],
           "in_median_abs_dev": ins["median_abs_dev"],
           "oos_25to26_share": oos_dev[0]["share_in_band"],
           "oos_25to26_median_abs_dev": oos_dev[0]["median_abs_dev"],
           "oos_26to25_share": oos_dev[1]["share_in_band"],
           "oos_26to25_median_abs_dev": oos_dev[1]["median_abs_dev"],
           "oos_null_median_abs_dev": oos_null_dev,
           "ad_pvalue_detied": p_ad, "verdict": verdict}
    row["qq_share_in_band"] = float(np.mean((gap >= qlo) & (gap <= qhi)))
    plot = {"qq": (model, gap, qlo, qhi), "ratio": (c, r, lo, hi), "oos": oos_curves,
            "fit": fit}
    return row, plot


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def _grid(sex, title):
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(3.4 * len(EVENTS), 3.8))
    fig.suptitle(f"National {'boys' if sex == 'm' else 'girls'}, 2025 + 2026: {title}",
                 fontsize=11, color=INK)
    return fig, axes


def _save(fig, path, handles=None, labels=None):
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=len(labels),
                   frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.08 if handles else 0, 1, 0.93))
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


def figure_qq(plots, sex, path):
    fig, axes = _grid(sex, "detrended QQ: data − model quantile of the excesses above u")
    for ax, ev in zip(axes, EVENTS):
        model, gap, lo, hi = plots[ev]["qq"]
        style_axis(ax)
        ax.fill_between(model, lo, hi, color=REFERENCE, alpha=0.3, lw=0)
        ax.plot(model, gap, color=BLUE, lw=1.2)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_title(f"{pool_name(ev, sex)} (N_u = {gap.size:,})", fontsize=9.5, color=INK)
        ax.set_xlabel("model quantile: seconds faster than u", fontsize=8, color=INK_SOFT)
    axes[0].set_ylabel("data − model (s)", fontsize=9, color=INK_SOFT)
    h = [plt.Line2D([], [], color=BLUE, lw=1.2), plt.Line2D([], [], color=INK, lw=0.8),
         plt.Rectangle((0, 0), 1, 1, color=REFERENCE, alpha=0.3)]
    _save(fig, path, h, ["data − model", "perfect fit",
                         "95% band (200 refitted model samples)"])


def _ratio_axes(ax, ev, sex):
    style_axis(ax)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.25, 4)
    ax.set_yticks([0.25, 0.5, 1, 2, 4])
    ax.set_yticklabels(["×0.25", "×0.5", "×1", "×2", "×4"])
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_title(pool_name(ev, sex), fontsize=9.5, color=INK)
    ax.set_xlabel("athletes at this time or faster", fontsize=8, color=INK_SOFT)


def figure_ratio(plots, sex, path):
    fig, axes = _grid(sex, "expected ÷ actual count, every distinct time in the tail")
    for ax, ev in zip(axes, EVENTS):
        c, r, lo, hi = plots[ev]["ratio"]
        _ratio_axes(ax, ev, sex)
        ax.fill_between(c, lo, hi, color=REFERENCE, alpha=0.3, lw=0)
        ax.plot(c, r, color=BLUE, lw=1.2)
    axes[0].set_ylabel("expected ÷ actual (log)", fontsize=9, color=INK_SOFT)
    h = [plt.Line2D([], [], color=BLUE, lw=1.2),
         plt.Rectangle((0, 0), 1, 1, color=REFERENCE, alpha=0.3)]
    _save(fig, path, h, ["stacked fit, in sample", "95% band if the model is right"])


def figure_oos(plots, sex, path):
    fig, axes = _grid(sex, "out of sample: fit one season, count the other")
    for ax, ev in zip(axes, EVENTS):
        _ratio_axes(ax, ev, sex)
        for (a, b), (c, r, lo, hi) in plots[ev]["oos"].items():
            ax.fill_between(c, lo, hi, color=SEASON_C[b], alpha=0.10, lw=0)
            ax.plot(c, r, color=SEASON_C[b], lw=1.2)
    axes[0].set_ylabel("expected ÷ actual (log)", fontsize=9, color=INK_SOFT)
    h = [plt.Line2D([], [], color=SEASON_C[2026], lw=1.2),
         plt.Line2D([], [], color=SEASON_C[2025], lw=1.2)]
    _save(fig, path, h, ["fit 2025 → count 2026", "fit 2026 → count 2025"])


# ---------------------------------------------------------------------------
# write-up (read by Daren: ASD-STE100 style)
# ---------------------------------------------------------------------------
def write_md(Q: pd.DataFrame, out: Path) -> None:
    rec = None
    path = POOLED_RECORDS / "record_division_summary.csv"
    if path.exists():
        R = pd.read_csv(path)
        r = R[(R["level"] == "division") & (R["rule"] == "gompertz-fs5")]
        rec = r.iloc[0] if len(r) else None
    L = ["# How good is the national Gompertz fit? (2025 + 2026)", ""]
    L.append("Generated by `gompertz_fit_quality.py`. It examines the fits in "
             "`gompertz.md`. There are four views, from the shape of the whole tail "
             "to the record.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| pool | N_u | QQ gap at the 99% point (s) | in-sample: share in band | in-sample: typical error | in-sample: worst ratio (count ≥ 100) | out of sample: typical error 25→26 / 26→25 | the same for a correct model | A² p (de-tied) | verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in Q.iterrows():
        L.append(f"| {r['event']} {r['sex']} | {r['N_u']:,} | {r['qq_gap_990']:+.3f}"
                 f"{'' if r['qq_in_band_990'] else ' (outside band)'} "
                 f"| {r['in_share_in_band']:.0%} | {r['in_median_abs_dev']:.1%} "
                 f"| ×{r['in_worst_ratio']:.2f} "
                 f"| {r['oos_25to26_median_abs_dev']:.1%} / {r['oos_26to25_median_abs_dev']:.1%} "
                 f"| {r['oos_null_median_abs_dev']:.1%} "
                 f"| {r['ad_pvalue_detied']:.3f} | **{r['verdict']}** |")
    L.append("")
    L.append("**Verdict rules** (tail times with a count of 10 or more):")
    L.append(f"- *good:* ≥ {GOOD['in']:.0%} of the in-sample ratios are in the 95% band, "
             f"and the out-of-sample typical error is at most {GOOD['oos'] * 100:.0f} "
             "percentage points above the error of a correct model for the same pool;")
    L.append(f"- *fair:* ≥ {FAIR['in']:.0%} and at most {FAIR['oos'] * 100:.0f} points above;")
    L.append("- *poor:* all other pools.")
    L.append("")
    L.append("**What a correct model gives** (simulated Gompertz tails, 10,000 "
             "exceedances): 96–100% of the ratios in the band, a typical error of "
             "1–2%, and a worst ratio at count ≥ 100 within approximately ±20%. "
             "'Typical error' is the median |expected ÷ actual − 1|.")
    L.append("")
    L.append("## 1. Shape above u: the QQ plot")
    L.append("")
    L.append("Sort the excesses: how far each mark is faster than u. If the model "
             "is correct, the i-th excess is near the model quantile at "
             "(i − 0.5)/N_u. The figure plots the gap (data − model) against the "
             "model quantile, so a perfect fit is the zero line. The grey band shows "
             "how large the gap is by chance. To make it, 200 samples are drawn "
             "from the fitted model, rounded to 0.01 s, cut at u and fitted again, "
             "exactly like the data. A positive gap means the real marks are further "
             "ahead of u than the model says.")
    L.append("")
    L.append("| pool | gap at 50% | 90% | 99% | 99.9% | share of points in band |")
    L.append("|---|---|---|---|---|---|")
    for _, r in Q.iterrows():
        cells = [f"{r[f'qq_gap_{k}']:+.3f}{'' if r[f'qq_in_band_{k}'] else '*'}"
                 for k in (500, 900, 990, 999)]
        L.append(f"| {r['event']} {r['sex']} | " + " | ".join(cells)
                 + f" | {r['qq_share_in_band']:.0%} |")
    L.append("")
    L.append("\\* outside the 95% band. Figures: `fit_quality_qq_m.png`, `fit_quality_qq_f.png`.")
    L.append("")
    L.append("## 2. Counts: expected ÷ actual at every time in the tail")
    L.append("")
    L.append("For each time t in the tail, compare two numbers:")
    L.append("- n·S(t): the number of athletes that the model expects at t or faster;")
    L.append("- c: the number of athletes that actually were.")
    L.append("")
    L.append("If the model is correct, n·S(t) follows Gamma(c, 1). So the ratio has a "
             "known 95% band: approximately ×0.03–×3.7 at the record, ±20% at c = 100 "
             "and ±6% at c = 1,000. The curve must stay in the band and near 1. "
             "Times have only hundredths, so many athletes have the same time. The "
             "counts include these ties, and the model is read at t + 0.005 s.")
    L.append("")
    L.append("Figures: `fit_quality_ratio_m.png`, `fit_quality_ratio_f.png`.")
    L.append("")
    L.append("## 3. The formal test")
    L.append("")
    L.append("The Anderson–Darling p-value (the ForwardStop test at the chosen u, "
             "times de-tied) is in the summary table. With thousands of exceedances, "
             "this test finds misfits that are too small to change a score. A small "
             "p tells you that the model is not exactly correct. It does not tell you "
             "how wrong it is. Sections 1, 2 and 4 measure that.")
    L.append("")
    L.append("## 4. Out of sample")
    L.append("")
    L.append("Fit 2025 alone (at the same quantile level as the stacked fit), then "
             "compare its expected counts with the counts of 2026. Then do the reverse. "
             "The 'typical error' in the summary is the median |ratio − 1| over the "
             "times with c ≥ 10.")
    L.append("")
    L.append("**The yardstick.** The column 'the same for a correct model' repeats this "
             "test on two simulated seasons. Their fast tails are drawn from the "
             "stacked fit, at the real season sizes. So the seasons have no real "
             "difference, and the error that remains is only fit noise and count "
             "noise. The amount by which the real error is larger shows how much the "
             "two seasons really differ.")
    L.append("")
    if rec is not None:
        L.append(f"**Records** (division test, rule `gompertz-fs5`, "
                 f"{int(rec['n_records'])} out-of-sample records, predictive p): "
                 f"KS p = {rec['pred_ks']:.3f}, tails {rec['pred_tails']} "
                 f"(95% range {rec['tails_95_range']}), median z = {rec['median_z1']:.2f} "
                 "(0.69 if correct). Source: "
                 "`comparisons/record_tests/record_calibration.md`, section D.")
        L.append("")
    L.append("Figures: `fit_quality_oos_m.png`, `fit_quality_oos_f.png`.")
    (out / "fit_quality.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  wrote {out / 'fit_quality.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Goodness of fit, national Gompertz.")
    ap.add_argument("--n-sim", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out = gp.out_dir()
    F = pd.read_csv(out / "gompertz_fit.csv").set_index(["event", "sex"])
    cache = {r["key"]: r for r in pd.read_csv(out / "gompertz_forwardstop.csv")
             .to_dict("records")}
    rng = np.random.default_rng(args.seed)
    rows = []
    for sex in SEXES:
        plots = {}
        for ev in EVENTS:
            print(f"  {pool_name(ev, sex)} {sex}", flush=True)
            row, plots[ev] = analyse(ev, sex, F.loc[(pool_name(ev, sex), sex)],
                                     cache, args.n_sim, rng)
            rows.append(row)
        figure_qq(plots, sex, out / f"fit_quality_qq_{sex}.png")
        figure_ratio(plots, sex, out / f"fit_quality_ratio_{sex}.png")
        figure_oos(plots, sex, out / f"fit_quality_oos_{sex}.png")
    Q = pd.DataFrame(rows)
    Q.to_csv(out / "fit_quality.csv", index=False)
    write_md(Q, out)


if __name__ == "__main__":
    main()
