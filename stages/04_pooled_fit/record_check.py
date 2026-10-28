"""
record_check.py
===============
How accurate is each tail model AT THE RECORD, and which fitting threshold
makes it most accurate there?

The yardstick (stages/03_tail_fit/tail_models.rank_pit)
-------------------------------------------------------
The record is the best of n marks. If the model's S is right, z = n*S(record)
-- the number of athletes it expects at or beyond the record -- is Exp(1):
median 0.69, central 95% range 0.025 to 3.69. For the k-th best mark it is
Gamma(k, 1). So p = GammaCDF(z) is Uniform(0, 1) under a correct model, and a
single record can neither confirm nor refute it. What can: MANY records, whose
p's should look uniform. Small p = the model called the mark too rare (the
GPD near its wall); large p = it expected more athletes that fast (too heavy).

Three parts
-----------
A. Record calibration at each candidate threshold (top 10% ... top 0.5%):
     - out of sample: fit one northeast season, score the other's record and
       5th-best mark (10 pools x 2 directions = 20 of each);
     - in sample: the national 2026 pools (10 records);
     - plus, so the body is not sacrificed for the top: median |log(pred/actual)|
       at ranks 25 and 100, and 95% predictive-interval coverage (bootstrap +
       Poisson, the procedure of the 2026-10-14 report).
B. The girls' sprint records sit 2-3x lighter than the top-10% fits predict.
   Is that the mixture of grades? Records per GRADE (9-12) for the national
   100/200/400 m, both sexes, each grade-pool fitted on its own: 24 more
   in-sample records, and the boys are the control.
C. Figures: QQ plots of the record p's against Uniform, per threshold.
D. The decisive test (added 2026-10-22, once both national seasons existed):
   each Census division is its own pool, fitted on one season and scored on
   the other, both directions -- 9 x 10 x 2 = 180 records the rule never saw;
   the 4 regions (80) as a coarser check. The rule under test and its pass
   criterion are fixed beforehand (D_RULES); the other rules are references.
   Since 2026-10-22 the rule is the Gompertz threshold ForwardStop selects on
   the fit season, and the verdict uses the predictive p (see score_pair).

Writes output/comparisons/record_tests/record_calibration.{md,csv},
record_pit_qq.png; part D adds a section to the .md plus
record_division{,_summary}.csv and record_division_qq.png.

    python stages/04_pooled_fit/record_check.py [--n-boot 50]          # A-C and D
    python stages/04_pooled_fit/record_check.py --part d --n-boot 40   # D only
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
from scipy.stats import binom, gamma, kstest

from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import EVENTS, SEXES, load_pool, pool_name
from paths import POOLED_RECORDS, TAILFIT_DIR  # src/
from regions import CENSUS_DIVISIONS, CENSUS_REGIONS

sys.path.insert(0, str(TAILFIT_DIR))
from tail_models import fit_tail, rank_pit  # noqa: E402
from threshold_select import dequantize, select_forwardstop  # noqa: E402

MODELS = ("gpd", "weibull", "gompertz")
QS = (0.90, 0.95, 0.98, 0.99, 0.995)       # fitting threshold: top 10% ... 0.5%
STYLE = {"gpd": ("#8a8984", "--"), "gompertz": ("#eb6834", "-"),
         "weibull": ("#1baf7a", "-")}
SPRINTS = ("100m", "200m", "400m")
GRADES = ("9", "10", "11", "12")


def seasons():
    P = {}
    for ev in EVENTS:
        for sx in SEXES:
            for y in (2025, 2026):
                df, _ = load_pool(ev, sx, years=(y,))
                P[("ne", y, ev, sx)] = np.sort(df["seconds"].to_numpy(dtype=float))
            df, _ = load_pool(ev, sx, years=(2026,), region="us")
            P[("us", 2026, ev, sx)] = np.sort(df["seconds"].to_numpy(dtype=float))
    return P


def safe_fit(x, q, m):
    try:
        return fit_tail(x, np.quantile(x, q), m)
    except ValueError:                       # too few exceedances at this q
        return None


def score_pair(ta, tb, q, m, n_boot, rng) -> dict | None:
    """
    Fit model m to season ta (seconds, sorted) at its q-quantile, then score
    season tb's marks out of sample: the record and 5th-best PITs, the
    predicted/actual count at ranks 25 and 100, and (n_boot > 0) whether each
    rank's actual count falls in the 95% predictive interval (bootstrap of the
    fit + Poisson noise in the count). None when ta's tail is too thin to fit.

    With n_boot > 0 it also returns the PREDICTIVE p (pp1, pp5): the record's
    p averaged over the bootstrap refits instead of read off one fit. The
    plug-in p treats the fitted parameters as exact; with few exceedances they
    are not, and the plug-in p's pile up at both ends even for a correct model.
    The predictive p carries that uncertainty, so it is the yardstick from
    2026-10-22 on. It reuses the coverage refits, so no extra random draws
    are taken and every older column is unchanged.

    Shared by part A (northeast seasons) and part D (Census divisions/regions),
    so both are scored by literally the same code.
    """
    f = safe_fit(-ta, q, m)
    if f is None:
        return None
    r = rank_pit(f, tb, (1, 5))
    # A rank that sits slower than u has no model probability (prob -> nan).
    cal = {k: tb.size * float(f.prob(tb[k - 1])) / k if tb.size >= k else np.nan
           for k in (25, 100)}
    cov, pp = {}, {}
    if n_boot:
        lam = {k: [] for k in (1, 5, 25, 100)}
        for _ in range(n_boot):
            fb = safe_fit(rng.choice(-ta, ta.size), q, m)
            if fb is None:
                continue
            for k in lam:
                lam[k].append(tb.size * float(
                    np.nan_to_num(fb.prob(tb[k - 1]), nan=np.nan)))
        for k in (1, 5):
            v = np.asarray(lam[k])
            v = v[np.isfinite(v)]
            pp[k] = float(gamma.cdf(v, k).mean()) if v.size >= 10 else np.nan
        for k, v in lam.items():
            v = np.asarray(v)
            v = v[np.isfinite(v)]
            if v.size < 10:
                cov[k] = np.nan
                continue
            sims = rng.poisson(np.repeat(v, 40))
            lo, hi = np.percentile(sims, [2.5, 97.5])
            cov[k] = float(lo <= k <= hi)
    return {"n_fit": int(ta.size), "n_exceed": f.n_exceed, "n_scored": int(tb.size),
            "record": float(tb[0]),
            "z1": r[1][0], "p1": r[1][1],
            "z5": r.get(5, (np.nan, np.nan))[0], "p5": r.get(5, (np.nan, np.nan))[1],
            "cal25": cal[25], "cal100": cal[100],
            **{f"cov{k}": v for k, v in cov.items()},
            **{f"pp{k}": v for k, v in pp.items()}}


def part_a(P, n_boot, rng) -> pd.DataFrame:
    rows = []
    for q in QS:
        print(f"  threshold top {1 - q:.1%}", flush=True)
        for ev in EVENTS:
            for sx in SEXES:
                # out of sample, northeast, both directions
                for a, b in ((2025, 2026), (2026, 2025)):
                    ta, tb = P[("ne", a, ev, sx)], P[("ne", b, ev, sx)]
                    for m in MODELS:
                        s = score_pair(ta, tb, q, m, n_boot, rng)
                        if s is None:
                            continue
                        rows.append({"part": "oos", "q": q, "model": m,
                                     "event": pool_name(ev, sx), "sex": sx,
                                     "fit": a, "scored": b, **s})
                # in sample, national
                t = P[("us", 2026, ev, sx)]
                for m in MODELS:
                    f = safe_fit(-t, q, m)
                    if f is None:
                        continue
                    r = rank_pit(f, t, (1, 5))
                    rows.append({"part": "us", "q": q, "model": m,
                                 "event": pool_name(ev, sx), "sex": sx,
                                 "fit": 2026, "scored": 2026,
                                 "z1": r[1][0], "p1": r[1][1],
                                 "z5": r[5][0], "p5": r[5][1],
                                 "cal25": t.size * float(f.prob(t[24])) / 25,
                                 "cal100": t.size * float(f.prob(t[99])) / 100})
    return pd.DataFrame(rows)


def part_b() -> pd.DataFrame:
    """Records per grade, national 2026 sprints, Gompertz at each grade's top 10%."""
    rows = []
    for ev in SPRINTS:
        for sx in SEXES:
            df, _ = load_pool(ev, sx, years=(2026,), region="us")
            for g in GRADES:
                t = np.sort(df.loc[df["grade"] == g, "seconds"].to_numpy(dtype=float))
                for q in (0.90, 0.99):
                    f = safe_fit(-t, q, "gompertz")
                    if f is None:
                        continue
                    r = rank_pit(f, t, (1, 5))
                    rows.append({"event": ev, "sex": sx, "grade": g, "q": q,
                                 "n": t.size, "record": t[0],
                                 "z1": r[1][0], "p1": r[1][1], "p5": r[5][1]})
    return pd.DataFrame(rows)


