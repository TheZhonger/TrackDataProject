from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy.stats import chi2
import streamlit as st

DATA = Path(__file__).resolve().parent / "data"   # works from any launch folder
YEARS = (2025, 2026)
EPS = 1e-6        # times are floats: 117.29 may be stored as 117.28999999
MIN_DRAWS = 20    # fewer valid bootstrap draws than this -> no interval
EVENTS = ["100m", "200m", "400m", "800m", "mile"]

@st.cache_data
def load_data():
    fit = pd.read_csv(DATA / "gompertz_fit.csv")
    fit["zeta"] = fit["top_pct"] / 100
    boot = pd.read_csv(DATA / "gompertz_boot.csv")
    counts = pd.read_csv(DATA / "gompertz_counts.csv")
    return fit, boot, counts

def parse_time(raw) -> float:
    """'10.52' -> 10.52, '1:57.29' -> 117.29; anything else -> nan."""
    s = re.sub(r"[^0-9:.]", "", str(raw).strip())
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    return float("nan")


def fmt_time(sec: float) -> str:
    """117.29 -> '1:57.29', 10.31 -> '10.31', 3725.5 -> '1:02:05.50'."""
    if not np.isfinite(sec):
        return "--"
    cs = int(round(sec * 100))

    total_s, cs = divmod(cs, 100)
    m, s = divmod(total_s, 60)
    h, m = divmod(m, 60)

    if h:
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    if m:
        return f"{m}:{s:02d}.{cs:02d}"
    return f"{s}.{cs:02d}"

def pool_event(event: str, sex: str) -> str:
    """The 'mile' pool is 1600m for boys and 1500m for girls."""
    if event == "mile":
        return "1600m" if sex == "m" else "1500m"
    return event

def return_period(t, u_sec, zeta, c, b):
    """RP(t) = 1/S(t). nan where t is slower than u (outside the model).
    Works on one number or on numpy arrays (e.g. all 200 draws at once)."""
    t = np.asarray(t, dtype=float)
    y = u_sec - t                                  # seconds faster than u
    s = zeta * np.exp(-c * np.expm1(np.maximum(y, 0) / b))
    with np.errstate(divide="ignore"):
        return np.where(y >= 0, 1.0 / s, np.nan)


def equal_rarity_time(rp, u_sec, zeta, c, b):
    """The inverse: the time t with RP(t) = rp. nan if that time is slower than u."""
    q = 1.0 / (np.asarray(rp, dtype=float) * zeta)   # share of the tail this fast
    with np.errstate(divide="ignore", invalid="ignore"):
        t = u_sec - b * np.log1p(-np.log(q) / c)
    return np.where(q <= 1, t, np.nan)


def interval(values, level):
    """The middle `level` share of the finite values: (lo, hi)."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < MIN_DRAWS:
        return (np.nan, np.nan)
    return tuple(np.percentile(v, [50 * (1 - level), 50 * (1 + level)]))

def model_answer(fit, boot, ev, sex, t, levels=(0.8, 0.95)):
    f = fit[(fit.event == ev) & (fit.sex == sex)].iloc[0]
    rp = float(return_period(t, f.u_sec, f.zeta, f.c, f.b))
    d = boot[(boot.event == ev) & (boot.sex == sex)]
    rp_draws = return_period(t, d.u_sec.values, d.zeta.values, d.c.values, d.b.values)
    return rp, {L: interval(rp_draws, L) for L in levels}

# Counts

def pool_counts(counts, ev, sex):
    """Sorted times, and per season the cumulative count at that time or faster."""
    g = counts[(counts.event == ev) & (counts.sex == sex)].sort_values("time_s")
    cum = {y: np.cumsum(g[f"k_{y}"].values) for y in YEARS}
    return g.time_s.values, cum


def count_at(times, cum, t):
    """k (at t or faster) and n, per season and in total."""
    i = np.searchsorted(times, t + EPS, side="right")   # number of distinct times <= t
    k = {y: int(cum[y][i - 1]) if i else 0 for y in YEARS}
    n = {y: int(cum[y][-1]) for y in YEARS}
    return k, n


def poisson_ci(k, level=0.95):
    """Exact (Garwood) interval for the mean of a Poisson count k."""
    a = 1 - level
    lo = chi2.ppf(a / 2, 2 * k) / 2 if k else 0.0
    hi = chi2.ppf(1 - a / 2, 2 * k + 2) / 2
    return lo, hi


def counted_answer(counts, ev, sex, t, level=0.95):
    times, cum = pool_counts(counts, ev, sex)
    k, n = count_at(times, cum, t)
    K, N = sum(k.values()), sum(n.values())
    lo, hi = poisson_ci(K, level)
    return {
        "k": K, "n": N,
        "rp": N / K if K else np.inf,
        "ci": (N / hi, N / lo if lo else np.inf),   # more marks -> smaller RP
        "per_season": {y: (k[y], n[y], n[y] / k[y] if k[y] else np.inf) for y in YEARS},
    }

def time_at_share(times, cum, share):
    """The slowest time with (marks at it or faster) / n <= share."""
    tot = sum(cum[y] for y in YEARS)
    i = np.searchsorted(tot, share * tot[-1], side="right")
    return float(times[max(i - 1, 0)])

def field_size(f):
    """Athlete-seasons in a typical season: the mean of the two seasons."""
    return (f.n_2025 + f.n_2026) / 2


def query(fit, boot, counts, event, sex, t, levels=(0.8, 0.95)):
    ev = pool_event(event, sex)
    f = fit[(fit.event == ev) & (fit.sex == sex)].iloc[0]
    out = {"event": ev, "sex": sex, "t": t, "u": f.u_sec,
           "counted": counted_answer(counts, ev, sex, t)}

    rp_model, ci_model = model_answer(fit, boot, ev, sex, t, levels)
    if np.isfinite(rp_model):                       # t <= u: the model leads
        out.update(source="model", rp=rp_model, ci=ci_model)
    else:                                           # t > u: the count leads
        c = out["counted"]
        out.update(source="counted", rp=c["rp"], ci={0.95: c["ci"]})
    out["field"] = field_size(f)
    out["per_season"] = out["field"] / out["rp"]

    # the equally rare time in the other events of the same sex
    out["equiv"] = []
    for other_event in EVENTS:
        other = pool_event(other_event, sex)
        if other == ev:
            continue
        g = fit[(fit.event == other) & (fit.sex == sex)].iloc[0]
        te = float(equal_rarity_time(out["rp"], g.u_sec, g.zeta, g.c, g.b))
        how = "model"
        if not np.isfinite(te):                     # slower than that pool's u
            times, cum = pool_counts(counts, other, sex)
            te, how = time_at_share(times, cum, 1 / out["rp"]), "counted"
        out["equiv"].append({"event": other, "time": te, "how": how,
                             "per_season": field_size(g) / out["rp"]})
    return out
