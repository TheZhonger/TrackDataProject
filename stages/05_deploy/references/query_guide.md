# Query guide: the Gompertz data in a Streamlit app

This guide shows how to turn the 3 CSV files in `data/` into the same answers as the
command-line tool:

```bash
.venv/bin/python stages/04_pooled_fit/gompertz_query.py 800m m 1:57.29
```

- Section 3 has the code to copy: small functions that do not need Streamlit.
- Section 4 shows how to connect them to Streamlit. The app layout is your decision.
- The reference implementation is `stages/04_pooled_fit/gompertz_query.py`.
  When this guide and that file differ, that file is correct.

---

## 1. The three files

All three have one block of rows for each **pool**. A pool is one event × sex, and
there are 10 pools. The event values are `100m 200m 400m 800m`, `1600m` (boys) and
`1500m` (girls). The sex is `m` or `f`.

### `gompertz_fit.csv`: the model, one row per pool

| Column | Meaning | Example (100m, m) |
|---|---|---|
| `u_sec` | the threshold u in seconds. The model is valid only at u or faster | 11.30 |
| `top_pct` | the share of athlete-seasons at u or faster, in %. ζ = top_pct / 100 | 6.197 |
| `c`, `b` | the 2 Gompertz parameters | 2.204, 0.7907 |
| `n` | athlete-seasons in the pool, 2025 + 2026 | 384,598 |
| `n_2025`, `n_2026` | athlete-seasons in each season | 183,612, 200,986 |

The other columns (`c_lo`, `b_hi`, `fs_outcome` ...) are diagnostics. The app does not
need them. **Do not** use `c_lo`/`c_hi` and `b_lo`/`b_hi` to make an interval: c and b
move together, so their separate ranges do not combine into an interval for a return
period.

### `gompertz_boot.csv`: 200 refits per pool, for the intervals

| Column | Meaning |
|---|---|
| `draw` | 0 … 199 |
| `u_sec`, `zeta`, `c`, `b` | the fit of that bootstrap draw (each draw has its own u) |

### `gompertz_counts.csv`: the real data, for times slower than u

| Column | Meaning | Example |
|---|---|---|
| `time_s` | one distinct time in the pool, in seconds (up to 4 decimals) | 270.0 |
| `k_2025`, `k_2026` | athlete-seasons with exactly this time, in each season | 6, 8 |

The rows are not cumulative. You add them up yourself (section 3.6). Some times have 4
decimals (for example 270.0021). These are converted mile marks (1500 m → 1600 m and the
reverse). Keep them as they are.

---

## 2. The idea

**Athlete-season.** One athlete's best mark in one event in one season. With 2025 and
2026 stacked, an athlete who ran both seasons counts twice.

**Return period, "1 in X".** S(t) is the share of athlete-seasons at time t or faster.
The return period is RP = 1 / S(t). "1 in 57" means that 1 in 57 season-best marks is this
fast or faster. RP is per runner, so the same RP in two events means "equally rare".

**Two ways to get S(t):**

| Time t | Method | Why |
|---|---|---|
| t ≤ u (faster than the threshold) | **the Gompertz model** | few marks; a count is noisy, capped at 1 in n, and blind to the margin |
| t > u (slower than the threshold) | **count the marks** | ≥ ~1,000 marks; a count is accurate to ~3%, with no model risk |

**The model above u.** Let y = u − t, the number of seconds faster than u. Then

S(t) = ζ · exp(−c · (e^(y/b) − 1)),  RP(t) = 1 / S(t).

At t = u, y = 0 and S = ζ. Each second faster makes S smaller, faster than an
exponential would.

**The count below u.** k = the number of athlete-seasons at t or faster, so RP = n / k.

**Intervals.**
- **Model:** compute RP(t) with each of the 200 bootstrap fits. The 80% interval is the
  middle 80% of those 200 values.
- **Count:** k is a random count, so its noise follows the Poisson distribution. The exact
  (Garwood) interval for k gives an interval for n / k.