# ---- part D: the division test ---------------------------------------------
# Rules are fixed BEFORE the run and named, so the table and the verdict refer
# to one thing each. q is a quantile level, or "fs": the threshold ForwardStop
# selects on the FIT season (stages/03_tail_fit/threshold_select.py). The
# ForwardStop rule never sees the scored season, so it is a fair test; the
# others are references, and "gompertz 5%" in particular was picked by looking
# at these very records (record_test_report_2026-10-22.md), so it cannot pass
# or fail anything here.
D_RULES = (
    # label          model       q       role
    ("gompertz-fs5", "gompertz", "fs5", "the rule: ForwardStop, nothing rejected -> top 5%"),
    ("gompertz-fs", "gompertz", "fs",  "ForwardStop, old fallback (lowest u); failed"),
    ("gompertz 1%", "gompertz", 0.99,  "failed 2026-10-22 (pooled_method §13.1)"),
    ("gompertz 5%", "gompertz", 0.95,  "post-hoc: selected on these records"),
    ("gpd 1%",      "gpd",      0.99,  "contrast"),
)
D_RULE = "gompertz-fs5"
# The fs5 fallback was chosen after seeing the gompertz-fs failure on these
# records (2026-10-22). Daren's call: the goal is the best-fitting rule, not a
# publication-grade hold-out, so it is adopted and tested here as is.
FS_FALLBACK_Q = 0.95

