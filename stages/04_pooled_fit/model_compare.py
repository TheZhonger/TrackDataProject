"""
model_compare.py
================
Which tail family describes the pooled data: the GPD, or a light but unbounded
tail (exponential, Weibull-type, Gompertz)? stages/03_tail_fit/tail_models.py
has the models; this script runs three tests on the pooled northeast seasons
(2025, 2026) and the national boys pool (us-2026).

Why the GPD is on trial (pooled_method.md section 10): its shape xi slides
toward 0 as the threshold rises, in every pool and season. That is what a
GPD does when the true tail is light but unbounded and is only seen at finite
thresholds. A model that is the right FAMILY should not need a threshold to
be "high enough" -- so:

1. In-sample fit at one common threshold (the top 10% of each pool), by AIC.
   Every model gets the same exceedances, so the comparison is about shape,
   not about threshold choice.

2. Threshold stability. Refit every model across thresholds from the top 20%
   to the top 1% and score one fixed benchmark (the pool's 25th-fastest mark)
   each time. A model that is the right family returns about the same "1 in N"
   whatever the threshold; a model that is only an asymptote drifts. The
   spread is reported as max/min of N across the grid.

3. Out of sample, season to season (northeast only; the only pools with two
   seasons). Fit on 2025 at its threshold, then score 2026's marks above that
   same threshold (in seconds) by their log density under each fit -- and the
   other way round. This is the test in-sample goodness-of-fit cannot be: the
   Anderson-Darling test is power-saturated at these sizes and rejects every
   model. A GPD with a wall gives density 0 (log score -inf) to any mark past
   its wall; those are counted rather than averaged.
   Calibration rides along: the predicted number of next-season athletes at
   or under that season's k-th fastest mark, against k.

Plus a figure per dataset: the observed GPD xi sweep against the sweep each
model, fitted once at the lowest threshold, implies (TailFit.implied_gpd_xi).
If a model's curve runs through the observed points, the slide is explained.

Writes output/comparisons/tail_models/ : model_comparison.md, three CSVs, three PNGs.

    python stages/04_pooled_fit/model_compare.py
"""

from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import EVENTS, SEXES, fmt_time, load_pool, pool_name
from paths import POOLED_MODELS, TAILFIT_DIR  # src/

sys.path.insert(0, str(TAILFIT_DIR))
from tail_models import MODELS, fit_tail  # noqa: E402

Q_COMMON = 0.90                               # common threshold: top 10%
Q_GRID = (0.80, 0.85, 0.90, 0.95, 0.98, 0.99)
Q_SWEEP = np.linspace(0.80, 0.995, 14)        # for the overlay figure
BENCH_RANK = 25
CAL_RANKS = (1, 5, 25, 100)

# Fixed colour and line style per model, shared by every figure.
STYLE = {"gpd": ("#8a8984", "--"), "gompertz": ("#eb6834", "-"),
         "weibull": ("#1baf7a", "-"), "exponential": ("#52514e", ":")}

DATASETS = {                                   # name -> (years, region, sexes)
    "2026": ((2026,), "northeast", SEXES),
    "2025": ((2025,), "northeast", SEXES),
    "us-2026": ((2026,), "us", ("m",)),
}


def pools():
    """(dataset, event, sex) -> seconds array, for every pool used here."""
    out = {}
    for name, (years, region, sexes) in DATASETS.items():
        for event in EVENTS:
            for sex in sexes:
                df, _ = load_pool(event, sex, years=years, region=region)
                out[(name, event, sex)] = np.sort(df["seconds"].to_numpy(dtype=float))
    return out


