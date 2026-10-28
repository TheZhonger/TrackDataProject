"""
run_states.py
=============
Single-event GPD fits for every northeast state, both sexes, all five events,
on the 2026 scrape. 9 states x 2 sexes x 5 events = 90 fits.

Why per state when stage 04 pools
---------------------------------
Pooling is a mixture of nine fields, and a mixture's tail belongs to its
deepest component (NY, PA). Fitting each state on its own answers the question
the pool cannot: is a sliding shape parameter a property of each state's
distribution, or something pooling manufactured? pooled_method.md section 7
claimed "every state's 1600 m slides on its own"; this tests it on current
data, for every event.

What it reuses, unchanged
-------------------------
gpd_tail.load_event / fit_gpd / bootstrap / threshold_sweep / make_figure and
threshold_select.select_forwardstop / select_mixture_mle -- the same code the
single-file scripts run. Only the orchestration and two guards are new:

  * ForwardStop rejecting NOTHING is a fallback, not a selection (the
    "nothing rejected" gap in references/threshold_select.md). Detected here as
    "selected the first candidate", and not counted as converged.
  * A mixture optimum on the grid edge is not an optimum (select_mixture_mle
    already reports `at_edge`).

The threshold used for the fit is ForwardStop's if it converged, else the
mixture's if it did not sit on an edge, else a FALLBACK leaving max(25, 5% of
n) exceedances -- a number to look at, not a result. (A fixed 0.95 quantile
would leave RI girls' 155-runner 1500 m with 8 points, too few to fit.)

The mile
--------
Per state and sex the mile variant with the most rows (src/distances.py) is
converted to 1600 m for boys and 1500 m for girls, exactly as stage 04 does.
A single state's fit does not need a common scale, but reporting walls and
fastest marks on the same scale as the pooled table makes them comparable.

Note the single-file loader has no slow-side fence (stage 04's pool does), so a
few junk rows ("12:57.00" filed as a 100 m) sit in n. They cannot reach the
fast tail; they nudge zeta = N_u/n by well under 1%.

Usage:  python stages/03_tail_fit/run_states.py [--states NY,PA] [--sex m]
                                                [--events 100m,mile] [--n-sim 199]
Output: stages/03_tail_fit/output/2026/<ST>_<sex>_<pool>.png
        stages/03_tail_fit/output/2026/state_fits.csv, state_fits.md
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# gpd_tail puts src/ on sys.path, so paths and distances import after it.
from gpd_tail import (bootstrap, endpoint_interval, fit_gpd,  # noqa: E402
                      load_event, make_figure, threshold_sweep)
from threshold_select import select_forwardstop, select_mixture_mle  # noqa: E402
from paths import DATA_2026, TAILFIT_OUT                               # noqa: E402
from distances import factors_for, main_mile_slug, target_name         # noqa: E402

NORTHEAST = ("CT", "MA", "ME", "NH", "NJ", "NY", "PA", "RI", "VT")
EVENTS = ("100m", "200m", "400m", "800m", "mile")
OUT = TAILFIT_OUT / "2026"

Q_LO, Q_HI, N_CAND = 0.80, 0.995, 18     # same candidate grid as compare()
FALLBACK_MIN_EXCEED = 25
FALLBACK_FRAC = 0.05


def fmt(s: float) -> str:
    if s is not None and np.isneginf(s):
        return "unbounded"          # no finite fast end (gpd_tail.endpoint_interval)
    if s is None or not np.isfinite(s):
        return "--"
    if s < 60:
        return f"{s:.2f}"
    m, sec = divmod(s, 60)
    return f"{int(m)}:{sec:05.2f}"


def source(state: str, sex: str, event: str) -> tuple[Path | None, str, float]:
    """(csv path, pool name, factor onto that pool's scale)."""
    d = DATA_2026 / state / sex
    if event != "mile":
        p = d / f"{event[:-1]}r.csv"
        return (p if p.exists() else None), event, 1.0
    slug = main_mile_slug(d)
    if slug is None:
        return None, target_name(sex), 1.0
    return d / f"{slug}.csv", target_name(sex), factors_for(sex)[slug]


def fit_one(state, sex, event, n_sim, n_boot, seed, plot=True) -> dict:
    path, pool, factor = source(state, sex, event)
    row = {"state": state, "sex": sex, "event": pool,
           "file": path.name if path else None, "factor": round(factor, 6)}
    if path is None:
        return {**row, "status": "no file"}

    df, stats = load_event(str(path))
    t = df["seconds"].to_numpy(dtype=float) * factor
    x = -t
    row.update(n=len(t), fastest_s=float(t.min()))

    us = np.quantile(x, np.linspace(Q_LO, Q_HI, N_CAND))
    rng = np.random.default_rng(seed)

    # ---- the two selectors, with their failure modes made explicit -------
    try:
        fs = select_forwardstop(x, us, n_sim=n_sim, rng=rng, verbose=False)
        # Selecting the very first candidate means nothing was rejected: the
        # lowest threshold is a default, not evidence.
        nothing_rejected = np.isclose(fs["u"], us[0])
        fs_ok = fs["note"] == "ok" and not nothing_rejected
        fs_why = ("nothing rejected" if nothing_rejected else
                  "all rejected" if fs["note"] != "ok" else "ok")
    except ValueError:                       # too few exceedances anywhere
        fs, fs_ok, fs_why = None, False, "too few exceedances"
    try:
        mx = select_mixture_mle(t, -us, verbose=False)
        mx_ok = not mx["at_edge"]
    except Exception:                        # tiny states can defeat the optimiser
        mx, mx_ok = None, False

    if fs_ok:
        u, chosen = fs["u"], "forwardstop"
    elif mx_ok:
        u, chosen = -mx["u_sec"], "mixture"
    else:
        k = max(FALLBACK_MIN_EXCEED, int(FALLBACK_FRAC * len(x)))
        u, chosen = float(np.sort(x)[-k - 1]), f"FALLBACK N_u={k}"

    row.update(fs_u=fs["u_sec"] if fs else np.nan, fs_status=fs_why,
               mx_u=mx["u_sec"] if mx else np.nan,
               mx_status=("ok" if mx_ok else "edge" if mx else "failed"),
               chosen=chosen)

    try:
        fit = fit_gpd(x, u)
    except Exception as err:
        return {**row, "status": f"fit failed: {err}"}

    # ---- bootstrap: xi CI and the wall's CI -----------------------------
    q_of_u = float((x <= u).mean())
    boot = bootstrap(x, [float(t.min())], "quantile", q_of_u, n_boot, rng)
    raw = boot["raw"]
    # Unbounded draws (xi >= 0, or a wall at or below 0 s) count as -inf rather
    # than being dropped -- see gpd_tail.endpoint_interval.
    w_lo, w_hi, w_unb = endpoint_interval(raw)
    wall_ci = (w_lo, w_hi)

    # ---- plateau: how far xi travels across the threshold sweep ---------
    sweep = threshold_sweep(x)
    xs = sweep["xi"].dropna().to_numpy()
    drift = float(xs.max() - xs.min()) if xs.size else np.nan
    rises = float(np.mean(np.diff(xs) > 0)) if xs.size > 2 else np.nan

    row.update(
        status="ok", u_s=fit.u_seconds, N_u=fit.n_exceed,
        xi=fit.xi, xi_lo=boot["xi_ci"][0], xi_hi=boot["xi_ci"][1],
        sigma=fit.sigma, wall_s=fit.endpoint_seconds,
        wall_lo=wall_ci[0], wall_hi=wall_ci[1], wall_unbounded_frac=w_unb,
        wall_margin_s=(t.min() - fit.endpoint_seconds
                       if fit.endpoint_seconds is not None else np.nan),
        xi_drift=drift, xi_rise_frac=rises,
        xi_below_half=fit.xi < -0.5,
    )

    if plot:
        OUT.mkdir(parents=True, exist_ok=True)
        who = "boys" if sex == "m" else "girls"
        make_figure(x, fit, sweep, [float(t.min())],
                    f"{state} {who} {pool} 2026 ({chosen})",
                    OUT / f"{state}_{sex}_{pool}.png")
        plt.close("all")
    return row


def write_tables(df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "state_fits.csv", index=False)

    L = ["# Per-state single-event GPD fits -- 2026 northeast", "",
         "One row per state x sex x event. Mile pools: boys on 1600 m, girls on "
         "1500 m (src/distances.py). `chosen` is which selector set u; "
         "FALLBACK means neither converged. `xi drift` is max-min of xi "
         "across stages/03's 40-step threshold sweep; `rise` is the share of "
         "steps where xi increased (a slide reads near 0 or 1, a plateau "
         "near 0.5).", ""]
    for (sex, event), g in df.groupby(["sex", "event"], sort=False):
        who = "boys" if sex == "m" else "girls"
        L += [f"## {event} {who}", "",
              "| state | file | n | chosen | u | N_u | xi | xi 95% CI | wall | "
              "wall CI | fastest | xi drift | rise |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            if r["status"] != "ok":
                L.append(f"| {r['state']} | {r['file']} | {r.get('n', '')} | "
                         f"{r['status']} |" + " |" * 9)
                continue
            flag = " ⚠" if r["xi_below_half"] else ""
            L.append(
                f"| {r['state']} | {r['file']} | {int(r['n']):,} | {r['chosen']} | "
                f"{fmt(r['u_s'])} | {int(r['N_u'])} | {r['xi']:+.3f}{flag} | "
                f"[{r['xi_lo']:+.2f}, {r['xi_hi']:+.2f}] | {fmt(r['wall_s'])} | "
                f"{fmt(r['wall_lo'])}–{fmt(r['wall_hi'])} | {fmt(r['fastest_s'])} | "
                f"{r['xi_drift']:.2f} | {r['xi_rise_frac']:.2f} |")
        L.append("")
    L += ["⚠ = xi < -0.5: maximum likelihood is non-regular there "
          "(_config/lessons.md); treat that row's CIs and wall as unreliable.", ""]
    (OUT / "state_fits.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Per-state GPD fits, 2026 northeast.")
    ap.add_argument("--states", default=",".join(NORTHEAST))
    ap.add_argument("--sex", default="m,f")
    ap.add_argument("--events", default=",".join(EVENTS))
    ap.add_argument("--n-sim", type=int, default=199)
    ap.add_argument("--n-boot", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()

    rows, t0 = [], time.time()
    for event in a.events.split(","):
        for sex in a.sex.split(","):
            for state in a.states.split(","):
                t1 = time.time()
                r = fit_one(state, sex, event, a.n_sim, a.n_boot, a.seed,
                            plot=not a.no_plot)
                rows.append(r)
                xi = f"xi={r['xi']:+.3f}" if r.get("status") == "ok" else r.get("status")
                print(f"  {state} {sex} {r['event']:<6} n={r.get('n', 0):>6,} "
                      f"{r.get('chosen', ''):<15} {xi}   ({time.time() - t1:.0f} s)",
                      flush=True)
    write_tables(pd.DataFrame(rows))
    print(f"\n  {len(rows)} fits in {time.time() - t0:.0f} s -> {OUT}")


if __name__ == "__main__":
    main()