# ForwardStop settings, fixed before the run: the same as the GPD's in run_all.
FS_GRID = np.linspace(0.80, 0.995, 18)
FS_ALPHA, FS_NSIM, FS_MIN_EXCEED = 0.05, 199, 25
FS_RESOLUTION = 0.01     # ForwardStop's input is de-tied (threshold_select.dequantize)
FS_CACHE = POOLED_RECORDS / "forwardstop_gompertz.csv"


def group_states(level: str) -> dict:
    """{'Pacific': ('AK', 'CA', ...), ...} for level 'division' or 'region'."""
    m = CENSUS_DIVISIONS if level == "division" else CENSUS_REGIONS
    out = {}
    for st, g in m.items():
        out.setdefault(g, []).append(st)
    return {g: tuple(sorted(s)) for g, s in out.items()}


def forwardstop_q(t, key, cache) -> float:
    """
    The quantile level of the Gompertz threshold ForwardStop selects on the
    season t (seconds). Cached, because 18 thresholds x 199 refits per pool
    add up, and the selection does not change unless the data does.

    The seed comes from the pool's key, so each pool's selection is
    reproducible on its own, whatever order the pools run in.
    """
    if key in cache:
        return cache[key]["q_level"]
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    x = dequantize(-t, FS_RESOLUTION, rng)
    us = np.quantile(x, FS_GRID)
    r = select_forwardstop(x, us, alpha=FS_ALPHA, n_sim=FS_NSIM,
                           min_exceed=FS_MIN_EXCEED, rng=rng, verbose=False,
                           model="gompertz")
    q_level = float(FS_GRID[int(np.argmin(np.abs(us - r["u"])))])
    cache[key] = {"key": key, "q_level": q_level, "u_sec": r["u_sec"],
                  "n_exceed": r["n_exceed"], "k_reject": r["k_reject"],
                  "n_candidates": len(r["us"]), "note": r["note"],
                  "pvalues": " ".join(f"{p:.3f}" for p in r["pvalues"])}
    return q_level