def in_sample_and_stability(P) -> tuple[pd.DataFrame, pd.DataFrame]:
    fits, stab = [], []
    for (name, event, sex), t in P.items():
        x = -t
        bench = t[BENCH_RANK - 1]
        u = np.quantile(x, Q_COMMON)
        for m in MODELS:
            f = fit_tail(x, u, m)
            fits.append({"dataset": name, "event": pool_name(event, sex), "sex": sex,
                         "model": m, "N_u": f.n_exceed, "loglik": f.loglik,
                         "aic": 2 * f.k - 2 * f.loglik,
                         "theta": f.params.get("theta", np.nan),
                         "xi": f.params.get("xi", np.nan)})
        for q in Q_GRID:
            uq = np.quantile(x, q)
            for m in MODELS:
                f = fit_tail(x, uq, m)
                stab.append({"dataset": name, "event": pool_name(event, sex),
                             "sex": sex, "model": m, "q": q,
                             "bench_s": bench,
                             "rp": float(f.return_period(bench))})
    fits = pd.DataFrame(fits)
    keys = ["dataset", "event", "sex"]
    gpd_aic = fits[fits["model"] == "gpd"].set_index(keys)["aic"]
    fits["d_aic_vs_gpd"] = fits["aic"].to_numpy() - gpd_aic.reindex(
        pd.MultiIndex.from_frame(fits[keys])).to_numpy()
    return fits, pd.DataFrame(stab)


def out_of_sample(P) -> pd.DataFrame:
    rows = []
    for event in EVENTS:
        for sex in SEXES:
            for a, b in (("2025", "2026"), ("2026", "2025")):
                ta, tb = P[(a, event, sex)], P[(b, event, sex)]
                xa, xb = -ta, -tb
                u = np.quantile(xa, Q_COMMON)        # fitted season's threshold
                yb = xb[xb > u] - u                  # next season's excesses over it
                ls = {}
                for m in MODELS:
                    f = fit_tail(xa, u, m)
                    lp = f.logpdf_excess(yb)
                    ls[m] = lp
                    for k in CAL_RANKS:
                        pred = tb.size * float(f.prob(tb[k - 1]))
                        rows.append({"fit": a, "scored": b,
                                     "event": pool_name(event, sex), "sex": sex,
                                     "model": m, "kind": "calibration", "k": k,
                                     "value": pred / k})
                # Paired log-score differences against the GPD, over the marks
                # every model gives positive density to; marks past the GPD wall
                # are counted separately (they score -inf under the GPD alone).
                finite = np.all([np.isfinite(v) for v in ls.values()], axis=0)
                n_beyond = int((~np.isfinite(ls["gpd"])).sum())
                for m in MODELS:
                    d = ls[m][finite] - ls["gpd"][finite]
                    rows.append({"fit": a, "scored": b,
                                 "event": pool_name(event, sex), "sex": sex,
                                 "model": m, "kind": "logscore",
                                 "n_scored": int(yb.size), "n_beyond_gpd_wall": n_beyond,
                                 "mean_logscore": float(ls[m][finite].mean()),
                                 "diff_vs_gpd": float(d.mean()),
                                 "se_diff": float(d.std(ddof=1) / np.sqrt(d.size))
                                 if m != "gpd" else 0.0})
    return pd.DataFrame(rows)


