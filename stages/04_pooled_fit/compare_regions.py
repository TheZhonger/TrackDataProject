"""
compare_regions.py
==================
Set the northeast-nine boys fits (2026) beside the all-51-state boys fits
(us-2026), and ask what the wider population changes.

1. Does the shape change?
   The national pool is a 51-component mixture with five to seven times the
   athletes. If the slide in xi came from the northeast being too small, the
   national pool would plateau. If it is the penultimate behaviour of a light,
   normal-like tail (pooled_method.md section 10), it slides too.

2. Same bar, both pools.
   As in compare_years.py: refit the national pool at the NORTHEAST's
   threshold (fixed in seconds), so the two xi values are read at the same
   height on the slide.

3. Is the northeast representative at the top?
   A return period is a probability per athlete-season, so if the northeast
   were a representative slice of the country, a given time would have the
   SAME return period in both pools. The ratio rp_US / rp_NE at a fixed
   benchmark says how the northeast's top end compares: above 1 means the time
   is rarer nationally, i.e. the northeast has relatively more athletes that
   fast. The empirical fractions (no model) are shown beside the fitted ones.

Reads  output/northeast/2026/summary.csv and output/national/2026/summary.csv (run_all.py first).
Writes output/comparisons/northeast_vs_national/region_comparison.{md,csv}.

    python stages/04_pooled_fit/compare_regions.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import EVENTS, dataset_dirs, fmt_time, load_pool, pool_name
from paths import POOLED_REGIONS, TAILFIT_DIR  # src/

sys.path.insert(0, str(TAILFIT_DIR))
from gpd_tail import exceedance_probability, fit_gpd  # noqa: E402
from compare_years import fit_from_row, half_width  # noqa: E402

SEX = "m"                 # national girls are scraped but not fitted yet
BENCH_RANK = 25           # the northeast pool's 25th-fastest boy


def compare() -> pd.DataFrame:
    paths = {"NE": dataset_dirs((2026,), "northeast")["out"] / "summary.csv",
             "US": dataset_dirs((2026,), "us")["out"] / "summary.csv"}
    for p in paths.values():
        if not p.exists():
            raise SystemExit(f"missing {p}: run run_all.py for it first")
    ne = pd.read_csv(paths["NE"]).set_index(["event", "sex"])
    us = pd.read_csv(paths["US"]).set_index(["event", "sex"])

    rows = []
    for event in EVENTS:
        key = (pool_name(event, SEX), SEX)
        rn, ru = ne.loc[key], us.loc[key]
        dn, _ = load_pool(event, SEX, years=(2026,), region="northeast")
        du, _ = load_pool(event, SEX, years=(2026,), region="us")
        tn = dn["seconds"].to_numpy(dtype=float)
        tu = du["seconds"].to_numpy(dtype=float)

        # Both pools at the northeast's threshold. Textbook SEs, which ran
        # 1.8-3.3x narrower than the bootstrap in 2026: read the gap with that
        # in mind.
        fu = fit_gpd(-tu, -rn["u_sec"])
        se_u = abs(1 + fu.xi) / np.sqrt(fu.n_exceed)
        se_n = abs(1 + rn["xi"]) / np.sqrt(rn["N_u"])

        bench = float(np.sort(tn)[BENCH_RANK - 1])
        rp = {}
        for name, r in (("NE", rn), ("US", ru)):
            q = exceedance_probability(bench, fit_from_row(r))
            rp[name] = q["return_period"] if q["status"] == "ok" else np.nan
        emp_ne = BENCH_RANK / tn.size                    # by construction
        emp_us = float((tu <= bench).sum()) / tu.size

        rows.append({
            "event": key[0], "sex": SEX,
            "n_NE": int(rn["n"]), "n_US": int(ru["n"]),
            "fastest_NE": rn["fastest_s"], "fastest_US": ru["fastest_s"],
            "u_NE": rn["u_sec"], "u_US": ru["u_sec"],
            "N_u_NE": int(rn["N_u"]), "N_u_US": int(ru["N_u"]),
            "xi_NE": rn["xi"], "xi_NE_lo": rn["xi_ci_lo"], "xi_NE_hi": rn["xi_ci_hi"],
            "xi_US": ru["xi"], "xi_US_lo": ru["xi_ci_lo"], "xi_US_hi": ru["xi_ci_hi"],
            "shape_NE": rn["plateau"], "shape_US": ru["plateau"],
            "source_US": ru["threshold_source"],
            "wall_NE": rn["implied_wall_s"], "wall_US": ru["implied_wall_s"],
            "wall_US_lo": ru["wall_ci_lo"], "wall_US_hi": ru["wall_ci_hi"],
            "xi_US_at_uNE": fu.xi, "N_u_US_at_uNE": fu.n_exceed,
            "gap_over_se": (fu.xi - rn["xi"]) / np.hypot(se_u, se_n),
            "width_ratio_US_vs_NE": half_width(ru) / half_width(rn),
            "bench_s": bench,
            "rp_NE": rp["NE"], "rp_US": rp["US"],
            "rp_ratio_US_over_NE": rp["US"] / rp["NE"],
            "emp_frac_NE": emp_ne, "emp_frac_US": emp_us,
            "emp_ratio_US_over_NE": emp_ne / emp_us if emp_us else np.nan,
        })
    return pd.DataFrame(rows)


def _ci(r, tag) -> str:
    return f"{r[f'xi_{tag}']:+.3f} [{r[f'xi_{tag}_lo']:+.3f}, {r[f'xi_{tag}_hi']:+.3f}]"


def _shape(text: str) -> str:
    return "slides" if text.startswith("sliding") else text.replace("xi flat at ", "flat ")


def _wall(v) -> str:
    return "unbounded" if np.isneginf(v) else fmt_time(v)


def write(df: pd.DataFrame) -> None:
    L = ["# Pooled boys 2026: northeast nine vs all 51 states", ""]
    L.append("Generated by `compare_regions.py` from `output/northeast/2026/summary.csv` and "
             "`output/national/2026/summary.csv`. Times in seconds; xi intervals are "
             "95% bootstrap intervals.")
    L.append("")
    L.append("## 1. Fits")
    L.append("")
    L.append("| pool | n NE / US | fastest NE / US | xi NE | xi US | shape NE / US | US threshold from | wall US [95% CI] |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(f"| {r['event']} | {r['n_NE']:,} / {r['n_US']:,} "
                 f"| {fmt_time(r['fastest_NE'])} / {fmt_time(r['fastest_US'])} "
                 f"| {_ci(r, 'NE')} | {_ci(r, 'US')} "
                 f"| {_shape(r['shape_NE'])} / {_shape(r['shape_US'])} "
                 f"| {r['source_US']} "
                 f"| {fmt_time(r['wall_US'])} [{_wall(r['wall_US_lo'])}, {fmt_time(r['wall_US_hi'])}] |")
    L.append("")
    L.append("## 2. Both pools at the northeast's threshold")
    L.append("")
    L.append("| pool | u (s) | xi NE | xi US | N_u NE / US | gap / textbook SE |")
    L.append("|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(f"| {r['event']} | {fmt_time(r['u_NE'])} | {r['xi_NE']:+.3f} "
                 f"| {r['xi_US_at_uNE']:+.3f} | {r['N_u_NE']:,} / {r['N_u_US_at_uNE']:,} "
                 f"| {r['gap_over_se']:+.1f} |")
    L.append("")
    L.append("The bootstrap ran 1.8-3.3x wider than the textbook SE, so |gap/SE| "
             "below about 4 is within noise. The pools are not independent "
             "either: the northeast is inside the national pool.")
    L.append("")
    L.append(f"## 3. Is the northeast representative at the top?")
    L.append("")
    L.append(f"Benchmark: the northeast pool's {BENCH_RANK}th-fastest mark. If the "
             f"northeast were a representative slice, the ratio would be 1. Above "
             f"1, the time is rarer nationally (the northeast is relatively "
             f"strong at this level); below 1, it is more common nationally.")
    L.append("")
    L.append("| pool | benchmark | 1 in (NE fit) | 1 in (US fit) | ratio, fitted | ratio, empirical |")
    L.append("|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(f"| {r['event']} | {fmt_time(r['bench_s'])} | {r['rp_NE']:,.0f} "
                 f"| {r['rp_US']:,.0f} | {r['rp_ratio_US_over_NE']:.2f} "
                 f"| {r['emp_ratio_US_over_NE']:.2f} |")
    L.append("")
    L.append("Empirical ratio = (25 / n_NE) / (US athletes at or under the "
             "benchmark / n_US): no model involved. Where fitted and empirical "
             "agree, the fits are reproducing the data at this level.")

    POOLED_REGIONS.mkdir(parents=True, exist_ok=True)
    out = POOLED_REGIONS / "region_comparison.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    df.to_csv(POOLED_REGIONS / "region_comparison.csv", index=False, encoding="utf-8")
    print(f"  wrote {out}")


if __name__ == "__main__":
    write(compare())