def part_d(n_boot, rng, refit_fs=False) -> pd.DataFrame:
    """
    The decisive record test: many records the rule never saw.

    Each Census division (then region) is its own pool, fitted on one national
    season and scored on the other, both directions -- 9 x 10 x 2 = 180 records
    for divisions. Fitting each group on its own avoids pretending they share
    one tail shape; loading each through load_pool (not slicing the national
    pool) gives each group its own fence and dedupe, as a real pool would.

    For the ForwardStop rule the threshold is selected once on the fit season;
    the bootstrap then re-takes u at that quantile level in every resample
    (the convention gpd_pooled uses). Re-running ForwardStop inside each
    resample would be the full treatment, but costs 40x the time; the
    shortcut understates the threshold's own uncertainty a little.
    """
    cache = {}
    if FS_CACHE.exists() and not refit_fs:
        cache = {r["key"]: r for r in pd.read_csv(FS_CACHE).to_dict("records")}
    rows = []
    for level in ("division", "region"):
        groups = group_states(level)
        print(f"  part D: {len(groups)} {level}s", flush=True)
        for g, sts in groups.items():
            print(f"    {g}", flush=True)
            for ev in EVENTS:
                for sx in SEXES:
                    t = {}
                    for y in (2025, 2026):
                        df, _ = load_pool(ev, sx, states=sts, years=(y,), region="us")
                        t[y] = np.sort(df["seconds"].to_numpy(dtype=float))
                    for a, b in ((2025, 2026), (2026, 2025)):
                        for label, m, q, _role in D_RULES:
                            if q in ("fs", "fs5"):
                                key = f"{level}|{g}|{ev}|{sx}|{a}"
                                fs_q = forwardstop_q(t[a], key, cache)
                                nothing = str(cache[key]["note"]).startswith("nothing")
                                q = FS_FALLBACK_Q if (q == "fs5" and nothing) else fs_q
                            s = score_pair(t[a], t[b], q, m, n_boot, rng)
                            base = {"level": level, "group": g, "event": pool_name(ev, sx),
                                    "sex": sx, "fit": a, "scored": b, "rule": label,
                                    "model": m, "q": q}
                            # A group whose tail is too thin to fit is kept as a
                            # row, so the drop is counted rather than invisible.
                            rows.append({**base, **(s or {"dropped": True})})
    pd.DataFrame(list(cache.values())).to_csv(FS_CACHE, index=False)
    D = pd.DataFrame(rows)
    D["dropped"] = D.get("dropped", False)
    D["dropped"] = D["dropped"].fillna(False).astype(bool)
    return D


def binom_range(n: int, p: float = 0.025) -> tuple[int, int]:
    """Central 95% range of how many of n records land in one 2.5% tail."""
    return int(binom.ppf(0.025, n, p)), int(binom.ppf(0.975, n, p))


def summarise_d(D: pd.DataFrame) -> pd.DataFrame:
    rows = []
    order = {lab: i for i, (lab, *_r) in enumerate(D_RULES)}
    for (level, rule), g in D.groupby(["level", "rule"], sort=False):
        k = g[~g["dropped"]]
        logcal = np.abs(np.log(pd.concat([k["cal25"], k["cal100"]]).replace(0, np.nan)))
        cov_cols = [c for c in k if c.startswith("cov")]
        lo, hi = binom_range(len(k))
        row = {"level": level, "rule": rule, "order": order[rule],
               "n_records": len(k), "n_dropped": int(g["dropped"].sum()),
               "min_exceed": int(k["n_exceed"].min()) if len(k) else 0,
               "tails_95_range": f"{lo}-{hi}",
               "median_abs_log_cal_25_100": float(np.nanmedian(logcal)),
               "n_cal_missing": int(pd.concat([k["cal25"], k["cal100"]]).isna().sum()),
               "coverage": float(np.nanmean(k[cov_cols].to_numpy())) if cov_cols else np.nan}
        # The same statistics on the plug-in p ("p") and the predictive p ("pp").
        for tag, c1, c5 in (("plug", "p1", "p5"), ("pred", "pp1", "pp5")):
            if c1 not in k:
                continue
            row.update({
                f"{tag}_ks": ks(k[c1]),
                f"{tag}_ks_25to26": ks(k.loc[k["fit"] == 2025, c1]),
                f"{tag}_ks_26to25": ks(k.loc[k["fit"] == 2026, c1]),
                f"{tag}_tails": tails(k[c1]),
                f"{tag}_rank5_ks": ks(k[c5]),
            })
        row["median_z1"] = float(np.nanmedian(k["z1"]))
        rows.append(row)
    return (pd.DataFrame(rows).sort_values(["level", "order"])
            .drop(columns="order").reset_index(drop=True))


