"""
northeast.py
============
The northeast nine as one pooled field, for any stage that wants it.

Stage 04 (`pool_data.load_pool`) is the inferential version: strict time
parsing, a slow-side outlier fence, athlete dedupe, coverage checks. This is the
descriptive version for stage 02's exploratory plots -- the same files and the
same mile rule, and one piece of cleaning shared with stage 04: the one-sided
slow-side log-IQR fence. Without it a single units error ("36:24.00" filed as a
200 m) stretches a pooled histogram's x-axis to half an hour; nine states pool
nine states' junk. The fence removes 0.3-1.2% of each pool, all slow-side, and
cannot touch the fast tail. No dedupe -- these are season-best lists.

Keeping the pooling rule here rather than in stage 04 means stage 02 never
imports from a later stage.

The mile is the one non-trivial event: per state and sex the variant with the
most rows (src/distances.main_mile_slug), converted onto 1600 m for boys and
1500 m for girls (src/distances.factors_for).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from distances import factors_for, main_mile_slug, target_name
from util import parse_time

# The nine states with both sprint and mile lists for both sexes in 2025 and
# 2026. Stage 04 imports this rather than keeping its own copy.
NORTHEAST = ("CT", "MA", "ME", "NH", "NJ", "NY", "PA", "RI", "VT")

EVENTS = ("100m", "200m", "400m", "800m", "mile")


def pool_label(event: str, sex: str) -> str:
    """Panel title: '100m' ... '800m', or '1600m eq.' / '1500m eq.' for the mile."""
    return f"{target_name(sex)} eq." if event == "mile" else event


def slow_fence(seconds: np.ndarray, k: float = 2.0) -> float:
    """exp(Q3_log + k * IQR_log): stage 04's fence (pool_data.log_iqr_fence),
    on logs because times are right-skewed, one-sided because a time cannot be
    erroneously fast."""
    q1, q3 = np.percentile(np.log(seconds), [25, 75])
    return float(np.exp(q3 + k * (q3 - q1)))


def pooled_rows(year_dir: Path, sex: str, event: str,
                states=NORTHEAST, fence_k: float | None = 2.0) -> pd.DataFrame:
    """Every state's rows for one event, stacked.

    Columns: the scraped six (name,time,team,grade,state,date) plus `state_dir`
    (the folder it came from -- the `state` column is often blank) and
    `seconds`, already converted for the mile. Rows whose time cannot be read
    are dropped, then slow-side junk beyond the fence (fence_k=None disables it).
    The number fenced is in `df.attrs["n_fenced"]`.
    """
    frames = []
    for st in states:
        d = Path(year_dir) / st / sex
        if event == "mile":
            slug = main_mile_slug(d)
            if slug is None:
                continue
            factor = factors_for(sex)[slug]
        else:
            slug, factor = f"{event[:-1]}r", 1.0
        path = d / f"{slug}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str, encoding="utf-8").fillna("")
        df["seconds"] = df["time"].map(parse_time) * factor
        df["state_dir"] = st
        frames.append(df[np.isfinite(df["seconds"]) & (df["seconds"] > 0)])
    if not frames:
        raise FileNotFoundError(f"no {event} files for sex={sex} under {year_dir}")
    pool = pd.concat(frames, ignore_index=True)
    n_fenced = 0
    if fence_k is not None:
        keep = pool["seconds"] <= slow_fence(pool["seconds"].to_numpy(), fence_k)
        n_fenced = int((~keep).sum())
        pool = pool[keep].reset_index(drop=True)
    pool.attrs["n_fenced"] = n_fenced
    return pool