- **Levels:** an 80% interval is narrower than a 95% interval. It is not wrong; it claims
  less (it misses the true value 1 time in 5).

---

## 3. Code to copy

Put these in one module, for example `stages/05_deploy/query.py` (you choose the name).
Only `load_data` uses Streamlit. The other functions are plain Python, so you can test
them without the app.

### 3.1 Imports and constants

```python
from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy.stats import chi2

DATA = Path(__file__).resolve().parent / "data"   # works from any launch folder
YEARS = (2025, 2026)
EPS = 1e-6        # times are floats: 117.29 may be stored as 117.28999999
MIN_DRAWS = 20    # fewer valid bootstrap draws than this -> no interval
EVENTS = ["100m", "200m", "400m", "800m", "mile"]
```

`Path(__file__).resolve().parent` is the folder of your `.py` file. If your file is in a
subfolder (for example `pages/`), add one `.parent` for each level.

### 3.2 Load the data once

```python
import streamlit as st

@st.cache_data
def load_data():
    fit = pd.read_csv(DATA / "gompertz_fit.csv")
    fit["zeta"] = fit["top_pct"] / 100
    boot = pd.read_csv(DATA / "gompertz_boot.csv")
    counts = pd.read_csv(DATA / "gompertz_counts.csv")
    return fit, boot, counts
```

Streamlit runs your whole script again after every click. Without `@st.cache_data`,
it reads 2 MB of CSV each time. With it, it reads the files once and keeps the result.

### 3.3 Parse a time

```python
def parse_time(raw) -> float:
    """'10.52' -> 10.52, '1:57.29' -> 117.29; anything else -> nan."""
    s = re.sub(r"[^0-9:.]", "", str(raw).strip())
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
    except ValueError:
        pass
    return float("nan")


def fmt_time(sec: float) -> str:
    """117.29 -> '1:57.29', 10.31 -> '10.31'."""
    if not np.isfinite(sec):
        return "--"
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:05.2f}" if m else f"{s:.2f}"
```

### 3.4 Event name → pool

```python
def pool_event(event: str, sex: str) -> str:
    """The 'mile' pool is 1600m for boys and 1500m for girls."""
    if event == "mile":
        return "1600m" if sex == "m" else "1500m"
    return event
```

Girls' times for the mile pool are on the **1500 m** scale. Make this clear in the app,
for example in the label of the input box.

### 3.5 The model: return period and its inverse

```python
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
```

- `np.expm1(x)` is e^x − 1. It is more accurate than `np.exp(x) - 1` when x is small.
- The formula in `equal_rarity_time` comes from solving S(t) = 1 / RP for t.

**An example of the model with an interval:**

```python
def model_answer(fit, boot, ev, sex, t, levels=(0.8, 0.95)):
    f = fit[(fit.event == ev) & (fit.sex == sex)].iloc[0]
    rp = float(return_period(t, f.u_sec, f.zeta, f.c, f.b))
    d = boot[(boot.event == ev) & (boot.sex == sex)]
    rp_draws = return_period(t, d.u_sec.values, d.zeta.values, d.c.values, d.b.values)
    return rp, {L: interval(rp_draws, L) for L in levels}
```

A draw whose own u is faster than t gives nan, and `interval` leaves it out.

### 3.6 Times slower than u: counts

```python
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
```

How `searchsorted` works: `times` is sorted, so `searchsorted(times, t, side="right")`
gives the number of distinct times ≤ t. The cumulative count at the position before it
is k. `t + EPS` makes sure a stored 117.28999999 still counts for a query of 117.29.

**Equivalent time from counts.** This finds the time with the same share in another
pool:

```python
def time_at_share(times, cum, share):
    """The slowest time with (marks at it or faster) / n <= share."""
    tot = sum(cum[y] for y in YEARS)
    i = np.searchsorted(tot, share * tot[-1], side="right")
    return float(times[max(i - 1, 0)])
```

### 3.7 Field size and expected count