def verdict_d(SD: pd.DataFrame) -> list[str]:
    """The pass criterion, fixed in the plan before the run: divisions, the
    rule under test, judged on the PREDICTIVE p."""
    r = SD[(SD["level"] == "division") & (SD["rule"] == D_RULE)].iloc[0]
    if "pred_ks" not in r or not np.isfinite(r["pred_ks"]):
        return ["- No verdict: the predictive p needs --n-boot >= 10."]
    lo, hi = (int(x) for x in r["tails_95_range"].split("-"))
    t_lo, t_hi = (int(x) for x in r["pred_tails"].split(" / "))
    checks = [
        ("record KS p > 0.05 overall (predictive p)", r["pred_ks"] > 0.05),
        ("... and fit 2025 -> score 2026", r["pred_ks_25to26"] > 0.05),
        ("... and fit 2026 -> score 2025", r["pred_ks_26to25"] > 0.05),
        (f"records in each 2.5% tail within {lo}-{hi}", lo <= t_lo <= hi and lo <= t_hi <= hi),
        ("median abs log calibration at ranks 25/100 <= 0.11",
         r["median_abs_log_cal_25_100"] <= 0.11),
    ]
    L = [f"- {'PASS' if ok else 'FAIL'}: {name}" for name, ok in checks]
    L.append("")
    L.append(f"**Verdict: `{D_RULE}` {'PASSES' if all(ok for _, ok in checks) else 'FAILS'}.**")
    return L


DIV_START, DIV_END = "<!-- division-test:start -->", "<!-- division-test:end -->"


def _f(v, fmt="{:.3f}"):
    return fmt.format(v) if isinstance(v, (int, float)) and np.isfinite(v) else "-"


