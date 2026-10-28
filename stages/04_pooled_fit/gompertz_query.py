"""
gompertz_query.py
=================
Score any time with the national Gompertz fits (2025 + 2026 stacked): how rare
is it, and how sure are we?

WHAT IT PRINTS
--------------
For a time t at or faster than the pool's threshold u:

    return period  RP(t) = 1 / S(t),   S(t) = zeta * exp(-c * (e^((u - t)/b) - 1))

"one athlete-season in RP runs this fast" (u, t in seconds; zeta = N_u / n,
the share of athlete-seasons at u or faster). Plus the expected number of
athletes this fast in ONE season, n_season * S(t), with n_season the mean of
the two seasons' pool sizes: "0.3 per season" means about one every three
seasons.

Slower than u, the tail model says nothing -- the Gompertz was fitted to the
excesses above u only -- so no number is printed. Use the empirical rank there.

THE INTERVALS
-------------
Each of the 200 cluster-bootstrap draws in gompertz_boot.csv is a whole refit
(its own u, zeta, c and b), so each gives its own RP(t); the interval is the
middle L% of those. That is the joint uncertainty. The c and b intervals in
gompertz_fit.csv cannot be combined into one, because c and b are correlated.

Two levels by default, 80% and 95%. A narrower interval is not wrong, it
claims less: an 80% interval misses the true value about 1 time in 5, a 95%
interval 1 in 20. The 95% interval also rests on the 5 outermost draws on each
side, so it is the noisier of the two. A draw whose own u is faster than t
cannot score t and is left out; the "draws" column says how many remain.

FIELD SIZE AND EQUIVALENT TIMES
-------------------------------
"1 in 3,969" is per runner, so it needs a field to mean something. Each
query also prints the field: n_season athlete-seasons run this event in a
typical season, so the model expects n_season / RP of them this fast. The
same RP gives different counts in different events because the fields
differ (about 192,000 boys run the 100m in a season, about 105,000 the
1600m).

Equal RP means equally rare per runner, which is the project's cross-event
scale. So for each other event E of the same sex the query solves
S_E(t) = 1/RP for t, the equally rare time there. With q = 1 / (RP * zeta_E),
the share of E's tail that is this fast,

    t = u_E - b_E * log1p(-ln(q) / c_E),

valid only for q <= 1. If q > 1 the equally rare time is slower than E's
threshold and the model cannot give it (it prints "slower than E's
threshold"). The interval of an equivalent time applies the same formula to
each of E's bootstrap draws at the point RP, so it shows E's fit uncertainty
only. The two events' bootstraps are independent, not paired, so there is no
honest joint interval.

SLOWER THAN u: COUNTS, NOT THE MODEL
------------------------------------
The Gompertz describes only the marks faster than u, so it says nothing
slower. There the tool COUNTS instead: k of the n athlete-seasons in 2025 +
2026 ran t or faster, so RP = n / k. Below u, k is above about 1,000, so a
count is accurate to about 3% and needs no model. Faster than u, the count
is printed under the model's answer as a check. Its 95% interval is the exact
Poisson interval for k, and a model RP outside it is flagged. Near the record
k is tiny and the count is only a rank: it cannot be rarer than 1 in n, and
it cannot see the margin. That is why the model leads there.

Equivalent times follow the same rule. An equally rare time faster than the
other event's u comes from its model; a slower one is the time at the same
share of that event's counts, marked "(counted)".

The counts come from gompertz_counts.csv: every distinct time in each pool,
with the number of athlete-seasons at that time in each season. --build-counts
(or a missing file) writes it from the pools; it takes about a minute. Its
pool sizes must equal gompertz_fit.csv's, or the tool stops: rerun both.

Far past the fastest real mark, the return period is extrapolation. The
record test (pooled_method.md §13.3) passed, but only just, so trust the
order of magnitude out there, not the digits.

    python stages/04_pooled_fit/gompertz_query.py 100m m 10.31 10.50
    python stages/04_pooled_fit/gompertz_query.py mile f 4:35 --level 0.68,0.95
    python stages/04_pooled_fit/gompertz_query.py --csv queries.csv   # event,sex,time
    python stages/04_pooled_fit/gompertz_query.py 400m f 54.2 --no-equiv
    python stages/04_pooled_fit/gompertz_query.py --check
    python stages/04_pooled_fit/gompertz_query.py --build-counts

Events: 100m 200m 400m 800m, and mile / 1600m (boys) / 1500m (girls). Reads
gompertz_fit.csv and gompertz_boot.csv from gompertz_pooled.py, and
gompertz_counts.csv; it does not load the pools, so it answers at once.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import POOLED_GOMPERTZ, TAILFIT_DIR  # noqa: E402
from pool_data import EVENTS, load_pool, pool_name  # noqa: E402
from util import parse_time  # noqa: E402

sys.path.insert(0, str(TAILFIT_DIR))
from tail_models import TailFit  # noqa: E402

YEARS = (2025, 2026)
MIN_DRAWS = 20          # as gompertz_pooled.ci: fewer finite draws -> no interval
COUNTS = POOLED_GOMPERTZ / "gompertz_counts.csv"
EPS = 1e-6              # times are floats from 0.01 s strings: compare with slack


def return_period(t, u_sec, zeta, c, b) -> np.ndarray:
    """RP(t) = 1/S(t); nan where t is slower than u (outside the tail model).
    Broadcasts, so one call scores every bootstrap draw at once."""
    t = np.asarray(t, dtype=float)
    y = u_sec - t                                   # seconds faster than u
    s = zeta * np.exp(-c * np.expm1(np.maximum(y, 0) / b))
    with np.errstate(divide="ignore"):
        return np.where(y >= 0, 1.0 / s, np.nan)


def equal_rarity_time(rp, u_sec, zeta, c, b) -> np.ndarray:
    """The inverse of return_period: the time t with RP(t) = rp. nan where the
    equally rare time is slower than u (q > 1: outside the tail model)."""
    q = 1.0 / (np.asarray(rp, dtype=float) * zeta)     # share of the tail this fast
    with np.errstate(divide="ignore", invalid="ignore"):
        t = u_sec - b * np.log1p(-np.log(q) / c)
    return np.where(q <= 1, t, np.nan)


def interval(v, levels) -> dict:
    """Percentile intervals of the finite values, one (lo, hi) per level."""
    v = v[np.isfinite(v)]
    return {L: (tuple(np.percentile(v, [50 * (1 - L), 50 * (1 + L)]))
                if v.size >= MIN_DRAWS else (np.nan, np.nan)) for L in levels}


def draws(B, event, sex):
    d = B[(B["event"] == event) & (B["sex"] == sex)]
    return d.u_sec.to_numpy(), d.zeta.to_numpy(), d.c.to_numpy(), d.b.to_numpy()


def n_season(f) -> float:
    return float(np.mean([f[f"n_{y}"] for y in YEARS]))


def pool_key(event: str, sex: str) -> str:
    """The event column of gompertz_fit.csv: 'mile' is 1600m boys, 1500m girls."""
    event = event.lower()
    if event == "mile":
        return "1600m" if sex == "m" else "1500m"
    if event in ("1600m", "1500m") and event != ("1600m" if sex == "m" else "1500m"):
        raise SystemExit(f"{event} {sex}: the mile pool is 1600m boys, 1500m girls")
    return event


# ---------------------------------------------------------------------------
# counts
# ---------------------------------------------------------------------------
def build_counts() -> None:
    """Every distinct time per pool, with athlete-seasons at it per season.
    The same pools (load_pool) the fits used, so n matches gompertz_fit.csv."""
    parts = []
    for sex in ("m", "f"):
        for ev in EVENTS:
            df, _ = load_pool(ev, sex, years=YEARS, region="us")
            # 4 decimals, not 2: converted mile marks (1500 m -> 1600 m etc.)
            # are not on the 0.01 s grid, and rounding them moves counts.
            tab = (df.assign(time_s=df["seconds"].round(4))
                     .groupby(["time_s", "year"]).size().unstack(fill_value=0)
                     .reindex(columns=list(YEARS), fill_value=0))
            tab.columns = [f"k_{y}" for y in YEARS]
            parts.append(tab.reset_index().assign(event=pool_name(ev, sex), sex=sex))
            print(f"  counted {pool_name(ev, sex)} {sex}: {len(df):,} marks", flush=True)
    out = pd.concat(parts, ignore_index=True)
    out[["event", "sex", "time_s"] + [f"k_{y}" for y in YEARS]].to_csv(COUNTS, index=False)
    print(f"  wrote {COUNTS}")


class Counts:
    """Cumulative counts per pool: how many athlete-seasons ran t or faster."""

    def __init__(self, F):
        if not COUNTS.exists():
            build_counts()
        C = pd.read_csv(COUNTS)
        self.pools = {}
        for (ev, sx), g in C.groupby(["event", "sex"]):
            g = g.sort_values("time_s")
            cum = {y: np.cumsum(g[f"k_{y}"].to_numpy()) for y in YEARS}
            self.pools[(ev, sx)] = (g["time_s"].to_numpy(), cum)
            n = sum(int(c[-1]) for c in cum.values())
            if (ev, sx) in F.index and n != int(F.loc[(ev, sx), "n"]):
                raise SystemExit(f"{COUNTS.name}: {ev} {sx} has {n:,} marks, the fit "
                                 f"{int(F.loc[(ev, sx), 'n']):,}; rerun --build-counts")

    def at(self, key, t) -> dict:
        """k per season and stacked at t or faster, and the stacked n."""
        times, cum = self.pools[key]
        i = np.searchsorted(times, t + EPS, side="right")
        k = {y: int(cum[y][i - 1]) if i else 0 for y in YEARS}
        n = {y: int(cum[y][-1]) for y in YEARS}
        return {"k": sum(k.values()), "n": sum(n.values()), "k_y": k, "n_y": n}

    def time_at_share(self, key, share) -> float:
        """The slowest time whose 'this fast or faster' share is <= share:
        the counted equally rare time."""
        times, cum = self.pools[key]
        tot = sum(cum[y] for y in YEARS)
        i = np.searchsorted(tot, share * tot[-1], side="right")
        return float(times[max(i - 1, 0)])


def poisson_ci(k: int, level: float = 0.95) -> tuple[float, float]:
    """Exact (Garwood) interval for a Poisson mean, given k events."""
    a = 1 - level
    lo = chi2.ppf(a / 2, 2 * k) / 2 if k else 0.0
    return lo, chi2.ppf(1 - a / 2, 2 * k + 2) / 2


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    fit_p, boot_p = POOLED_GOMPERTZ / "gompertz_fit.csv", POOLED_GOMPERTZ / "gompertz_boot.csv"
    if not boot_p.exists():
        raise SystemExit(f"{boot_p} missing: run stages/04_pooled_fit/gompertz_pooled.py")
    F = pd.read_csv(fit_p)
    F["zeta"] = F["top_pct"] / 100
    return F.set_index(["event", "sex"]), pd.read_csv(boot_p)


def query(F, B, C, event, sex, t, levels, equiv=True) -> dict:
    key = (pool_key(event, sex), sex)
    if key not in F.index:
        raise SystemExit(f"no Gompertz fit for {key[0]} {sex}")
    f = F.loc[key]
    rp = float(return_period(t, f.u_sec, f.zeta, f.c, f.b))
    rb = return_period(t, *draws(B, *key))
    cnt = C.at(key, t) if C else None
    row = {"event": key[0], "sex": sex, "time_s": t, "u_sec": f.u_sec, "rp": rp,
           "n_season": n_season(f), "draws": f"{np.isfinite(rb).sum()}/{rb.size}",
           "ci": interval(rb, levels) if np.isfinite(rp) else {}, "equiv": [],
           "count": cnt}
    if cnt:
        lo, hi = poisson_ci(cnt["k"])
        cnt["rp"] = cnt["n"] / cnt["k"] if cnt["k"] else np.inf
        cnt["ci"] = (cnt["n"] / hi, cnt["n"] / lo if lo else np.inf)
        # The model's answer, when it has one, must sit inside the count's noise.
        cnt["agrees"] = (not np.isfinite(rp)) or cnt["ci"][0] <= rp <= cnt["ci"][1]
    # The headline: the model faster than u, the count slower.
    row["rp_used"] = rp if np.isfinite(rp) else (cnt["rp"] if cnt else np.nan)
    row["per_season"] = row["n_season"] / row["rp_used"]
    if not (equiv and np.isfinite(row["rp_used"])):
        return row
    # The equally rare time in each other event of the same sex: its model
    # when the time falls in its tail, its counts when it does not.
    for ev in EVENTS:
        other = pool_name(ev, sex)
        if other == key[0]:
            continue
        g = F.loc[(other, sex)]
        R = row["rp_used"]
        te = float(equal_rarity_time(R, g.u_sec, g.zeta, g.c, g.b))
        e = {"event": other, "time_s": te, "u_sec": g.u_sec, "n_season": n_season(g),
             "ci": {}, "counted": False}
        if np.isfinite(te):
            e["ci"] = interval(equal_rarity_time(R, *draws(B, other, sex)), levels)
        elif C:
            e["time_s"], e["counted"] = C.time_at_share((other, sex), 1 / R), True
        row["equiv"].append(e)
    return row


def _n(v: float) -> str:
    if not np.isfinite(v):
        return "--"
    return f"{v:,.0f}" if v >= 100 else f"{v:,.1f}"


def _c(v: float) -> str:
    """An expected count: whole numbers when large, 2 significant digits when small."""
    return f"{v:,.0f}" if v >= 10 else f"{v:.2g}"


def _t(s: float) -> str:
    if not np.isfinite(s):
        return "--"
    m, sec = divmod(s, 60)
    return f"{int(m)}:{sec:05.2f}" if m else f"{sec:.2f}"


def _ivs(ci: dict, fmt) -> str:
    return "  ".join(f"{L:.0%} [{fmt(lo)} - {fmt(hi)}]" for L, (lo, hi) in ci.items())


def show(rows: list[dict]) -> None:
    for r in rows:
        who = "boys" if r["sex"] == "m" else "girls"
        c = r["count"]
        print(f"\n{r['event']} {who}  {_t(r['time_s'])}")
        # Each season on its own: k of n, and its own "1 in X".
        per_year = ", ".join(
            f"{y}: {c['k_y'][y]:,} of {c['n_y'][y]:,}"
            + (f" = 1 in {_n(c['n_y'][y] / c['k_y'][y])}" if c["k_y"][y] else "")
            for y in YEARS) if c else ""
        if np.isfinite(r["rp"]):
            print(f"  1 in {_n(r['rp'])} athlete-seasons    {_ivs(r['ci'], _n)}"
                  f"    (model; draws {r['draws']})")
            if c:
                flag = "" if c["agrees"] else "   <-- model outside the count's 95% range"
                rng = (f"95% [{_n(c['ci'][0])} - {_n(c['ci'][1])}]" if c["k"] else
                       f"95%: rarer than 1 in {_n(c['ci'][0])}")
                rp_c = f"1 in {_n(c['rp'])}" if c["k"] else "none this fast"
                print(f"  counted: {rp_c}  {rng}    ({c['k']:,} of {c['n']:,}){flag}")
        elif c:
            print(f"  1 in {_n(c['rp'])} athlete-seasons    95% [{_n(c['ci'][0])} - "
                  f"{_n(c['ci'][1])}]    (counted: slower than the model's u = "
                  f"{_t(r['u_sec'])})")
        else:
            print(f"  outside the tail model (u = {_t(r['u_sec'])}), and no counts")
            continue
        src = "the model expects" if np.isfinite(r["rp"]) else "counted"
        print(f"  field: ~{round(r['n_season'], -2):,.0f} {who} run the {r['event']} each"
              f" season -> {src} ~{_c(r['per_season'])} this fast per season"
              + (f"  ({per_year})" if per_year else ""))
        if r["equiv"]:
            print(f"  equally rare, {who}:")
        for e in r["equiv"]:
            if not np.isfinite(e["time_s"]):
                print(f"    {e['event']:<6} slower than {e['event']}'s threshold "
                      f"({_t(e['u_sec'])}): outside its tail model")
                continue
            how = "(counted)" if e["counted"] else _ivs(e["ci"], _t)
            print(f"    {e['event']:<6} {_t(e['time_s']):>8}   {how}"
                  f"   ~{_c(e['n_season'] / r['rp_used'])} of "
                  f"~{round(e['n_season'], -2):,.0f} per season")


def check(F, B) -> None:
    """The closed form must equal TailFit.return_period, and must reproduce
    gompertz_queries.csv (point and 95% interval) for the rank-k rows."""
    Q = pd.read_csv(POOLED_GOMPERTZ / "gompertz_queries.csv")
    worst = 0.0
    for q in Q[Q["kind"].str.startswith("rank")].itertuples():
        f = F.loc[(q.event, q.sex)]
        tf = TailFit(model="gompertz", u=-f.u_sec, zeta=f.zeta, n_exceed=int(f.N_u),
                     n_total=int(f.n), params={"c": f.c, "b": f.b})
        r = query(F, B, None, q.event, q.sex, q.time_s, [0.95], equiv=False)
        lo, hi = r["ci"][0.95]
        # The inverse must land back on the queried time.
        back = float(equal_rarity_time(r["rp"], f.u_sec, f.zeta, f.c, f.b))
        for got, want in [(r["rp"], float(tf.return_period(q.time_s))),
                          (r["rp"], q.rp), (lo, q.rp_lo), (hi, q.rp_hi),
                          (back, q.time_s)]:
            worst = max(worst, abs(got / want - 1))
    print(f"  {len(Q[Q['kind'].str.startswith('rank')])} rank rows; "
          f"worst relative difference {worst:.2e}")
    if worst > 1e-9:
        raise SystemExit("  CHECK FAILED")
    print("  check passed")


def main() -> None:
    ap = argparse.ArgumentParser(description="Score times with the national Gompertz fits.")
    ap.add_argument("event", nargs="?")
    ap.add_argument("sex", nargs="?", choices=["m", "f"])
    ap.add_argument("times", nargs="*")
    ap.add_argument("--csv", help="batch file with columns event, sex, time")
    ap.add_argument("--level", default="0.8,0.95", help="interval levels, e.g. 0.68,0.95")
    ap.add_argument("--no-equiv", action="store_true",
                    help="skip the equally rare times in the other events")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--build-counts", action="store_true",
                    help="rewrite gompertz_counts.csv from the pools (about a minute)")
    args = ap.parse_args()
    F, B = load()
    if args.build_counts:
        build_counts()
        if not (args.times or args.csv):
            return
    if args.check:
        return check(F, B)
    levels = [float(v) for v in args.level.split(",")]
    jobs = [(args.event, args.sex, t) for t in args.times]
    if args.csv:
        jobs += [(r.event, r.sex, str(r.time)) for r in pd.read_csv(args.csv).itertuples()]
    if not jobs:
        ap.error("give EVENT SEX TIME [TIME ...] or --csv FILE")
    C = Counts(F)
    show([query(F, B, C, e, s, parse_time(t), levels, not args.no_equiv)
          for e, s, t in jobs])


if __name__ == "__main__":
    main()