```python
def field_size(f):
    """Athlete-seasons in a typical season: the mean of the two seasons."""
    return (f.n_2025 + f.n_2026) / 2

# expected number this fast in one season = field_size(f) / rp
```

"1 in 3,969" in a field of ~192,300 means about 48 boys each season. Show both
numbers. The same RP gives a different count in each event, because the fields have
different sizes.

### 3.8 One function for everything

```python
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
```

Use it:

```python
fit, boot, counts = load_data()
r = query(fit, boot, counts, "800m", "m", parse_time("1:57.29"))
print(r["source"], round(r["rp"], 1), r["counted"]["per_season"])
```

This leaves out one thing that `gompertz_query.py` does: the intervals on the
equivalent times. To add them, apply `equal_rarity_time` to the other pool's 200 draws,
as in `model_answer`.

---

## 4. Into Streamlit

**How Streamlit runs.** Your script runs from the top to the bottom. Each time the user
changes an input, it runs again. Widgets return their current value, so you use them like
variables:

```python
event = st.selectbox("Event", EVENTS)
sex = st.radio("Sex", ["m", "f"], horizontal=True)
raw = st.text_input("Time (10.31 or 1:57.29)")
```

Widgets that fit this app:

| Need | Widget |
|---|---|
| choose event / sex | `st.selectbox`, `st.radio` |
| enter a time | `st.text_input`, then `parse_time` (show `st.error` if it is nan) |
| the headline "1 in X" | `st.metric(label, value)` |
| the equivalent-times table | `st.dataframe(pd.DataFrame(r["equiv"]))` |
| explanations | `st.markdown`, `st.caption`, `st.expander` |
| several sections | `st.tabs`, or a `pages/` folder (multi-page app) |
| choose interval levels | `st.multiselect` or `st.slider` |

Run it from the project root:

```bash
.venv/bin/streamlit run stages/05_deploy/<your_app>.py
```

Then open http://localhost:8501.

---

## 5. Check your answers

Your app must give these values. They come from `gompertz_query.py` on 2026-10-23
(the same data as `data/`).

| Query | Source | 1 in X | Interval | Per season |
|---|---|---|---|---|
| 100m m 10.31 | model | 3,969 | 80% 3,661–4,455; 95% 3,507–4,687 | ~48 |
| 100m m 9.70 | model | 31,082,224 | 95% 16.1M–83.9M | ~0.0062 |
| 800m m 1:57.29 | counted | 57.2 | 95% 55.5–59.0 | 2025: 1,930 of 109,505; 2026: 2,063 of 118,979 |
| 1600m m 4:30 | counted | 21.5 | 95% 21.1–21.9 | 2025: 4,826 of 100,651; 2026: 4,910 of 108,716 |

Equivalent times for 100m m 10.31: 200m 20.87, 400m 46.73, 800m 1:50.19, 1600m 4:04.51.
For 800m m 1:57.29: 100m 10.94 (model), 200m 22.20 (counted), 400m 49.81 (model),
1600m 4:21.99 (counted).

---

## 6. Pitfalls

1. **Float times.** Do not test `time_s == 117.29`. Use `searchsorted` with `EPS`, as in
   3.6.
2. **nan from the model.** A time slower than u gives nan. Check it with
   `np.isfinite(rp)` before you format it, and go to the counts.
3. **k = 0.** If no mark is this fast, RP = n/k divides by zero. Show
   "none this fast; rarer than 1 in N/hi" instead.
4. **The girls' mile is 1500 m.** A girls' 1600 m or mile time gives the wrong answer.
5. **Pandas rows.** `fit[...].iloc[0]` gives one row (a Series). Read its values as
   `f.u_sec`, `f.c` and so on.
6. **Stale data.** After a refit in stage 04, copy the 3 CSVs into `data/` again. Then
   clear the cache: press **C** in the app, or restart it.
7. **Far past the record.** The model's number there is an extrapolation. Show the
   interval, and say it in the app.
