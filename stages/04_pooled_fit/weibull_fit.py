"""
weibull_fit.py
==============
Fit the Weibull-type tail (stages/03_tail_fit/tail_models.py) to every pool of
one dataset, with bootstrap intervals, and write it up as a section of that
dataset's summary.md.

    python stages/04_pooled_fit/weibull_fit.py --region us --sex m      # us-2026
    python stages/04_pooled_fit/weibull_fit.py                          # northeast 2026

The model, intuition first
--------------------------
The GPD assumes the tail ends at a wall (xi < 0). The Weibull-type tail assumes
it never ends but thins out ever faster:

    P(time <= t | past the threshold) = exp( -((x - mu)/s)^theta + ((u - mu)/s)^theta ),
    x = -t,

theta is the tail weight: 2 thins out like a bell curve's tail, bigger is
lighter, and theta -> infinity is the Gompertz tail. It has no wall, and its
local GPD shape is negative at the threshold and creeps to 0 further out, which
is the slide every GPD fit in this project shows (pooled_method.md section 12).

What is reported, and why
-------------------------
theta and mu trade off along a flat ridge of the likelihood: many (theta, mu)
pairs describe the same curve over the observed range. So theta alone is
weakly identified and is reported with its interval as a caveat. What matters
-- and is stable across thresholds -- is the return period of a given time,
which is what gets compared with the GPD.

Bootstrap: resample athlete-seasons, re-derive u at the same quantile (the RULE
is fixed, not the value, as for the GPD), refit. 95% percentile intervals.

Writes, in the dataset's folder (output/northeast/<years>/ or output/national/<years>/):
    weibull_fit.csv      one row per pool
    weibull_queries.csv  one row per pool x query time
    weibull_section.md   the write-up; spliced into summary.md now, and
                         re-appended by run_all.py whenever the pools still
                         match (it checks n), so a rerun does not drop it.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import numpy as np
import pandas as pd
from scipy.stats import gamma

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import (EVENTS, dataset_dirs, dataset_name, fmt_time, load_pool,
                       parse_years, pool_name)
from paths import TAILFIT_DIR  # src/

sys.path.insert(0, str(TAILFIT_DIR))
from gpd_tail import GPDFit, exceedance_probability  # noqa: E402
from tail_models import THETA_MAX, fit_tail  # noqa: E402

Q_FIT = 0.90                                    # top 10%, as in model_compare
Q_GRID = (0.80, 0.85, 0.90, 0.95, 0.98, 0.99)   # threshold-stability check
QUERY_RANKS = (1, 5, 25, 100)                   # same ranks as the GPD queries
SECTION_START = "<!-- weibull-section:start -->"
SECTION_END = "<!-- weibull-section:end -->"


def gpd_from_summary(r: pd.Series) -> GPDFit:
    return GPDFit(u=-r["u_sec"], xi=r["xi"], sigma=r["sigma"],
                  n_exceed=int(r["N_u"]), n_total=int(r["n"]), zeta=r["zeta"])


def gpd_rp(fit: GPDFit, t: float) -> float:
    q = exceedance_probability(t, fit)
    return q["return_period"] if q["status"] == "ok" or q["prob"] == 0 else np.nan


def analyse_pool(event, sex, years, region, gpd_row, n_boot, rng):
    df, meta = load_pool(event, sex, years=years, region=region)
    t = np.sort(df["seconds"].to_numpy(dtype=float))
    x = -t
    u = np.quantile(x, Q_FIT)
    fit = fit_tail(x, u, "weibull")
    queries = [t[k - 1] for k in QUERY_RANKS if k <= t.size]

    # ---- bootstrap ------------------------------------------------------
    th_b, rp_b = [], {q: [] for q in queries}
    for _ in range(n_boot):
        xb = rng.choice(x, size=x.size, replace=True)
        try:
            fb = fit_tail(xb, np.quantile(xb, Q_FIT), "weibull")
        except Exception:
            continue
        th_b.append(fb.params["theta"])
        for q in queries:
            rp_b[q].append(float(fb.return_period(q)))
    ci = lambda v: tuple(np.percentile(v, [2.5, 97.5])) if len(v) >= 20 else (np.nan, np.nan)

    # ---- threshold stability: 1 in N for the 25th-fastest mark ----------
    bench = t[24]
    stab_w, stab_g = [], []
    for q in Q_GRID:
        uq = np.quantile(x, q)
        stab_w.append(float(fit_tail(x, uq, "weibull").return_period(bench)))
        stab_g.append(float(fit_tail(x, uq, "gpd").return_period(bench)))

    gfit = gpd_from_summary(gpd_row)
    p = fit.params
    row = {
        "event": pool_name(event, sex), "sex": sex, "n": meta["n"],
        "u_sec": fit.u_seconds, "N_u": fit.n_exceed, "zeta": fit.zeta,
        "theta": p["theta"], "theta_lo": ci(th_b)[0], "theta_hi": ci(th_b)[1],
        "theta_at_cap": p["at_theta_max"], "s": p["s"], "z": p["z"],
        "mu_seconds": p["mu_seconds"],
        "local_xi_at_u": float(fit.local_xi(np.array([fit.u]))[0]),
        "local_xi_at_record": float(fit.local_xi(np.array([x.max()]))[0]),
        "implied_gpd_xi_at_u": fit.implied_gpd_xi(fit.u),
        "fastest_s": float(t[0]), "gpd_wall_s": gpd_row["implied_wall_s"],
        "bench_s": float(bench),
        "stab_spread_weibull": max(stab_w) / min(stab_w),
        "stab_spread_gpd": max(stab_g) / min(stab_g),
        "loglik_weibull": fit.loglik,
        "loglik_gpd_same_u": fit_tail(x, u, "gpd").loglik,
        "n_boot_ok": len(th_b),
    }
    qrows = []
    for k, q in zip(QUERY_RANKS, queries):
        lo, hi = ci(rp_b[q])
        qrows.append({"event": row["event"], "sex": sex, "rank": k, "time_s": q,
                      "rp_weibull": float(fit.return_period(q)),
                      "rp_lo": lo, "rp_hi": hi,
                      "rp_gpd": gpd_rp(gfit, q),
                      # In-sample check: athletes the fit expects this fast
                      # against the k who were.
                      "pred_over_actual": t.size * float(fit.prob(q)) / k})
    return row, qrows


def _rp(v) -> str:
    if v is None or not np.isfinite(v):
        return "∞ (past the wall)" if v == np.inf else "-"
    return f"{v:,.0f}"


def section(fits: pd.DataFrame, qs: pd.DataFrame, dataset: str, n_boot: int) -> str:
    # Label every row "100m boys" / "1500m girls": with both sexes in one
    # dataset, a bare event name is ambiguous.
    lab = lambda d: d.assign(event=d["event"] + d["sex"].map({"m": " boys", "f": " girls"}))
    fits, qs = lab(fits), lab(qs)
    L = [SECTION_START, "", "## Weibull-type tail (alternative to the GPD)", ""]
    L.append(f"Written by `weibull_fit.py` on {date.today().isoformat()} "
             f"({n_boot} bootstrap resamples). Rerun it if the pools change; "
             f"`run_all.py` drops this section when the pool sizes no longer match.")
    L.append("")
    L.append("**The model.** The GPD above assumes the tail stops at a wall. The "
             "Weibull-type tail assumes it never stops but thins out ever faster: "
             "P(t or faster | past u) = exp(−((x−μ)/s)^θ + ((u−μ)/s)^θ) with "
             "x = −t. θ is the tail weight (2 is a bell curve's tail, larger is "
             "lighter, ∞ is the Gompertz tail). No wall, and its local GPD shape "
             "is negative at u and creeps to 0 further out, which is the slide the "
             "GPD fits here show. Fitted to the top "
             f"{1 - Q_FIT:.0%} of each pool. Comparison and theory: "
             "`stages/04_pooled_fit/references/pooled_method.md` §12, "
             "`_config/evt_theory.md` §3.7.")
    L.append("")
    L.append("### Fits")
    L.append("")
    L.append("| event | u | N_u | θ [95% CI] | local ξ at u → at record | Δ log-lik vs GPD (same u) | 25th-fastest: spread of 1 in N across thresholds, Weibull / GPD |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in fits.iterrows():
        th = (f"≥{THETA_MAX:.0f} (Gompertz limit)" if r["theta_at_cap"]
              else f"{r['theta']:.1f}")
        L.append(f"| {r['event']} | {fmt_time(r['u_sec'])} | {int(r['N_u']):,} "
                 f"| {th} [{r['theta_lo']:.1f}, {r['theta_hi']:.1f}] "
                 f"| {r['local_xi_at_u']:+.2f} → {r['local_xi_at_record']:+.2f} "
                 f"| {r['loglik_weibull'] - r['loglik_gpd_same_u']:+.0f} "
                 f"| {r['stab_spread_weibull']:.2f} / {r['stab_spread_gpd']:.2f} |")
    L.append("")
    L.append("### Return periods, Weibull vs GPD")
    L.append("")
    L.append("The same query times as the GPD table above (each pool's 1st, 5th, "
             "25th and 100th fastest marks). \"1 in N athlete-seasons\". The last "
             "columns are an in-sample check: athletes the Weibull fit expects at or "
             "under that time, divided by the number who were, and how surprising "
             "that is. Under a correct model the expected count z at the k-th "
             "best mark is Gamma(k, 1) -- for the record, Exp(1), whose 95% range is "
             "0.025-3.69 -- so p = GammaCDF(z) is uniform: only p below 0.025 or "
             "above 0.975 is a real misfit.")
    L.append("")
    L.append("| event | rank | time | 1 in (Weibull) [95% CI] | 1 in (GPD) | Weibull ÷ GPD | predicted / actual | p |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in qs.iterrows():
        ratio = (r["rp_weibull"] / r["rp_gpd"]
                 if np.isfinite(r["rp_gpd"]) and r["rp_gpd"] > 0 else np.nan)
        L.append(f"| {r['event']} | {int(r['rank'])} | {fmt_time(r['time_s'])} "
                 f"| {_rp(r['rp_weibull'])} [{_rp(r['rp_lo'])}, {_rp(r['rp_hi'])}] "
                 f"| {_rp(r['rp_gpd'])} | {ratio:.2f} | {r['pred_over_actual']:.2f} "
                 f"| {gamma.cdf(r['pred_over_actual'] * r['rank'], r['rank']):.3f} |")
    L.append("")

    # ---- interpretation, computed from the numbers -------------------------
    rec = qs[qs["rank"] == 1]
    lower = rec[rec["rp_weibull"] < rec["rp_gpd"]]
    cap = fits[fits["theta_at_cap"]]["event"].tolist()
    wide = fits[(fits["theta_hi"] - fits["theta_lo"]) > 10]["event"].tolist()
    stab_better = (fits["stab_spread_weibull"] < fits["stab_spread_gpd"]).sum()
    L.append("Figures: `figures/weibull_vs_gpd_<sex>.png`, both models' 1-in-N curves "
             "against the data for each event, and each model ÷ the data.")
    L.append("")
    L.append("### Reading it")
    L.append("")
    L.append(f"- **The records.** For {len(lower)} of {len(rec)} events the Weibull "
             f"calls the fastest mark *less* rare than the GPD does, by a factor of "
             f"{(lower['rp_gpd'] / lower['rp_weibull']).min():,.0f} to "
             f"{(lower['rp_gpd'] / lower['rp_weibull']).max():,.0f}"
             + ("" if len(lower) == len(rec) else
                " (" + ", ".join(f"{r['event']}: Weibull ÷ GPD {r['rp_weibull'] / r['rp_gpd']:.2f}"
                                 for _, r in rec.drop(lower.index).iterrows()) + ")")
             + f". The GPD's numbers "
             f"there are set by where its wall landed (\"at the wall\" above). The "
             f"Weibull has no wall, so its record return periods come from the shape "
             f"of the tail, not from a boundary. Their intervals are still wide: one "
             f"mark per pool is very little information.")
    deep = qs[qs["rank"] >= 25]
    r = deep["rp_weibull"] / deep["rp_gpd"]
    L.append(f"- **Below the records the two models agree** within a factor of "
             f"{np.maximum(r, 1 / r).max():.2f} at the 25th and 100th fastest marks "
             f"(Weibull ÷ GPD {r.min():.2f}–{r.max():.2f}), where both are well "
             f"supported by data.")
    # In-sample calibration against count noise: k athletes observed, roughly
    # Poisson, so a correct model's prediction usually lies within k +/- 2*sqrt(k).
    pred = qs["pred_over_actual"] * qs["rank"]
    miss = qs[(pred - qs["rank"]).abs() > 2 * np.sqrt(qs["rank"])]
    L.append("- **In-sample calibration** (last column): "
             + ("every prediction is within count noise (k ± 2√k)." if miss.empty else
                f"{len(qs) - len(miss)} of {len(qs)} predictions are within count noise "
                f"(k ± 2√k). Outside it: "
                + ", ".join(f"{m['event']} rank {int(m['rank'])} "
                            f"({m['pred_over_actual']:.2f})" for _, m in miss.iterrows())
                + ". Above 1 means the Weibull expects more athletes that fast than "
                  "there were: at those ranks it is too heavy."))
    L.append(f"- **θ is weakly identified.** "
             + (f"{', '.join(cap)} ran to the Gompertz limit (θ capped at "
                f"{THETA_MAX:.0f}); " if cap else "")
             + (f"{', '.join(wide)} have θ intervals more than 10 wide. " if wide else "")
             + "θ and μ trade off along a flat ridge: many pairs draw nearly the same "
               "curve over the observed range. So read the return periods, not θ. "
             + (f"Every θ is above 2 (lowest {fits['theta'].min():.1f}), so the tail "
                f"is *lighter* than a bell curve's, consistent with the GPD's "
                f"negative ξ." if fits["theta"].min() > 2 else
                f"θ ranges {fits['theta'].min():.1f}–{fits['theta'].max():.1f}; "
                f"below 2 the tail is heavier than a bell curve's."))
    L.append(f"- **Threshold stability.** The 25th-fastest mark's 1 in N varies less "
             f"across thresholds (top 20% to top 1%) under the Weibull than under the "
             f"GPD for {stab_better} of {len(fits)} events.")
    L.append("- **Physical meaning.** The local shape is strongly negative at u "
             "(the tail is bending hard there), and less so at the record, but it "
             "never reaches a wall. The fast end of a season's list behaves like the "
             "top of a talent distribution, not like a population pressing against a "
             "physiological limit.")
    L.append("")
    L.append(SECTION_END)
    return "\n".join(L) + "\n"


def comparison_figure(fits: pd.DataFrame, summ: pd.DataFrame, years, region,
                      sexes) -> None:
    """One figure per sex: figures/weibull_vs_gpd_<sex>.png."""
    for sex in sexes:
        _comparison_figure_one(fits, summ, years, region, sex)


def _comparison_figure_one(fits: pd.DataFrame, summ: pd.DataFrame, years,
                           region, sex: str) -> None:
    """
    Weibull vs GPD side by side, one column per pool.

    Top row: "1 in N" against time for the fastest marks. Dots are the data
    (the k-th fastest mark is run by k of n athlete-seasons, so 1 in n/k);
    the two curves are the fitted models, each drawn from its own threshold
    to just past the record. The GPD's wall is the dotted vertical line: its
    curve shoots to infinity there, which is why the two disagree most at the
    record.

    Bottom row: each model's 1 in N divided by the empirical one, at every
    mark. 1 is exact; above 1 the model calls the mark rarer than it was.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from tail_models import TailFit

    keys = [(e, sex) for e in EVENTS]
    fig, axes = plt.subplots(2, len(keys), figsize=(3.9 * len(keys), 7.4),
                             gridspec_kw={"height_ratios": [2.2, 1]}, squeeze=False)
    c_w, c_g, c_d = "#1baf7a", "#8a8984", "#2a78d6"
    fr = fits.set_index(["event", "sex"])
    for j, (event, sex) in enumerate(keys):
        name = pool_name(event, sex)
        df, _ = load_pool(event, sex, years=years, region=region)
        t = np.sort(df["seconds"].to_numpy(dtype=float))
        n = t.size
        w = fr.loc[(name, sex)]
        g = summ.loc[(name, sex)]
        wf = TailFit(model="weibull", u=-w["u_sec"], zeta=w["zeta"],
                     n_exceed=int(w["N_u"]), n_total=n,
                     params={"s": w["s"], "z": w["z"], "theta": w["theta"]})
        gf = TailFit(model="gpd", u=-g["u_sec"], zeta=g["zeta"],
                     n_exceed=int(g["N_u"]), n_total=n,
                     params={"xi": g["xi"], "sigma": g["sigma"]})

        kmax = min(2000, int(n * min(wf.zeta, gf.zeta)))     # inside both fits
        k = np.unique(np.round(np.logspace(0, np.log10(kmax), 60)).astype(int))
        emp = n / k                                          # empirical 1 in N
        top, bot = axes[0, j], axes[1, j]

        span = t[kmax - 1] - t[0]
        grid = np.linspace(t[0] - 0.08 * span, t[kmax - 1], 400)
        for fit, col, ls, lab in ((gf, c_g, "--", "GPD"), (wf, c_w, "-", "Weibull")):
            with np.errstate(divide="ignore"):
                rp = fit.return_period(grid)
            ok = np.isfinite(rp)
            top.plot(grid[ok], rp[ok], color=col, ls=ls, lw=2, label=lab)
            ratio = fit.return_period(t[k - 1]) / emp
            bot.plot(t[k - 1], ratio, color=col, ls=ls, lw=1.8)
        wall = gf.endpoint_seconds
        if wall is not None:
            top.axvline(wall, color=c_g, ls=":", lw=1.2, label="GPD wall")
        top.plot(t[k - 1], emp, "o", color=c_d, ms=3.5, label="data (n / rank)")

        top.set_yscale("log")
        top.set_title(f"{name} {'boys' if sex == 'm' else 'girls'}", fontsize=11)
        top.set_ylim(emp.min() / 2, emp.max() * 300)
        top.set_xlim(grid[0], grid[-1])
        bot.set_xlim(grid[0], grid[-1])
        bot.axhline(1, color="#0b0b0b", lw=0.8)
        bot.set_yscale("log")
        bot.set_ylim(0.2, 20)
        bot.set_xlabel("time (fast ←)", fontsize=9)
        for ax in (top, bot):
            ax.tick_params(labelsize=7)
            if t[0] >= 60:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_time))
    axes[0, 0].set_ylabel("1 in N athlete-seasons", fontsize=9)
    axes[1, 0].set_ylabel("model ÷ data", fontsize=9)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=10)
    who = "boys" if sex == "m" else "girls"
    fig.suptitle(f"Weibull vs GPD tail, {who}, {dataset_name(years, region)}: how rare "
                 f"is each mark?", fontsize=14)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    path = dataset_dirs(years, region)["out"] / "figures" / f"weibull_vs_gpd_{sex}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"  wrote {path}")


