"""
compare_years.py
================
Set the pooled fits for 2026, 2025 and the two seasons stacked (2025-2026) side
by side, and ask the three questions a second season can answer.

1. Does the shape REPLICATE?
   2025 is an independent re-run of the same experiment: same nine states, same
   events, a different set of races (and two thirds different athletes). If
   2026's sliding xi is a property of the event, 2025 slides too, at similar
   values. If it was a quirk of one season, 2025 disagrees.

2. Do the seasons agree at the SAME bar?
   Each season's selector picks its own threshold u, and in 9 of 10 pools xi
   drifts with u (pooled_method.md section 7). So xi_2025 and xi_2026 at their
   own thresholds mix two effects: a real difference between seasons, and the
   two fits sitting at different heights on the slide. Refitting both seasons
   at one threshold, fixed in seconds, removes the second effect. The 2026
   threshold is used as the common bar.

3. What did stacking buy?
   Twice the athlete-seasons, but not twice the information: a third of the
   tail is the same people twice. The ratio of the stacked xi interval's width
   to 2026's says how much sharper the estimate got. Independent data would
   give sqrt(1/2) = 0.71; repeat athletes push it toward 1.

Reads  output/northeast/<years>/summary.csv for the three datasets (run_all.py first).
Writes output/comparisons/northeast_seasons/year_comparison.{md,csv}.

    python stages/04_pooled_fit/compare_years.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import (EVENTS, SEXES, dataset_dirs, fmt_time, load_pool,
                       pool_name)
from paths import POOLED_SEASONS, TAILFIT_DIR  # src/

sys.path.insert(0, str(TAILFIT_DIR))
from gpd_tail import GPDFit, exceedance_probability, fit_gpd  # noqa: E402

DATASETS = {"2026": (2026,), "2025": (2025,), "2025-2026": (2025, 2026)}

# Benchmark for the return-period comparison: this rank in the STACKED pool,
# i.e. roughly the 25th-fastest athlete of a single season. Deep enough into
# the tail to be a real benchmark, far enough from the record that no fit is
# reporting its own wall (the record itself is unidentified in every pool).
BENCH_RANK = 50


def load_summaries() -> dict[str, pd.DataFrame]:
    out = {}
    for name, years in DATASETS.items():
        path = dataset_dirs(years)["out"] / "summary.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}: run run_all.py --years "
                             f"{','.join(map(str, years))} first")
        out[name] = pd.read_csv(path).set_index(["event", "sex"])
    return out


def fit_from_row(r: pd.Series) -> GPDFit:
    """Rebuild a fitted tail from its summary row (x = -seconds internally)."""
    return GPDFit(u=-r["u_sec"], xi=r["xi"], sigma=r["sigma"],
                  n_exceed=int(r["N_u"]), n_total=int(r["n"]), zeta=r["zeta"])


def half_width(r: pd.Series) -> float:
    return (r["xi_ci_hi"] - r["xi_ci_lo"]) / 2


def compare() -> pd.DataFrame:
    S = load_summaries()
    rows = []
    for event in EVENTS:
        for sex in SEXES:
            key = (pool_name(event, sex), sex)
            r26, r25, rst = S["2026"].loc[key], S["2025"].loc[key], S["2025-2026"].loc[key]

            # --- question 2: both seasons at 2026's threshold ------------
            # Plain MLE, no bootstrap: the textbook SE (1+xi)/sqrt(N_u) is
            # printed alongside, knowing it understated the bootstrap width by
            # 1.8-3.3x in 2026. Read the gap against that, not against zero.
            u_common = -r26["u_sec"]
            matched = {}
            for name in ("2025", "2026"):
                df, _ = load_pool(event, sex, years=DATASETS[name])
                f = fit_gpd(-df["seconds"].to_numpy(dtype=float), u_common)
                matched[name] = (f.xi, abs(1 + f.xi) / np.sqrt(f.n_exceed),
                                 f.n_exceed)

            # --- benchmark: one fixed time scored by all three fits ------
            st, _ = load_pool(event, sex, years=DATASETS["2025-2026"])
            bench = float(np.sort(st["seconds"].to_numpy(dtype=float))[BENCH_RANK - 1])
            rp = {}
            for name, r in (("2026", r26), ("2025", r25), ("2025-2026", rst)):
                q = exceedance_probability(bench, fit_from_row(r))
                rp[name] = q["return_period"] if q["status"] == "ok" else np.nan

            d = r25["xi"] - r26["xi"]
            tol = np.hypot(half_width(r25), half_width(r26))
            rows.append({
                "event": key[0], "sex": sex,
                "n_2026": int(r26["n"]), "n_2025": int(r25["n"]),
                "n_stacked": int(rst["n"]),
                "athletes_stacked": int(rst["n_athletes"]),
                "multi_season": int(rst["n_multi_season"]),
                "fastest_2026": r26["fastest_s"], "fastest_2025": r25["fastest_s"],
                "u_2026": r26["u_sec"], "u_2025": r25["u_sec"], "u_stacked": rst["u_sec"],
                "xi_2026": r26["xi"], "xi_2026_lo": r26["xi_ci_lo"], "xi_2026_hi": r26["xi_ci_hi"],
                "xi_2025": r25["xi"], "xi_2025_lo": r25["xi_ci_lo"], "xi_2025_hi": r25["xi_ci_hi"],
                "xi_stacked": rst["xi"], "xi_stacked_lo": rst["xi_ci_lo"],
                "xi_stacked_hi": rst["xi_ci_hi"],
                "plateau_2026": r26["plateau"], "plateau_2025": r25["plateau"],
                "plateau_stacked": rst["plateau"],
                "source_2026": r26["threshold_source"], "source_2025": r25["threshold_source"],
                "source_stacked": rst["threshold_source"],
                # Seasons consistent at their own thresholds? The difference
                # against the two half-widths combined in quadrature: about a
                # 5% test if the seasons were independent. They share a third
                # of their athletes, which makes the difference LESS variable
                # than that, so this errs toward calling them consistent.
                "dxi_own_u": d, "dxi_tolerance": tol, "consistent": abs(d) <= tol,
                "xi_2025_at_u2026": matched["2025"][0], "se_2025_at_u2026": matched["2025"][1],
                "nu_2025_at_u2026": matched["2025"][2],
                "xi_2026_at_u2026": matched["2026"][0], "se_2026_at_u2026": matched["2026"][1],
                "nu_2026_at_u2026": matched["2026"][2],
                "width_ratio_stacked_vs_2026": half_width(rst) / half_width(r26),
                "bench_s": bench,
                "rp_bench_2026": rp["2026"], "rp_bench_2025": rp["2025"],
                "rp_bench_stacked": rp["2025-2026"],
            })
    return pd.DataFrame(rows)


def _ci(r, tag) -> str:
    return f"{r[f'xi_{tag}']:+.3f} [{r[f'xi_{tag}_lo']:+.3f}, {r[f'xi_{tag}_hi']:+.3f}]"


def _plateau(text: str) -> str:
    return "slides" if text.startswith("sliding") else text.replace("xi flat at ", "flat ")


def _rp(v) -> str:
    return f"{v:,.0f}" if np.isfinite(v) else "-"


def write(df: pd.DataFrame) -> None:
    L = ["# Pooled northeast: 2026 vs 2025 vs both seasons stacked", ""]
    L.append("Generated by `compare_years.py` from the three `summary.csv` files. "
             "xi intervals are 95% bootstrap intervals; the stacked dataset's "
             "resample whole athletes. Times in seconds.")
    L.append("")

    L.append("## 1. Shape by season")
    L.append("")
    L.append("| pool | sex | xi 2026 | xi 2025 | xi stacked | shape 2026 / 2025 / stacked | consistent? |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        shape = " / ".join(_plateau(r[f"plateau_{t}"]) for t in ("2026", "2025", "stacked"))
        ok = ("yes" if r["consistent"] else "**no**") + f" (dxi {r['dxi_own_u']:+.3f}, tol {r['dxi_tolerance']:.3f})"
        L.append(f"| {r['event']} | {r['sex']} | {_ci(r, '2026')} | {_ci(r, '2025')} "
                 f"| {_ci(r, 'stacked')} | {shape} | {ok} |")
    L.append("")
    L.append("`consistent` compares the two seasons' point estimates at their "
             "own thresholds against both half-widths combined in quadrature. "
             "Because the seasons share athletes, it leans toward saying yes.")
    L.append("")

    L.append("## 2. Both seasons at the same threshold (2026's u)")
    L.append("")
    L.append("| pool | sex | u (s) | u 2025 own | xi 2026 | xi 2025 | N_u 2026 / 2025 | gap / textbook SE |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        gap = r["xi_2025_at_u2026"] - r["xi_2026_at_u2026"]
        se = np.hypot(r["se_2025_at_u2026"], r["se_2026_at_u2026"])
        L.append(f"| {r['event']} | {r['sex']} | {fmt_time(r['u_2026'])} | {fmt_time(r['u_2025'])} "
                 f"| {r['xi_2026_at_u2026']:+.3f} | {r['xi_2025_at_u2026']:+.3f} "
                 f"| {int(r['nu_2026_at_u2026']):,} / {int(r['nu_2025_at_u2026']):,} "
                 f"| {gap / se:+.1f} |")
    L.append("")
    L.append("The last column is the gap in textbook standard errors. The "
             "bootstrap was 1.8-3.3x wider than the textbook SE in 2026, so "
             "|gap/SE| below about 4 is within noise.")
    L.append("")

    L.append(f"## 3. One benchmark time, three fits")
    L.append("")
    L.append(f"The benchmark is the stacked pool's {BENCH_RANK}th-fastest mark "
             f"(about the 25th-fastest athlete of one season). Each fit scores it "
             f"as \"1 in N athlete-seasons\".")
    L.append("")
    L.append("| pool | sex | benchmark | 1 in (2026) | 1 in (2025) | 1 in (stacked) | xi width, stacked / 2026 | athletes in both seasons |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(f"| {r['event']} | {r['sex']} | {fmt_time(r['bench_s'])} "
                 f"| {_rp(r['rp_bench_2026'])} | {_rp(r['rp_bench_2025'])} "
                 f"| {_rp(r['rp_bench_stacked'])} "
                 f"| {r['width_ratio_stacked_vs_2026']:.2f} "
                 f"| {r['multi_season']:,} of {r['athletes_stacked']:,} |")
    L.append("")
    L.append("Width ratio: independent data doubling n would give 0.71. A ratio "
             "near 1, or above it, means the extra season added little "
             "independent information about the shape, or that the stacked "
             "fit chose a different threshold.")

    POOLED_SEASONS.mkdir(parents=True, exist_ok=True)
    out = POOLED_SEASONS / "year_comparison.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    df.to_csv(POOLED_SEASONS / "year_comparison.csv", index=False, encoding="utf-8")
    print(f"  wrote {out}")
    print(f"  wrote {POOLED_SEASONS / 'year_comparison.csv'}")


if __name__ == "__main__":
    write(compare())