def overlay_figure(P, name: str) -> None:
    """Observed GPD xi sweep vs the sweep each model implies."""
    keys = [k for k in P if k[0] == name]
    ncols = 5 if len(keys) > 5 else len(keys)
    nrows = int(np.ceil(len(keys) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.6 * ncols, 3.0 * nrows),
                             squeeze=False)
    for ax, key in zip(axes.flatten(), keys):
        _, event, sex = key
        x = -P[key]
        us = np.quantile(x, Q_SWEEP)
        obs = []
        for u in us:
            f = fit_tail(x, u, "gpd")
            obs.append(f.params["xi"])
        ax.plot(Q_SWEEP, obs, "o", color="#2a78d6", ms=4, label="observed GPD xi")
        for m in ("gompertz", "weibull", "gpd"):
            f0 = fit_tail(x, us[0], m)
            ax.plot(Q_SWEEP, [f0.implied_gpd_xi(u) for u in us],
                    color=STYLE[m][0], ls=STYLE[m][1], lw=1.6, label=f"{m}, fit at top 20%")
        ax.axhline(0, color="#d8d7d2", lw=0.8)
        ax.set_title(f"{pool_name(event, sex)} {'boys' if sex == 'm' else 'girls'}",
                     fontsize=10)
        ax.set_xlabel("threshold quantile", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes.flatten()[len(keys):]:
        ax.axis("off")
    axes[0, 0].set_ylabel("GPD shape xi", fontsize=9)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.suptitle(f"{name}: does a model fitted once at the top 20% predict the "
                 f"slide in xi?", fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    path = POOLED_MODELS / f"xi_overlay_{name}.png"
    fig.savefig(path, dpi=130, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"  wrote {path}")


def predicted_vs_actual_figure(P, fit_ds: str, score_ds: str) -> None:
    """
    Predicted vs actual counts at the top of a season, one panel per pool.

    For the k-th fastest mark t_k of `score_ds`, the ACTUAL count is k (k
    athletes ran t_k or faster) and the PREDICTED count is n * P(time <= t_k)
    under a model fitted on `fit_ds` at its top-10% threshold -- the number of
    athletes the model expected that fast. On the 45-degree line the model is
    right. Below it, the model thinks the top end is rarer than it is.

    Counts are roughly Poisson, so +/- 2*sqrt(k) around the diagonal is the
    band where a correct model's points would usually fall. A GPD that puts a
    mark past its wall predicts 0, which a log axis cannot show; those marks
    are drawn as x's on the bottom edge and counted in the panel title.
    """
    keys = [(fit_ds, e, s) for (d, e, s) in P if d == fit_ds and (score_ds, e, s) in P]
    ncols = 5 if len(keys) > 5 else len(keys)
    nrows = int(np.ceil(len(keys) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.6 * ncols, 3.4 * nrows),
                             squeeze=False)
    for ax, (_, event, sex) in zip(axes.flatten(), keys):
        ta, tb = P[(fit_ds, event, sex)], P[(score_ds, event, sex)]
        u = np.quantile(-ta, Q_COMMON)
        n_above = int((-tb > u).sum())
        k = np.arange(1, min(300, n_above) + 1)
        lo_y = 0.3
        # Noise band and the line of perfect prediction.
        ax.fill_between(k, np.maximum(k - 2 * np.sqrt(k), lo_y), k + 2 * np.sqrt(k),
                        color="#d8d7d2", alpha=0.6, lw=0, label="±2√k (count noise)")
        ax.plot(k, k, color="#0b0b0b", lw=0.8, label="perfect prediction")
        n_wall = 0
        for m in ("gpd", "weibull", "gompertz"):
            f = fit_tail(-ta, u, m)
            pred = tb.size * f.prob(tb[k - 1])
            ok = pred > 0
            ax.plot(k[ok], pred[ok], color=STYLE[m][0], ls=STYLE[m][1],
                    lw=1.8 if m != "gpd" else 1.4, label=m)
            if m == "gpd" and (~ok).any():
                n_wall = int((~ok).sum())
                ax.plot(k[~ok], np.full(n_wall, lo_y), "x", color=STYLE[m][0],
                        ms=7, mew=1.6, clip_on=False, label="GPD: past its wall")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(lo_y, k[-1] * 3)
        wall = f"   ({n_wall} past GPD wall)" if n_wall else ""
        ax.set_title(f"{pool_name(event, sex)} {'boys' if sex == 'm' else 'girls'}{wall}",
                     fontsize=10)
        ax.set_xlabel(f"actual: rank k in {score_ds}", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes.flatten()[len(keys):]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("predicted athletes this fast", fontsize=8)
    # Collect legend entries from every panel: the wall marker exists only in some.
    seen = {}
    for ax in axes.flatten():
        for h, l in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(l, h)
    fig.legend(seen.values(), seen.keys(), loc="lower center", ncol=6,
               frameon=False, fontsize=9)
    kind = ("in-sample (fit and scored on the same season)" if fit_ds == score_ds
            else f"out of sample (fit on {fit_ds}, scored on {score_ds})")
    fig.suptitle(f"Predicted vs actual athletes at the top: {kind}", fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    name = fit_ds if fit_ds == score_ds else f"{fit_ds}_to_{score_ds}"
    path = POOLED_MODELS / f"predicted_vs_actual_{name}.png"
    fig.savefig(path, dpi=130, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"  wrote {path}")


def write(fits, stab, oos) -> None:
    L = ["# Tail-model comparison: GPD vs light unbounded tails", ""]
    L.append("Generated by `model_compare.py`. Models in "
             "`stages/03_tail_fit/tail_models.py`. Pools: northeast 2025 and 2026 "
             "(both sexes), national boys 2026.")
    L.append("")

    L.append(f"## 1. In-sample, common threshold (top {1 - Q_COMMON:.0%})")
    L.append("")
    L.append("ΔAIC against the GPD: negative is better. Each model sees the same "
             "exceedances. Weibull θ ≥ 50 means the fit ran to its Gompertz limit.")
    L.append("")
    L.append("| dataset | pool | sex | N_u | ΔAIC exponential | ΔAIC weibull (θ) | ΔAIC gompertz | best |")
    L.append("|---|---|---|---|---|---|---|---|")
    for (ds, ev, sx), g in fits.groupby(["dataset", "event", "sex"], sort=False):
        d = g.set_index("model")
        best = d["aic"].idxmin()
        L.append(f"| {ds} | {ev} | {sx} | {int(d.loc['gpd', 'N_u']):,} "
                 f"| {d.loc['exponential', 'd_aic_vs_gpd']:+.0f} "
                 f"| {d.loc['weibull', 'd_aic_vs_gpd']:+.0f} ({d.loc['weibull', 'theta']:.1f}) "
                 f"| {d.loc['gompertz', 'd_aic_vs_gpd']:+.0f} | {best} |")
    wins = fits.loc[fits.groupby(["dataset", "event", "sex"])["aic"].idxmin(), "model"]
    L.append("")
    L.append(f"Best by AIC: {', '.join(f'{m} {n}' for m, n in wins.value_counts().items())} "
             f"(of {len(wins)} pools).")
    L.append("")

    L.append(f"## 2. Threshold stability: 1 in N for the pool's {BENCH_RANK}th-fastest mark")
    L.append("")
    L.append(f"Each model refitted at thresholds from the top {1 - Q_GRID[0]:.0%} to the "
             f"top {1 - Q_GRID[-1]:.0%}. The spread is max/min of N across those "
             f"fits: 1.0 means the answer does not depend on the threshold.")
    L.append("")
    L.append("| dataset | pool | sex | benchmark | spread gpd | spread weibull | spread gompertz | spread exponential |")
    L.append("|---|---|---|---|---|---|---|---|")
    spreads = []
    for (ds, ev, sx), g in stab.groupby(["dataset", "event", "sex"], sort=False):
        s = {m: g.loc[g["model"] == m, "rp"].max() / g.loc[g["model"] == m, "rp"].min()
             for m in MODELS}
        spreads.append(s)
        L.append(f"| {ds} | {ev} | {sx} | {fmt_time(g['bench_s'].iloc[0])} "
                 f"| {s['gpd']:.2f} | {s['weibull']:.2f} | {s['gompertz']:.2f} "
                 f"| {s['exponential']:.2f} |")
    sp = pd.DataFrame(spreads)
    L.append("")
    L.append("Median spread: " + ", ".join(f"{m} {sp[m].median():.2f}" for m in MODELS) + ".")
    L.append("")

    L.append("## 3. Out of sample: fit one season, score the other")
    L.append("")
    L.append("Mean log density of the other season's marks above the fitted "
             "season's threshold, minus the GPD's (positive = better than the "
             "GPD), with its standard error. `past wall` counts marks the GPD "
             "calls impossible (log score −∞), which are left out of the means.")
    L.append("")
    L.append("| fit → scored | pool | sex | marks | past GPD wall | weibull − gpd | gompertz − gpd | exponential − gpd |")
    L.append("|---|---|---|---|---|---|---|---|")
    ls = oos[oos["kind"] == "logscore"]
    for (fa, sb, ev, sx), g in ls.groupby(["fit", "scored", "event", "sex"], sort=False):
        d = g.set_index("model")
        cell = lambda m: f"{d.loc[m, 'diff_vs_gpd']:+.3f} ± {d.loc[m, 'se_diff']:.3f}"
        L.append(f"| {fa} → {sb} | {ev} | {sx} | {int(d.loc['gpd', 'n_scored']):,} "
                 f"| {int(d.loc['gpd', 'n_beyond_gpd_wall'])} | {cell('weibull')} "
                 f"| {cell('gompertz')} | {cell('exponential')} |")
    tot = {m: (ls[ls["model"] == m]["diff_vs_gpd"] > 0).sum() for m in MODELS if m != "gpd"}
    L.append("")
    L.append(f"Beats the GPD out of sample in: "
             + ", ".join(f"{m} {n} of {ls['model'].eq(m).sum()}" for m, n in tot.items())
             + f" season-pairs. Marks past the GPD's wall: "
             f"{int(ls[ls['model'] == 'gpd']['n_beyond_gpd_wall'].sum())} in total.")
    L.append("")
    L.append("### Calibration: predicted / observed athletes at or under the other "
             "season's k-th fastest mark")
    L.append("")
    L.append("1.00 is perfect. Below 1 the model thinks the top end is rarer than it "
             "turned out; 0 means the GPD put the mark past its wall.")
    L.append("")
    cal = oos[oos["kind"] == "calibration"]
    L.append("| model | " + " | ".join(f"k = {k} (median)" for k in CAL_RANKS) + " |")
    L.append("|---|" + "---|" * len(CAL_RANKS))
    for m in MODELS:
        g = cal[cal["model"] == m]
        L.append(f"| {m} | " + " | ".join(
            f"{g.loc[g['k'] == k, 'value'].median():.2f}" for k in CAL_RANKS) + " |")
    L.append("")
    L.append("Figures: `xi_overlay_<dataset>.png`, observed GPD ξ sweep against "
             "the sweep each model implies when fitted once at the top 20%. "
             "`predicted_vs_actual_2025_to_2026.png` (and `_2026_to_2025`): for each "
             "of the scored season's top 300 marks, the number of athletes the "
             "fitted model expected that fast against the number who were (the "
             "rank). On the diagonal is right; below it, the model thinks the top "
             "is rarer than it is; x's on the bottom edge are marks past the GPD's "
             "wall. `predicted_vs_actual_us-2026.png` is the same for the national "
             "pool, in-sample only (one national season so far).")

    (POOLED_MODELS / "model_comparison.md").write_text("\n".join(L) + "\n",
                                                       encoding="utf-8")
    fits.to_csv(POOLED_MODELS / "in_sample.csv", index=False)
    stab.to_csv(POOLED_MODELS / "threshold_stability.csv", index=False)
    oos.to_csv(POOLED_MODELS / "out_of_sample.csv", index=False)
    print(f"  wrote {POOLED_MODELS / 'model_comparison.md'}")


def main() -> None:
    POOLED_MODELS.mkdir(parents=True, exist_ok=True)
    P = pools()
    fits, stab = in_sample_and_stability(P)
    oos = out_of_sample(P)
    write(fits, stab, oos)
    for name in DATASETS:
        overlay_figure(P, name)
    for fit_ds, score_ds in (("2025", "2026"), ("2026", "2025"), ("us-2026", "us-2026")):
        predicted_vs_actual_figure(P, fit_ds, score_ds)


if __name__ == "__main__":
    main()