def division_section(D: pd.DataFrame, SD: pd.DataFrame) -> str:
    roles = {lab: role for lab, _m, _q, role in D_RULES}
    L = [DIV_START, "## D. Division test: out of sample, many records", ""]
    L.append("Each Census division (and region) is its own pool. It is fitted on "
             "one national season and scored on the other, in both directions. "
             f"The rule is `{D_RULE}`: the Gompertz threshold that ForwardStop "
             "selects on the fit season; where ForwardStop rejects nothing, the "
             f"top {1 - FS_FALLBACK_Q:.0%}. That fallback was chosen after "
             "`gompertz-fs` (lowest-u fallback) failed on these records, so this "
             "is not a fresh test of it. The other rules are references.")
    L.append("")
    L.append("**Two versions of p.** The *plug-in* p uses one fit, as if its "
             "parameters were exact. The *predictive* p is the mean over the "
             "bootstrap refits, so it includes the parameter uncertainty. The "
             "verdict uses the predictive p.")
    L.append("")
    L.append("| level | rule | role | records | predictive KS | 25→26 | 26→25 "
             "| tails low / high (95% range) | plug-in KS | plug-in tails "
             "| rank-5 KS (pred.) | median z (0.69) | median abs log cal 25/100 "
             "| 95% coverage |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in SD.iterrows():
        name = f"**{r['rule']}**" if r["rule"] == D_RULE else r["rule"]
        miss = f" ({int(r['n_cal_missing'])} below u)" if r["n_cal_missing"] else ""
        L.append(f"| {r['level']} | {name} | {roles[r['rule']]} "
                 f"| {r['n_records']} ({r['n_dropped']} dropped) "
                 f"| {_f(r.get('pred_ks'))} | {_f(r.get('pred_ks_25to26'))} "
                 f"| {_f(r.get('pred_ks_26to25'))} "
                 f"| {r.get('pred_tails', '-')} ({r['tails_95_range']}) "
                 f"| {_f(r['plug_ks'])} | {r['plug_tails']} "
                 f"| {_f(r.get('pred_rank5_ks'))} | {r['median_z1']:.2f} "
                 f"| {r['median_abs_log_cal_25_100']:.2f}{miss} "
                 f"| {_f(r['coverage'], '{:.1%}')} |")
    L.append("")
    L.append("### Pass criterion (divisions, the rule under test)")
    L.append("")
    L += verdict_d(SD)
    L.append("")
    # What ForwardStop selected: if it mostly fell back to a grid end, the
    # rule is a default in disguise, and the verdict has to say so.
    if FS_CACHE.exists():
        C = pd.read_csv(FS_CACHE)
        L.append("### What ForwardStop selected (Gompertz)")
        L.append("")
        L.append(f"Grid: {len(FS_GRID)} quantile levels from {FS_GRID[0]:.0%} to "
                 f"{FS_GRID[-1]:.1%}; α = {FS_ALPHA}; {FS_NSIM} simulations per "
                 f"threshold; min. {FS_MIN_EXCEED} exceedances; times jittered "
                 f"±{FS_RESOLUTION / 2} s before the test (ties).")
        L.append("")
        for level in ("division", "region"):
            c = C[C["key"].str.startswith(level + "|")]
            if not len(c):
                continue
            notes = c["note"].map(lambda s: "ok" if s == "ok" else
                                  ("nothing rejected" if s.startswith("nothing")
                                   else "all rejected"))
            # Real selections only: the fallbacks sit at a grid end by
            # construction (and gompertz-fs5 replaces "nothing rejected" by
            # the top 5%), so including them would describe the fallback.
            top = (1 - c.loc[notes == "ok", "q_level"]) * 100
            sel = (f"real selections at top {top.min():.1f}% to {top.max():.1f}% "
                   f"(median {top.median():.1f}%)" if len(top) else "no real selections")
            L.append(f"- {level}s ({len(c)} pools): "
                     + ", ".join(f"{k}: {v}" for k, v in notes.value_counts().items())
                     + f"; {sel}. Under `gompertz-fs5`, 'nothing rejected' uses the "
                     f"top {1 - FS_FALLBACK_Q:.0%}; 'all rejected' uses the top "
                     f"{1 - FS_GRID[-1]:.1%}.")
        L.append("")
    k = D[(D["level"] == "division") & (D["rule"] == D_RULE) & ~D["dropped"]]
    col = "pp1" if "pp1" in k and k["pp1"].notna().any() else "p1"
    out = k[(k[col] < 0.025) | (k[col] > 0.975)].sort_values(col)
    if len(out):
        L.append(f"Records outside the central 95% under `{D_RULE}` "
                 f"({'predictive' if col == 'pp1' else 'plug-in'} p):")
        L.append("")
        L.append("| division | pool | fit → scored | fit at top | record | z | p |")
        L.append("|---|---|---|---|---|---|---|")
        for _, r in out.iterrows():
            L.append(f"| {r['group']} | {r['event']} {r['sex']} | {r['fit']} → {r['scored']} "
                     f"| {1 - r['q']:.1%} | {r['record']:.2f} | {r['z1']:.3f} | {r[col]:.3f} |")
        L.append("")
    L.append("Figure: `record_division_qq.png`. Rows: `record_division.csv`. "
             "ForwardStop selections: `forwardstop_gompertz.csv`.")
    L.append(DIV_END)
    return "\n".join(L)


def division_figure(D: pd.DataFrame) -> None:
    col = "pp1" if "pp1" in D and D["pp1"].notna().any() else "p1"
    look = {"gompertz-fs5": ("#eb6834", "-", 2.2), "gompertz-fs": ("#c0392b", "-.", 1.1),
            "gompertz 1%": ("#eb6834", ":", 1.1),
            "gompertz 5%": ("#1baf7a", "--", 1.1), "gpd 1%": ("#8a8984", "--", 1.1)}
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
    for ax, level in zip(axes, ("division", "region")):
        n = 0
        for label, *_r in D_RULES:
            k = D[(D["level"] == level) & (D["rule"] == label) & ~D["dropped"]]
            p = np.sort(k[col].dropna().to_numpy())
            if p.size == 0:
                continue
            n = max(n, p.size)
            exp_q = (np.arange(1, p.size + 1) - 0.5) / p.size
            color, ls, lw = look[label]
            ax.plot(exp_q, p, color=color, ls=ls, lw=lw,
                    label=label + (" (under test)" if label == D_RULE else ""))
        band = 1.36 / np.sqrt(max(n, 1))          # 95% KS band
        ax.plot([0, 1], [0, 1], color="#0b0b0b", lw=0.8)
        ax.fill_between([0, 1], [-band, 1 - band], [band, 1 + band],
                        color="#d8d7d2", alpha=0.4, lw=0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"{level}s: {n} out-of-sample records", fontsize=10)
        ax.set_xlabel("uniform quantile", fontsize=8)
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel(f"record {'predictive ' if col == 'pp1' else ''}p (sorted)", fontsize=9)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Division test: below the diagonal = records called too rare; "
                 "above = too heavy; grey = 95% KS band", fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    path = POOLED_RECORDS / "record_division_qq.png"
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"  wrote {path}")


def splice_division(section: str | None) -> None:
    """Put the division section into record_calibration.md, replacing any old
    one, so parts A-C and part D can be rerun independently."""
    path = POOLED_RECORDS / "record_calibration.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Record-level calibration\n"
    old = None
    if DIV_START in text and DIV_END in text:
        a, b = text.index(DIV_START), text.index(DIV_END) + len(DIV_END)
        old, text = text[a:b], (text[:a] + text[b:]).rstrip() + "\n"
    section = section or old
    if section:
        text = text.rstrip() + "\n\n" + section + "\n"
    path.write_text(text, encoding="utf-8")


