"""
run_all.py
==========
Drive the whole pooled pipeline for one dataset: every event x sex, every
figure, one summary.

    python stages/04_pooled_fit/run_all.py                     # 2026, the default
    python stages/04_pooled_fit/run_all.py --years 2025        # the other season
    python stages/04_pooled_fit/run_all.py --years 2025,2026   # both, stacked
    python stages/04_pooled_fit/run_all.py --region us --sex m # all 51 states, boys
    python stages/04_pooled_fit/run_all.py --quick    # coarse smoke test
    python stages/04_pooled_fit/run_all.py --refit    # ignore the cached thresholds

Writes, with <dataset> = 2026 | 2025 | 2025-2026 | us-2026
    stages/04_pooled_fit/output/<region>/<years>/figures/histograms/*.png
    stages/04_pooled_fit/output/<region>/<years>/figures/gpd/*.png
    stages/04_pooled_fit/output/<region>/<years>/summary.md
    stages/04_pooled_fit/output/<region>/<years>/summary.csv
    stages/04_pooled_fit/output/<region>/<years>/group_shifts.csv

compare_years.py then sets the three datasets side by side.

The summary closes with the cross-event comparison _config/open_questions.md asks
for in question 2: it is not enough for each fit to be individually valid. If
one event's tail rests on 600 exceedances and another's on 90, the second is far
noisier, and two return periods computed at very different noise floors are not
equally trustworthy even when both fits pass their own diagnostics.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import sys
from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from gpd_pooled import analyse
from plot_pooled import draw_figures
from pool_data import (EVENTS, NORTHEAST, SEXES, dataset_dirs, dataset_name,
                       fmt_time, load_pool, parse_years)
from regions import REGIONS  # src/


def summary_frame(results: list[dict]) -> pd.DataFrame:
    """One row per fit, in the order the columns are worth reading."""
    rows = []
    for r in results:
        lo, hi = r["xi_ci"]
        fastest = next((q for q in r["queries"]
                        if abs(q["time_s"] - r["fastest_s"]) < 1e-9), None)
        rows.append({
            "event": r["pool"], "sex": r["sex"],
            "dataset": r["dataset"],
            "n_states": r["n_states"],
            "n_athletes": r["n_athletes"],
            "n_multi_season": r["n_multi_season"],
            "bootstrap": r["bootstrap"],
            "n_before_fence": r["n_before_fence"],
            "n": r["n"],
            "rp_sensitivity": round(r["rp_sensitivity"], 4),
            "u_sec": round(r["u_sec"], 3),
            "N_u": r["n_exceed"],
            "zeta": round(r["zeta"], 6),
            "xi": round(r["xi"], 4),
            "xi_ci_lo": round(lo, 4) if np.isfinite(lo) else np.nan,
            "xi_ci_hi": round(hi, 4) if np.isfinite(hi) else np.nan,
            "sigma": round(r["sigma"], 4),
            "implied_wall_s": (round(r["endpoint_s"], 3)
                               if r["endpoint_s"] is not None else np.nan),
            "fastest_s": round(r["fastest_s"], 3),
            "wall_margin_s": (round(r["wall_margin_s"], 3)
                              if r["wall_margin_s"] is not None else np.nan),
            # -inf = no finite fast end (gpd_tail.endpoint_interval).
            "wall_ci_lo": (round(r["endpoint_ci"][0], 3)
                           if r.get("endpoint_ci") else np.nan),
            "wall_unbounded_frac": round(r.get("wall_unbounded_frac", np.nan), 4),
            "wall_ci_hi": (round(r["endpoint_ci"][1], 3)
                           if r.get("endpoint_ci") else np.nan),
            "rp_of_fastest": (round(fastest["return_period"])
                              if fastest and np.isfinite(fastest["return_period"])
                              else np.nan),
            "rp_identified": (not fastest.get("near_wall")) if fastest else False,
            "threshold_source": r["selection"]["source"],
            "converged": r["selection"]["any_converged"],
            "plateau": ("sliding xi -- no plateau"
                        if r["selection"]["plateau"].get("sliding")
                        else ("xi flat at "
                              f"{r['selection']['plateau']['xi_bar']:+.3f}"
                              if r["selection"]["plateau"].get("found")
                              else "none")),
            "under_collected": ",".join(r["coverage_warnings"]) or "-",
        })
    return pd.DataFrame(rows)


def cross_event_notes(df: pd.DataFrame) -> list[str]:
    """The checks that only make sense once every fit is on the table."""
    L = []

    # --- 1. are the exceedance counts in the same ballpark? -------------
    nu = df["N_u"]
    ratio = nu.max() / max(nu.min(), 1)
    L.append(f"**Exceedance counts** span {nu.min():,} to {nu.max():,} "
             f"(a factor of {ratio:.1f}).")
    if ratio > 3:
        L.append(
            "  A tail estimated from a few dozen athletes is far noisier than "
            "one estimated from several hundred, so these return periods are "
            "not equally trustworthy even where each fit passes its own "
            "diagnostics. Compare the sparsest event's confidence interval "
            "against the densest before reading anything into a difference "
            "between them.")
    else:
        L.append("  Close enough that the noise floors are comparable.")

    # --- 2. did the threshold selection actually converge? --------------
    bad = df.loc[~df["converged"], ["event", "sex"]]
    if len(bad):
        pairs = ", ".join(f"{r.event} {r.sex}" for r in bad.itertuples())
        L.append(f"**No selection method converged** for: {pairs}. Those "
                 f"thresholds are fallbacks, not selections, and the fits "
                 f"resting on them describe this dataset rather than "
                 f"estimating a tail.")
    else:
        L.append("**Threshold selection converged** on every fit.")

    # --- 2b. is there a stable regime at all? ---------------------------
    slide = df[df["plateau"] == "sliding xi -- no plateau"]
    if len(slide):
        pairs = ", ".join(f"{r.event} {r.sex}" for r in slide.itertuples())
        L.append(
            f"**The shape parameter never stabilises** for: {pairs}. xi drifts "
            f"monotonically across the entire candidate grid, which means the "
            f"Pickands-Balkema-de Haan limit is not reached anywhere in it -- "
            f"there is no threshold at which the GPD is the right shape, so no "
            f"choice of threshold rescues these fits. Widening the grid does "
            f"not help; the drift continues in both directions.")

    # --- 2c. are the headline return periods even identified? -----------
    unident = df[~df["rp_identified"]]
    if len(unident):
        pairs = ", ".join(f"{r.event} {r.sex} (1 in {r.rp_of_fastest:,.0f})"
                          for r in unident.itertuples())
        L.append(
            f"**The return period of the fastest mark is NOT identified** for: "
            f"{pairs}. Those marks sit closer to the fitted wall than the "
            f"wall's own confidence interval is wide, so with xi < 0 the "
            f"survival probability is collapsing toward zero and the number is "
            f"reporting where the endpoint landed rather than how rare the "
            f"performance is. Do not compare these across events -- that "
            f"comparison is the goal of the project, and these particular "
            f"numbers cannot serve it. Score a slightly slower benchmark "
            f"instead, where the fit is still supported by data.")

    # --- 3. is any fit being held up by one athlete? --------------------
    pinned = df[df["wall_margin_s"].notna() & (df["wall_margin_s"] < 1.0)
                & (df["N_u"] < 200)]
    if len(pinned):
        pairs = ", ".join(f"{r.event} {r.sex} ({r.wall_margin_s:+.2f} s on "
                          f"{r.N_u} exceedances)" for r in pinned.itertuples())
        L.append(f"**Implied wall within a second of the fastest athlete, on "
                 f"thin data** -- {pairs}. That is a threshold pinned by one or "
                 f"two marks rather than by the shape of a tail.")

    # A small margin on a LARGE N_u is expected rather than alarming: for
    # xi < 0 the sample maximum converges to the endpoint as n grows.
    tight = df[df["wall_margin_s"].notna() & (df["wall_margin_s"] < 1.0)
               & (df["N_u"] >= 200)]
    if len(tight):
        pairs = ", ".join(f"{r.event} {r.sex} ({r.wall_margin_s:+.2f} s)"
                          for r in tight.itertuples())
        L.append(f"**Implied walls sit close to the fastest athlete** for: "
                 f"{pairs} -- expected, not alarming. With a bounded tail the "
                 f"sample maximum converges to the endpoint as n grows, and "
                 f"these pools have tens of thousands of athletes. The wall is "
                 f"still the most fragile number the model produces; read the "
                 f"`wall_ci_*` columns, not the point estimate.")

    # --- 3b. walls the data cannot bound --------------------------------
    unb = df[np.isneginf(df["wall_ci_lo"])]
    if len(unb):
        pairs = ", ".join(f"{r.event} {r.sex} ({r.wall_unbounded_frac:.0%} of "
                          f"resamples)" for r in unb.itertuples())
        L.append(f"**No finite fast end to the wall interval** for: {pairs}. "
                 f"That share of bootstrap resamples had xi >= 0 or a wall at or "
                 f"below 0 s, i.e. no wall at all, so the data cannot rule out an "
                 f"unbounded tail. Read the point wall as meaningless here.")

    # --- 4. non-regular MLE ---------------------------------------------
    nonreg = df[df["xi"] < -0.5]
    if len(nonreg):
        pairs = ", ".join(f"{r.event} {r.sex} (xi = {r.xi:+.3f})"
                          for r in nonreg.itertuples())
        L.append(f"**xi < -0.5** for: {pairs}. Maximum likelihood is "
                 f"non-regular below that boundary, so the asymptotic standard "
                 f"errors are invalid rather than merely wide -- read the "
                 f"bootstrap interval instead, and prefer a lower threshold.")

    # --- 5. data coverage -------------------------------------------------
    holes = df[df["under_collected"] != "-"]
    if len(holes):
        pairs = ", ".join(f"{r.event} {r.sex}: {r.under_collected}"
                          for r in holes.itertuples())
        L.append(f"**Under-collected states** feed these pools -- {pairs}. "
                 f"Those pools are short of both depth and tail, so their "
                 f"return periods are biased and no amount of care in the fit "
                 f"repairs it. Rescrape before relying on them.")
    return L


def write_summary(df: pd.DataFrame, results: list[dict], path_md, path_csv):
    df.to_csv(path_csv, index=False, encoding="utf-8")

    dataset = results[0]["dataset"]
    scope = "US" if results[0]["region"] == "us" else "northeast"
    L = [f"# Pooled {dataset.removeprefix('us-')} {scope} -- GPD tail fits", ""]
    L.append("One row per event x sex. Times in seconds; `rp_of_fastest` is the "
             "return period of that pool's own fastest mark, read as "
             "\"one athlete-season in this many\".")
    L.append("")
    if len(results[0]["years"]) > 1:
        L.append(
            "**Stacked seasons.** `n` counts athlete-seasons, so return periods "
            "are in the same unit as a single-season fit. Many athletes appear "
            "in both seasons, and their two marks are not independent, so the "
            "bootstrap resamples whole athletes; the intervals below are "
            "cluster-bootstrap intervals. The threshold selectors' "
            "goodness-of-fit p-values still treat rows as independent and are "
            "somewhat optimistic.")
        L.append("")
        L.append("| event | sex | athlete-seasons | distinct athletes | in both seasons |")
        L.append("|---|---|---|---|---|")
        for _, r in df.iterrows():
            L.append(f"| {r['event']} | {r['sex']} | {r['n']:,} "
                     f"| {r['n_athletes']:,} | {r['n_multi_season']:,} |")
        L.append("")
    L.append("## Fits")
    L.append("")

    show = df.copy()
    for col in ("u_sec", "implied_wall_s", "fastest_s"):
        show[col] = show[col].map(lambda v: fmt_time(v) if pd.notna(v) else "-")
    show["wall_ci_lo"] = show["wall_ci_lo"].map(
        lambda v: "unbounded" if np.isneginf(v) else v)
    cols = ["event", "sex", "n", "u_sec", "N_u", "xi", "xi_ci_lo", "xi_ci_hi",
            "sigma", "implied_wall_s", "fastest_s", "wall_margin_s",
            "rp_of_fastest", "rp_identified", "wall_ci_lo", "wall_ci_hi",
            "plateau", "converged"]
    L.append("| " + " | ".join(cols) + " |")
    L.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, r in show.iterrows():
        L.append("| " + " | ".join(str(r[c]) for c in cols) + " |")

    L.append("")
    L.append("## Query times")
    L.append("")
    L.append("| event | sex | time | P(this fast or faster) | 1 in | 95% CI on 1 in |")
    L.append("|---|---|---|---|---|---|")
    for r in results:
        for q in r["queries"]:
            if q["status"] != "ok" or not np.isfinite(q["prob"]) or q["prob"] <= 0:
                L.append(f"| {r['pool']} | {r['sex']} | {fmt_time(q['time_s'])} "
                         f"| {q['status']} | - | - |")
                continue
            ci = q.get("rp_ci")
            ci_s = (f"{ci[0]:,.0f} - {ci[1]:,.0f}"
                    if ci and np.isfinite(ci[0]) and np.isfinite(ci[1])
                    else "unstable")
            flag = " **at the wall**" if q.get("near_wall") else ""
            L.append(f"| {r['pool']} | {r['sex']} | {fmt_time(q['time_s'])} "
                     f"| {q['prob']:.3e} | {q['return_period']:,.0f}{flag} "
                     f"| {ci_s} |")

    L.append("")
    L.append("## Denominator sensitivity")
    L.append("")
    L.append("The slow-side log-IQR fence removes rows from `n`, and every "
             "return period scales with `n` through zeta = N_u/n. "
             "`rp_sensitivity` is the factor by which the unfenced pool would "
             "change them.")
    L.append("")
    L.append("| event | sex | n before fence | n after | factor |")
    L.append("|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(f"| {r['event']} | {r['sex']} | {r['n_before_fence']:,} "
                 f"| {r['n']:,} | x{r['rp_sensitivity']:.4f} |")

    L.append("")
    L.append("## Who is in the tail")
    L.append("")
    L.append("Each state's share of the exceedances (the athletes faster than u, "
             "which are what the GPD is fitted to) against its share of the "
             "pool. Ratio > 1 means over-represented among the fast. A pool is "
             "a mixture, and this is whose tail it really is. Top 8 per pool.")
    L.append("")
    L.append("| event | sex | state: tail share (pool share, ratio) |")
    L.append("|---|---|---|")
    for r in results:
        ts = r["tail_share"].head(8)
        cells = ", ".join(f"{st} {row.share_tail:.0%} ({row.share_n:.0%}, "
                          f"x{row.ratio:.1f})" for st, row in ts.iterrows())
        L.append(f"| {r['pool']} | {r['sex']} | {cells} |")

    L.append("")
    L.append("## Cross-event checks")
    L.append("")
    for note in cross_event_notes(df):
        L.append(f"- {note}" if not note.startswith("  ") else note)

    # The Weibull-type section (weibull_fit.py) is slow to compute, so it is
    # kept in its own file and re-appended here -- but only while it still
    # describes these pools: any n that changed means the section is stale.
    sec, wcsv = path_md.parent / "weibull_section.md", path_md.parent / "weibull_fit.csv"
    if sec.exists() and wcsv.exists():
        w = pd.read_csv(wcsv).set_index(["event", "sex"])["n"]
        cur = df.set_index(["event", "sex"])["n"]
        if w.reindex(cur.index).eq(cur).all():
            L += ["", sec.read_text(encoding="utf-8").rstrip("\n")]
        else:
            print("  weibull_section.md is stale (pool sizes changed); rerun "
                  "weibull_fit.py to restore it")

    path_md.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the whole pooled pipeline.")
    ap.add_argument("--years", default="2026",
                    help="season(s): 2026, 2025, or 2025,2026 (stacked)")
    ap.add_argument("--region", default="northeast", choices=["northeast", "us"])
    ap.add_argument("--sex", default="m,f", help="m, f, or m,f")
    ap.add_argument("--states", default=None,
                    help="comma-separated subset of the region (default: all of it)")
    ap.add_argument("--q-lo", type=float, default=0.80)
    ap.add_argument("--q-hi", type=float, default=0.995)
    ap.add_argument("--n-cand", type=int, default=18)
    ap.add_argument("--n-sim", type=int, default=199)
    ap.add_argument("--n-boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--refit", action="store_true")
    ap.add_argument("--skip-plots", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.n_sim, args.n_cand, args.n_boot = 49, 10, 100

    years = parse_years(args.years)
    region = args.region
    sexes = tuple(s for s in args.sex.split(",") if s)
    states = (tuple(s.strip().upper() for s in args.states.split(",") if s.strip())
              if args.states else tuple(REGIONS[region]))
    dirs = dataset_dirs(years, region)
    HIST_DIR, OUT_DIR = dirs["hist"], dirs["out"]
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- figures -------------------------------------------------------
    if not args.skip_plots:
        print("=" * 74)
        print(f"  HISTOGRAMS  --  {dataset_name(years, region)}")
        print("=" * 74)
        pools = {(e, s): load_pool(e, s, states=states, years=years,
                                   region=region)
                 for e in EVENTS for s in sexes}
        tab = draw_figures(pools, states, years, region, args.dpi)
        if not tab.empty:
            print()
            print(f"  {'source':<14}{'sex':>4}{'pairs':>7}{'factor':>10}"
                  f"{'median resid':>14}{'implied':>10}")
            for _, r in tab.iterrows():
                print(f"  {r['source']:<14}{r['sex']:>4}{int(r['n_pairs']):>7}"
                      f"{r['factor']:>10.5f}{r['median_resid_s']:>13.2f}s"
                      f"{r['implied_factor']:>10.5f}")

    # ---- fits ----------------------------------------------------------
    results = []
    for event in EVENTS:
        for sex in sexes:
            print()
            results.append(analyse(
                event, sex, states=states, q_lo=args.q_lo, q_hi=args.q_hi,
                n_cand=args.n_cand, n_sim=args.n_sim, n_boot=args.n_boot,
                seed=args.seed, refit=args.refit,
                make_plot=not args.skip_plots, years=years, region=region))

    df = summary_frame(results)
    write_summary(df, results, OUT_DIR / "summary.md", OUT_DIR / "summary.csv")

    print()
    print("=" * 74)
    print("  CROSS-EVENT CHECKS")
    print("=" * 74)
    for note in cross_event_notes(df):
        print("  " + note.replace("**", ""))
    print()
    print(f"  wrote {OUT_DIR / 'summary.md'}")
    print(f"  wrote {OUT_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