def splice(summary_md, text: str) -> None:
    """Replace the section between the markers, or append it."""
    s = summary_md.read_text(encoding="utf-8")
    if SECTION_START in s:
        a, rest = s.split(SECTION_START, 1)
        b = rest.split(SECTION_END, 1)[1] if SECTION_END in rest else ""
        s = a.rstrip("\n") + "\n\n" + text + b.lstrip("\n")
    else:
        s = s.rstrip("\n") + "\n\n" + text
    summary_md.write_text(s, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Weibull-type tail fits for one dataset.")
    ap.add_argument("--years", default="2026")
    ap.add_argument("--region", default="northeast", choices=["northeast", "us"])
    ap.add_argument("--sex", default="m,f")
    ap.add_argument("--n-boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rewrite", action="store_true",
                    help="rebuild the write-up from the saved CSVs; no refitting")
    args = ap.parse_args()
    years = parse_years(args.years)
    out = dataset_dirs(years, args.region)["out"]
    summ = pd.read_csv(out / "summary.csv").set_index(["event", "sex"])
    if args.rewrite:
        fits = pd.read_csv(out / "weibull_fit.csv")
        qs = pd.read_csv(out / "weibull_queries.csv")
        text = section(fits, qs, dataset_name(years, args.region), args.n_boot)
        (out / "weibull_section.md").write_text(text, encoding="utf-8")
        splice(out / "summary.md", text)
        comparison_figure(fits, summ, years, args.region, args.sex.split(","))
        print(f"  rewrote weibull_section.md and summary.md in {out}")
        return
    summ = pd.read_csv(out / "summary.csv").set_index(["event", "sex"])
    rng = np.random.default_rng(args.seed)

    rows, qrows = [], []
    for event in EVENTS:
        for sex in args.sex.split(","):
            print(f"  {pool_name(event, sex)} {sex} ...", flush=True)
            r, q = analyse_pool(event, sex, years, args.region,
                                summ.loc[(pool_name(event, sex), sex)],
                                args.n_boot, rng)
            rows.append(r)
            qrows.extend(q)
    fits, qs = pd.DataFrame(rows), pd.DataFrame(qrows)
    fits.to_csv(out / "weibull_fit.csv", index=False)
    qs.to_csv(out / "weibull_queries.csv", index=False)
    text = section(fits, qs, dataset_name(years, args.region), args.n_boot)
    (out / "weibull_section.md").write_text(text, encoding="utf-8")
    splice(out / "summary.md", text)
    comparison_figure(fits, summ, years, args.region, args.sex.split(","))
    print(f"  wrote {out / 'weibull_fit.csv'}, weibull_queries.csv, "
          f"weibull_section.md; updated summary.md")


if __name__ == "__main__":
    main()