def ks(p) -> float:
    p = np.asarray(p, dtype=float)
    p = p[np.isfinite(p)]
    return float(kstest(p, "uniform").pvalue) if p.size >= 5 else np.nan


def tails(p) -> str:
    p = np.asarray(p, dtype=float)
    p = p[np.isfinite(p)]
    return f"{(p < 0.025).sum()} / {(p > 0.975).sum()}"


def summarise(A: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (q, m), g in A.groupby(["q", "model"]):
        o, u = g[g["part"] == "oos"], g[g["part"] == "us"]
        both = pd.concat([o["p1"], u["p1"]])
        logcal = np.abs(np.log(pd.concat([o["cal25"], o["cal100"]]).replace(0, np.nan)))
        rows.append({
            "q": q, "model": m,
            "record_ks_oos": ks(o["p1"]), "record_ks_us": ks(u["p1"]),
            "record_ks_all": ks(both), "record_tails_all": tails(both),
            "median_z1_all": float(np.nanmedian(pd.concat([o["z1"], u["z1"]]))),
            "rank5_ks_all": ks(pd.concat([o["p5"], u["p5"]])),
            "median_abs_log_cal_25_100": float(np.nanmedian(logcal)),
            "n_cal_missing": int(pd.concat([o["cal25"], o["cal100"]]).isna().sum()),
            "coverage": float(np.nanmean(o[[c for c in o if c.startswith("cov")]]
                                         .to_numpy())) if any(
                c.startswith("cov") for c in o) else np.nan,
        })
    return pd.DataFrame(rows)


def qq_figure(A: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, len(QS), figsize=(3.4 * len(QS), 3.6), sharey=True)
    for ax, q in zip(axes, QS):
        for m in MODELS:
            p = A[(A["q"] == q) & (A["model"] == m)]["p1"].dropna().sort_values().to_numpy()
            if p.size == 0:
                continue
            exp_q = (np.arange(1, p.size + 1) - 0.5) / p.size
            ax.plot(exp_q, p, marker="o", ms=3, color=STYLE[m][0], ls=STYLE[m][1],
                    lw=1.3, label=m)
        ax.plot([0, 1], [0, 1], color="#0b0b0b", lw=0.8)
        # 95% band for the KS statistic at n = 30 points
        ax.fill_between([0, 1], [-0.24, 0.76], [0.24, 1.24], color="#d8d7d2",
                        alpha=0.4, lw=0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"fit at top {1 - q:.1%}", fontsize=10)
        ax.set_xlabel("uniform quantile", fontsize=8)
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel("record p (sorted)", fontsize=9)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.suptitle("Record calibration: 30 records (20 out of sample, 10 national). "
                 "On the diagonal = right; below = model calls records too rare; "
                 "above = too heavy", fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    path = POOLED_RECORDS / "record_pit_qq.png"
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"  wrote {path}")


def write(A, S, B) -> None:
    # Capture part D's section BEFORE this file is overwritten, then put it
    # back. (Until 2026-10-22 the capture ran after the overwrite and found
    # nothing, so a parts-A-C run silently dropped section D.)
    path = POOLED_RECORDS / "record_calibration.md"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    kept = (old[old.index(DIV_START):old.index(DIV_END) + len(DIV_END)]
            if DIV_START in old and DIV_END in old else None)
    L = ["# Record-level calibration", ""]
    L.append("Generated by `record_check.py`. Yardstick: under a correct model "
             "z = n·S(record) ~ Exp(1) (median 0.69, 95% range 0.025–3.69), so "
             "p = 1 − e^(−z) ~ Uniform(0, 1); for the 5th-best mark, Gamma(5, 1). "
             "KS p-values test uniformity over many records (high = consistent). "
             "'tails' counts records with p < 0.025 (called too rare) / > 0.975 "
             "(too heavy); about 0.75 of each is expected among 30.")
    L.append("")
    L.append("## A. By model and fitting threshold")
    L.append("")
    L.append("| fit at top | model | record KS: out of sample (20) | national (10) | all 30 | tails low / high | median z (0.69) | rank-5 KS | median abs log calibration at ranks 25/100 | 95% coverage |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in S.iterrows():
        miss = f" ({int(r['n_cal_missing'])} below u)" if r["n_cal_missing"] else ""
        L.append(f"| {1 - r['q']:.1%} | {r['model']} | {r['record_ks_oos']:.3f} "
                 f"| {r['record_ks_us']:.3f} | {r['record_ks_all']:.3f} "
                 f"| {r['record_tails_all']} | {r['median_z1_all']:.2f} "
                 f"| {r['rank5_ks_all']:.3f} | {r['median_abs_log_cal_25_100']:.2f}{miss} "
                 f"| {r['coverage']:.1%} |")
    L.append("")
    L.append("Median abs log calibration: 0.10 means predictions are typically "
             "within about 10% of the actual count at ranks 25 and 100.")
    L.append("")
    L.append("### National records, per pool (in sample)")
    L.append("")
    L.append("| fit at top | model | " + " | ".join(
        f"{e} {s}" for e, s in A[A['part'] == 'us'][['event', 'sex']].drop_duplicates().itertuples(index=False)) + " |")
    pools = A[A["part"] == "us"][["event", "sex"]].drop_duplicates()
    L.append("|---|---|" + "---|" * len(pools))
    for (q, m), g in A[A["part"] == "us"].groupby(["q", "model"]):
        g = g.set_index(["event", "sex"])
        L.append(f"| {1 - q:.1%} | {m} | " + " | ".join(
            f"{g.loc[(e, s), 'p1']:.3f}" if (e, s) in g.index else "-"
            for e, s in pools.itertuples(index=False)) + " |")
    L.append("")
    L.append("## B. Sprint records by grade (national 2026, Gompertz, each grade on its own)")
    L.append("")
    L.append("| event | sex | grade | n | record | p (top 10%) | p (top 1%) |")
    L.append("|---|---|---|---|---|---|---|")
    for (ev, sx, g), d in B.groupby(["event", "sex", "grade"], sort=False):
        d = d.set_index("q")
        cell = lambda q: f"{d.loc[q, 'p1']:.3f}" if q in d.index else "-"
        L.append(f"| {ev} | {sx} | {g} | {int(d['n'].iloc[0]):,} "
                 f"| {d['record'].iloc[0]:.2f} | {cell(0.90)} | {cell(0.99)} |")
    for sx in SEXES:
        for q in (0.90, 0.99):
            p = B[(B["sex"] == sx) & (B["q"] == q)]["p1"]
            L.append("")
            L.append(f"- {'boys' if sx == 'm' else 'girls'}, top {1 - q:.0%}: "
                     f"{len(p)} grade records, KS p = {ks(p):.3f}, "
                     f"median p = {p.median():.2f}, tails {tails(p)}")
    L.append("")
    L.append("Figure: `record_pit_qq.png`.")
    (POOLED_RECORDS / "record_calibration.md").write_text("\n".join(L) + "\n",
                                                        encoding="utf-8")
    A.to_csv(POOLED_RECORDS / "record_calibration.csv", index=False)
    S.to_csv(POOLED_RECORDS / "record_calibration_summary.csv", index=False)
    B.to_csv(POOLED_RECORDS / "record_by_grade.csv", index=False)
    splice_division(kept)          # keep part D's section if it existed
    print(f"  wrote {POOLED_RECORDS / 'record_calibration.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Record-level calibration check.")
    ap.add_argument("--n-boot", type=int, default=50,
                    help="bootstrap resamples for coverage (0 skips it)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--refit-fs", action="store_true",
                    help="part D: ignore the cached ForwardStop selections")
    ap.add_argument("--part", choices=["all", "abc", "d"], default="all",
                    help="abc: northeast/national/grade checks; d: division test")
    args = ap.parse_args()
    POOLED_RECORDS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    if args.part in ("all", "abc"):
        P = seasons()
        A = part_a(P, args.n_boot, rng)
        S = summarise(A)
        B = part_b()
        write(A, S, B)
        qq_figure(A)
    if args.part in ("all", "d"):
        D = part_d(args.n_boot, rng, args.refit_fs)
        SD = summarise_d(D)
        D.to_csv(POOLED_RECORDS / "record_division.csv", index=False)
        SD.to_csv(POOLED_RECORDS / "record_division_summary.csv", index=False)
        splice_division(division_section(D, SD))
        division_figure(D)
        print("\n".join(verdict_d(SD)))


if __name__ == "__main__":
    main()
