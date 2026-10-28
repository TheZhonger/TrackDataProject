"""
pool_data.py
============
Load the northeast scrape and pool it across states into ONE distribution
per event x sex -- for one season (2026, 2025) or for several seasons stacked
(2025-2026; see "Pooling seasons" below).

Why pool at all
---------------
A single state's list is thin at the top. NH has 948 boys in the 100 m; its
fastest three marks are the entire tail, and a GPD fitted to them is a fit to
three data points. Pooling nine states buys a tail deep enough to estimate a
shape parameter from.

What pooling costs, stated plainly
----------------------------------
A pool of nine states is a MIXTURE, not a sample from one population. Its tail
is dominated by whichever component reaches furthest -- here NY and PA, which
together are half the rows. Pickands-Balkema-de Haan still applies (a mixture is
just another distribution, and the theorem does not care which one), so the GPD
is still the right limiting form. But read the fitted tail as describing the
deep states more than the thin ones. `plot_pooled.py`'s per-state figure is what
makes that visible rather than assumed.

Events
------
Five per sex: 100, 200, 400 and 800 m, each read straight from that event's
restricted list, and the metric mile.

The mile problem
----------------
There is no national "1600 m" (see stages/01_scrape/references/scraping.md
section 3). Each state x sex contests one of 1600 m, the mile or 1500 m. Per
state and sex the list with the most performances wins, and it is converted
to the sex's TARGET distance: 1600 m for boys, 1500 m for girls (NY, the
largest girls' field, runs the 1500). The rule and the factors live in
src/distances.py, shared with stage 03:

    boys  -> 1600 m :  mile x 0.99419 (distance ratio), 1500 x 1.070806 (Riegel)
    girls -> 1500 m :  1600 x 0.933877, mile x 0.928130 (both Riegel)

The analysis key for this event is "mile"; `pool_name(event, sex)` gives the
distance it is expressed in ("1600m" / "1500m") for labels and filenames.

Pooling seasons
---------------
`years=(2025, 2026)` stacks both seasons into one pool. The unit stays the
ATHLETE-SEASON: a junior's 2025 mark and the same athlete's 2026 mark are two
rows, so the dedupe key carries the year and a return period still reads "one
athlete-season in N" -- the same unit as a single-season fit, and directly
comparable with it. Doubling the seasons doubles n; it does not double the
return period of a given time.

What it costs: those two rows are NOT independent. 30-45% of each season's
athletes appear in the other, and they are over-represented in the fast tail
(33-48% of the top 10%), because a fast sophomore is usually a fast junior.
The point estimates are still fine (maximising the likelihood as if rows were
independent stays consistent; it just over-counts information), but an
interval built by resampling ROWS treats each repeat athlete as two
independent draws and comes out too narrow. Hence the `athlete` column: a
cross-season id that gpd_pooled hands to the bootstrap so it resamples whole
athletes instead (a cluster bootstrap).

Each season resolves its own mile file per state, so a state that switched
distance between seasons is still converted correctly.

Input : stages/01_scrape/output/<year>/<ST>/<sex>/<event>.csv, columns name,time,team,grade,state,date
Output: a tidy frame with a converted `seconds` column, plus a meta dict that
        records every judgement call made along the way.

Run `python src/pool_data.py` to print the resolution table, the outlier
fence, the dropped rows and the final pool sizes. That is the cheap correctness
check to run before fitting anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Deliberately no matplotlib import anywhere in this module. `gpd_tail` calls
# matplotlib.use("Agg") at import time, and a library that quietly switches the
# caller's backend is a nasty thing to debug -- so this stays numpy/pandas only.


# ======================================================================
# PATHS AND SCOPE
# ======================================================================

# Every location comes from src/paths.py, so this stage reads stage 01's output
# and writes only into its own output/, wherever it is launched from.
# This module lives in src/ (moved from stages/04_pooled_fit/ on 2026-10-22 so
# stage 02 can use the same cleaned pools without importing a later stage), so
# its siblings -- paths, util, distances, regions -- import directly.
from paths import POOLED_OUT, pooled_dataset, scrape_year  # noqa: E402

OUT_DIR = POOLED_OUT                   # stage 04's output root (see output/README.md)

# Seasons that have a complete northeast scrape. 2026 is the default
# everywhere, so a bare run reproduces the original single-season analysis.
YEARS = (2025, 2026)
DEFAULT_YEARS = (2026,)
DATA_ROOT = scrape_year(2026)


def parse_years(text: str) -> tuple[int, ...]:
    """'2026' -> (2026,), '2025,2026' -> (2025, 2026). Sorted, de-duplicated."""
    years = tuple(sorted({int(y) for y in str(text).split(",") if y.strip()}))
    bad = [y for y in years if y not in YEARS]
    if not years or bad:
        raise ValueError(f"years must be drawn from {YEARS}, got {text!r}")
    return years


def dataset_name(years, region: str = "northeast") -> str:
    """(2026,) -> '2026'; (2025, 2026) -> '2025-2026'; the national scope adds
    a prefix, 'us-2026'. Names the output folder. Northeast names carry no
    prefix so the folders written before the national run never moved."""
    name = "-".join(str(y) for y in sorted(years))
    return name if region == "northeast" else f"{region}-{name}"


def dataset_dirs(years, region: str = "northeast") -> dict[str, Path]:
    """Where one dataset's outputs go: output/<dataset>/ plus its figure dirs."""
    out = pooled_dataset(dataset_name(years, region))
    return {"out": out, "hist": out / "figures" / "histograms",
            "gpd": out / "figures" / "gpd"}

# The nine northeast states that have both a sprint list and a mile list for
# both sexes. WY (1600 only, boys only) and the DC/VT 3200 m files are scraper
# test artifacts and are deliberately out of scope: if the five events'
# pools rested on different state sets, their return periods would be counting
# different populations and could not be compared -- which is the entire point
# of the exercise.
from northeast import NORTHEAST  # noqa: E402  (single source: src/northeast.py)
# Pool scopes: "northeast" (the nine above, the default) or "us" (all 51).
# A pool's states must all come from one scope -- see src/regions.py.
from regions import REGIONS  # noqa: E402

SEXES = ("m", "f")

# Everything is read as UTF-8 explicitly. The 2026 scrape contains bytes that Windows'
# cp1252 default cannot decode, and the failure is a hard UnicodeDecodeError
# partway through a file, not a mangled character you might notice later.
ENCODING = "utf-8"

# athletic.net's own placeholder rows: four "Test Athlete #N" entries sit in
# 2026/MA/m/100r.csv, all on team "Acton-Boxborough Reg", all dated Apr 13.
# They are removed BY NAME rather than left to the outlier fence, because a fake
# record carrying a plausible time would sail straight through a distributional
# filter -- the whole value of a known-junk rule is that it does not depend on
# the junk being extreme. Anchored and exact: plenty of real athletes in this
# data are named Testa, Testone, Volpintesta or Testimony.
_TEST_ATHLETE_RE = re.compile(r"^\s*test athlete\b", re.IGNORECASE)

# Cross-event coverage check -- see coverage_check() for the reasoning.
COVERAGE_REF_EVENT = "100m"
COVERAGE_MIN_RATIO = 0.35


# ======================================================================
# DISTANCE CONVERSION
# ======================================================================

from distances import RIEGEL_EXPONENT, factors_for, target_name  # noqa: E402,F401

# Kept as names because plot_pooled and the self-check use them; they are the
# boys' factors and come from src/distances.py, the single source of truth.
MILE_TO_1600 = factors_for("m")["1miler"]          # 0.99419, the distance ratio
M1500_TO_1600 = factors_for("m")["1500r"]          # ~ 1.070806, Riegel


@dataclass(frozen=True)
class EventSpec:
    """
    One analysis event, and every file slug that can feed it.

    `factors(sex)` maps a filename stem to the multiplier that puts it on this
    event's scale for that sex. A factor of 1.0 means the file already IS the
    event. Sprints and the 800 are one slug at 1.0 for both sexes; the mile is
    three slugs whose factors depend on the sex's target distance.
    """
    key: str
    label: str
    slugs: tuple[str, ...]
    per_sex_target: bool = False

    def factors(self, sex: str) -> dict[str, float]:
        if self.per_sex_target:
            return factors_for(sex)
        return {slug: 1.0 for slug in self.slugs}

    def name(self, sex: str) -> str:
        """Distance this pool is expressed in: '100m', or '1600m'/'1500m'."""
        return target_name(sex) if self.per_sex_target else self.key

    def label_for(self, sex: str) -> str:
        if self.per_sex_target:
            return f"{target_name(sex)[:-1]} m equivalent"
        return self.label


EVENTS: dict[str, EventSpec] = {
    "100m": EventSpec(key="100m", label="100 m", slugs=("100r",)),
    "200m": EventSpec(key="200m", label="200 m", slugs=("200r",)),
    "400m": EventSpec(key="400m", label="400 m", slugs=("400r",)),
    "800m": EventSpec(key="800m", label="800 m", slugs=("800r",)),
    # The metric mile: 1600r / 1miler / 1500r, onto 1600 m (boys) or 1500 m
    # (girls). See src/distances.py.
    "mile": EventSpec(key="mile", label="mile", per_sex_target=True,
                      slugs=("1600r", "1miler", "1500r")),
}


def pool_name(event: str, sex: str) -> str:
    """'100m' ... '800m', or '1600m' (boys) / '1500m' (girls) for the mile."""
    return EVENTS[event].name(sex)


# ======================================================================
# TIME PARSING
# ======================================================================

# Matches "10.31", "1:52.34", "4:15", "10.31a", "  9.98h  ".
# Group 1 = optional minutes before a colon, group 2 = seconds.
# The trailing [a-zA-Z]* soaks up timing-method suffixes (a = auto, h = hand).
_TIME_RE = re.compile(r"^\s*(?:(\d+):)?(\d+(?:\.\d+)?)\s*[a-zA-Z]*\s*$")


def parse_time(raw) -> float:
    """Turn a messy time cell into a float number of seconds, or NaN.

    Kept byte-for-byte compatible with `stages/03_tail_fit/gpd_tail.py`'s version so a
    pooled fit and a single-file fit never disagree about what a row means.
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if np.isfinite(raw) else np.nan

    # Deliberately NOT stripping commas: "2:05,4" would silently become 174.0
    # instead of 125.4. A NaN you can see beats a wrong number you can't.
    s = str(raw).strip()
    if not s:
        return np.nan

    m = _TIME_RE.match(s)
    if m is None:
        return np.nan

    minutes, seconds = m.groups()
    total = float(seconds)
    if minutes is not None:
        total += 60.0 * int(minutes)
    return total


def fmt_time(x, _pos=None) -> str:
    """Seconds as SS.ss under a minute, M:SS.ss above. Also a matplotlib formatter."""
    if x is None or not np.isfinite(x):
        return "--"
    if x < 60:
        return f"{x:.2f}"
    minutes, seconds = divmod(float(x), 60.0)
    return f"{int(minutes)}:{seconds:05.2f}"


# ======================================================================
# OUTLIER FENCE
# ======================================================================

def log_iqr_fence(seconds: np.ndarray, k: float = 2.0) -> float:
    """
    One-sided (slow-side) Tukey fence, computed on log time.

        fence = exp( Q3_log + k * IQR_log )

    Two deliberate choices.

    ON LOGS, because race times are right-skewed and roughly lognormal through
    the body -- the same assumption `threshold_select.py`'s mixture model rests
    on. Tukey's fence assumes rough symmetry; applied to raw seconds it
    systematically over-flags the long side simply for being long.

    ONE-SIDED, because the fast tail is the object of inference. A lower fence
    would clip precisely the observations the GPD is fitted to. On the 2026 pool
    a two-sided version would put its lower fence at 9.62 s against a 10.44 s
    record -- safe today, but only by luck, and a deeper scrape would start
    deleting record holders. There is no upside to owning that risk: a track
    time cannot be erroneously FAST. Every junk row seen in this data is a units
    error on the slow side ("12:57.00" filed under a 100 m).
    """
    v = np.asarray(seconds, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    if v.size < 4:
        return float("inf")           # too small to fence; keep everything
    q1, q3 = np.percentile(np.log(v), [25, 75])
    return float(np.exp(q3 + k * (q3 - q1)))


# ======================================================================
# LOADING
# ======================================================================

def _read_csv(path: Path) -> pd.DataFrame:
    """Read one scraped CSV as strings. Everything is dtype=str because `grade`
    holds '-' for unknown and `state` is often blank; letting pandas infer types
    per file would make columns change dtype between states."""
    return pd.read_csv(path, dtype=str, encoding=ENCODING).fillna("")


def resolve_source(event: str, state: str, sex: str,
                   root: Path = DATA_ROOT) -> dict | None:
    """
    Pick THE ONE file that represents this event for this state and sex.

    This is not a convenience -- it is a correctness requirement. MA's
    `1600r.csv` holds 30 rows and shares 25 of those 30 names with its
    `1miler.csv`; RI's holds 10 and shares 6 with its `1500r.csv`. Those thin
    files are the same athletes' occasional off-distance races, not a separate
    field. Converting and concatenating every mile file a state owns would
    double-count exactly the athletes sitting at the top of the tail, which is
    the one place a duplicate does real damage.

    So: among the slugs this event accepts, take the single file with the most
    rows and discard the rest. Being row-count driven rather than a hardcoded
    state->distance map means it also resolves states nobody has mapped yet
    (scraping.md open item 2).

    Returns None when the state has no file for this event at all.
    """
    spec = EVENTS[event]
    candidates = []
    for slug, factor in spec.factors(sex).items():
        path = root / state / sex / f"{slug}.csv"
        if path.exists():
            df = _read_csv(path)
            candidates.append({"slug": slug, "factor": factor,
                               "path": path, "frame": df, "n_rows": len(df)})
    if not candidates:
        return None

    winner = max(candidates, key=lambda c: c["n_rows"])
    winner["rejected"] = [(c["slug"], c["n_rows"])
                          for c in candidates if c is not winner]
    return winner


def coverage_check(event: str, sex: str, per_state: dict[str, int],
                   states=NORTHEAST, root: Path = DATA_ROOT) -> list[dict]:
    """
    Flag states that are under-collected for this event, without hardcoding
    what "enough" would be.

    The idea: a state's share of one event's pool should roughly track its share
    of another event's pool. Athletes are not spread evenly across states -- NY
    fields twelve times New Hampshire's -- but the RATIO of that spread between
    two events is stable, because it is the same schools fielding both squads.
    Across the well-scraped states here it sits between 0.75 and 1.85.

    So a state supplying 27% of the sprint pool and 1% of the distance pool does
    not have a thin distance field. It has a truncated file.

    This makes the scraping.md section 3 failure detectable from the data alone.
    A short list looks exactly like a small state, and nothing inside the file
    tells them apart -- but the same state's OTHER event does. It is equally the
    tell for a state contesting a mile distance nobody has scraped. That is what
    it caught first: before 2026-10-07 only `1600m` had been scraped for most
    states, and it flagged VT (601 sprinters, 36 milers) and NY girls (96 rows
    against ~2,800 expected). Both turned out to run the 1500 m, not to be
    truncated -- once `1500r.csv` existed the row-count rule picked it up and
    the warnings cleared.

    Returns one entry per suspect state; an empty list is the all-clear.
    """
    if event == COVERAGE_REF_EVENT:
        return []

    ref = {}
    for state in states:
        src = resolve_source(COVERAGE_REF_EVENT, state, sex, root)
        if src is not None:
            ref[state] = src["n_rows"]

    total_ref, total_ev = sum(ref.values()), sum(per_state.values())
    if not total_ref or not total_ev:
        return []

    warnings = []
    for state, n in per_state.items():
        if not ref.get(state):
            continue
        ratio = (n / total_ev) / (ref[state] / total_ref)
        if ratio < COVERAGE_MIN_RATIO:
            warnings.append({
                "state": state, "n": n, "ratio": ratio, "n_ref": ref[state],
                # What this state would contribute if it tracked its sprint share.
                "expected": int(round(total_ev * ref[state] / total_ref)),
            })
    return sorted(warnings, key=lambda w: w["ratio"])


def load_pool(event: str, sex: str, states=None,
              dedupe: bool = True, fence_k: float = 2.0,
              years=DEFAULT_YEARS,
              region: str = "northeast") -> tuple[pd.DataFrame, dict]:
    """
    Build one pooled distribution for an event x sex, over one or more seasons.

    Returns (frame, meta). The frame carries:
        name, team, grade, state, date   as scraped
        state_dir                        the folder the row came from
        year                             the season it came from
        athlete                          state_dir|name|team: the same person
                                         across seasons (the bootstrap cluster)
        sex, source_slug, factor
        seconds_raw                      as run, in its own distance
        seconds                          converted to this event's distance

    `meta` records every judgement the loader made -- which file each state
    contributed, how many rows fell out at each stage, and where the fence
    landed -- because those are the numbers you need to sanity-check a pooled
    statistic, and they are invisible once the frames are concatenated.
    """
    if event not in EVENTS:
        raise ValueError(f"Unknown event {event!r}. Known: {sorted(EVENTS)}")
    if sex not in SEXES:
        raise ValueError(f"Unknown sex {sex!r}. Known: {SEXES}")

    if region not in REGIONS:
        raise ValueError(f"Unknown region {region!r}. Known: {sorted(REGIONS)}")
    scope = REGIONS[region]
    states = tuple(scope) if states is None else tuple(states)
    unknown = [s for s in states if s not in scope]
    if unknown:
        raise ValueError(
            f"{unknown} is outside the {region} scope {scope}. "
            "The pool scope is fixed on purpose: all five events' pools "
            "must rest on the same states for their return periods to be "
            "comparable."
        )

    years = tuple(sorted(years))
    multi = len(years) > 1
    spec = EVENTS[event]
    frames, resolution, missing = [], {}, []
    n_unparseable = 0
    n_test = 0

    for year, state in ((y, s) for y in years for s in states):
        # Resolution is per season: the label carries the year only when
        # several are stacked, so single-season output reads exactly as before.
        tag = f"{state} {year}" if multi else state
        src = resolve_source(event, state, sex, scrape_year(year))
        if src is None:
            missing.append(tag)
            continue

        df = src["frame"].copy()

        is_test = df["name"].map(lambda s: bool(_TEST_ATHLETE_RE.match(str(s))))
        n_test += int(is_test.sum())
        df = df[~is_test]

        df["seconds_raw"] = df["time"].map(parse_time)

        bad = int(df["seconds_raw"].isna().sum() + (df["seconds_raw"] <= 0).sum())
        n_unparseable += bad
        df = df[df["seconds_raw"].notna() & (df["seconds_raw"] > 0)]

        df["seconds"] = df["seconds_raw"] * src["factor"]
        df["state_dir"] = state
        df["year"] = year
        df["sex"] = sex
        df["source_slug"] = src["slug"]
        df["factor"] = src["factor"]
        frames.append(df)

        resolution[tag] = {"slug": src["slug"], "factor": src["factor"],
                             "n_rows": src["n_rows"], "n_parsed": len(df),
                             "rejected": src["rejected"]}

    if not frames:
        raise ValueError(f"No files found for {event} {sex} in {years}")

    pool = pd.concat(frames, ignore_index=True)
    pool["athlete"] = pool["state_dir"] + "|" + pool["name"] + "|" + pool["team"]
    n_parsed = len(pool)

    # Dedupe before fencing. The GPD derivation assumes independent
    # observations, and these are season-best lists so this is very nearly a
    # no-op within a state -- it is here as a guard, not a correction. Key on
    # the DIRECTORY state, never the `state` column, which is blank on up to
    # 65% of rows in RI/f/1500r.csv. The YEAR is in the key: one row per
    # athlete-SEASON, so stacking seasons keeps both of a repeat athlete's.
    n_dupes = 0
    if dedupe:
        keys = ["year", "state_dir", "name", "team"]
        pool = (pool.sort_values("seconds")
                    .drop_duplicates(subset=keys, keep="first"))
        n_dupes = n_parsed - len(pool)
    n_before_fence = len(pool)

    fence = log_iqr_fence(pool["seconds"].to_numpy(dtype=float), k=fence_k)
    dropped = pool[pool["seconds"] > fence].sort_values("seconds",
                                                        ascending=False)
    pool = pool[pool["seconds"] <= fence]

    pool = pool.sort_values("seconds").reset_index(drop=True)

    seconds = pool["seconds"].to_numpy(dtype=float)
    seasons = pool.groupby("athlete")["year"].nunique()
    meta = {
        "event": event, "label": spec.label_for(sex), "sex": sex,
        "pool": pool_name(event, sex),
        "years": years, "region": region,
        "dataset": dataset_name(years, region),
        "states": sorted(pool["state_dir"].unique(),
                         key=list(states).index),
        "missing_states": missing,
        "resolution": resolution,
        "n_unparseable": n_unparseable,
        "n_test_rows": n_test,
        "n_parsed": n_parsed,
        "n_dupes": n_dupes,
        "n_before_fence": n_before_fence,
        "n": len(pool),
        "fence_k": fence_k,
        "fence": fence,
        "n_fenced": len(dropped),
        "dropped": dropped[["name", "state_dir", "time", "seconds"]].copy(),
        # How much the fence moved the denominator. zeta = N_u/n, so every
        # return period scales by exactly this ratio (_config/evt_theory.md section 3.5).
        "rp_sensitivity": (n_before_fence / len(pool)) if len(pool) else np.nan,
        "fastest": float(seconds.min()) if seconds.size else np.nan,
        "median": float(np.median(seconds)) if seconds.size else np.nan,
        "per_state": pool.groupby("state_dir").size().to_dict(),
        "per_year": pool.groupby("year").size().to_dict(),
        # Distinct people, and how many of them contribute more than one
        # season -- the dependence the cluster bootstrap exists for.
        "n_athletes": int(seasons.size),
        "n_multi_season": int((seasons > 1).sum()),
    }
    # Coverage is a within-season comparison (one season's mile share against
    # the same season's sprint share), so it runs once per season.
    meta["coverage_warnings"] = []
    for year in years:
        per_state = (pool[pool["year"] == year]
                     .groupby("state_dir").size().to_dict())
        for w in coverage_check(event, sex, per_state, states=states,
                                root=scrape_year(year)):
            w["year"] = year
            w["tag"] = f"{w['state']} {year}" if multi else w["state"]
            meta["coverage_warnings"].append(w)
    return pool, meta


# ======================================================================
# REPORTING
# ======================================================================

def describe_pool(meta: dict) -> str:
    """Human-readable account of one pool. Every number here is a judgement the
    loader made on your behalf, so it all gets printed rather than assumed."""
    L = []
    L.append(f"  {meta['label']}  ({meta['sex']})")
    L.append(f"    states                 {len(meta['states'])}: "
             f"{' '.join(meta['states'])}")
    if meta["missing_states"]:
        L.append(f"    NO FILE                {' '.join(meta['missing_states'])}")

    L.append("    source file per state")
    for st, r in meta["resolution"].items():
        note = ""
        if r["factor"] != 1.0:
            note = f"  x{r['factor']:.6f} -> {meta['pool']}"
        if r["rejected"]:
            rej = ", ".join(f"{s} ({n})" for s, n in r["rejected"])
            note += f"   [also present, not used: {rej}]"
        L.append(f"      {st}  {r['slug']:<8} {r['n_rows']:6,d} rows{note}")

    L.append(f"    placeholder rows       {meta['n_test_rows']:,}"
             f"   ('Test Athlete #N')")
    L.append(f"    unparseable dropped    {meta['n_unparseable']:,}")
    L.append(f"    duplicate athletes     {meta['n_dupes']:,}")
    L.append(f"    n before fence         {meta['n_before_fence']:,}")
    L.append(f"    slow-side fence        {fmt_time(meta['fence'])} s "
             f"(log-IQR, k={meta['fence_k']})")
    L.append(f"    fenced out             {meta['n_fenced']:,}")
    if meta["n_fenced"]:
        for _, row in meta["dropped"].head(12).iterrows():
            L.append(f"        {row['name'][:28]:<28} {row['state_dir']}  "
                     f"raw={row['time']:<10} -> {fmt_time(row['seconds'])}")
        if meta["n_fenced"] > 12:
            L.append(f"        ... and {meta['n_fenced'] - 12:,} more")
    L.append(f"    FINAL n                {meta['n']:,}")
    if len(meta["years"]) > 1:
        per_year = ", ".join(f"{y}: {n:,}" for y, n in meta["per_year"].items())
        L.append(f"    athlete-seasons        {per_year}")
        L.append(f"    distinct athletes      {meta['n_athletes']:,}, of whom "
                 f"{meta['n_multi_season']:,} appear in more than one season")
    L.append(f"    return periods scale by x{meta['rp_sensitivity']:.4f} "
             f"vs the unfenced pool")
    L.append(f"    fastest / median       {fmt_time(meta['fastest'])} / "
             f"{fmt_time(meta['median'])}")

    for w in meta["coverage_warnings"]:
        L.append(f"    !! {w['tag']} IS UNDER-COLLECTED: {w['n']:,} rows here "
                 f"against {w['n_ref']:,} in the 100 m.")
        L.append(f"       Share ratio {w['ratio']:.2f} where every healthy state "
                 f"sits near 1; expected roughly")
        L.append(f"       {w['expected']:,} rows. This pool is missing that "
                 f"state's depth AND its tail.")
    return "\n".join(L)


def _self_check() -> None:
    """Assert the two conversion factors against hand-computed marks.

    These are the real fastest marks in MA's mile list and RI's 1500 list, so a
    silent change to either factor breaks here rather than in a fitted tail
    three scripts downstream.
    """
    mile = parse_time("4:07.37")                 # MA boys mile record, 247.37 s
    assert abs(mile - 247.37) < 1e-9, mile
    assert abs(mile * MILE_TO_1600 - 245.933) < 5e-4, mile * MILE_TO_1600

    m1500 = parse_time("3:55.00")                # RI boys 1500 record, 235.00 s
    assert abs(m1500 - 235.0) < 1e-9, m1500
    assert abs(m1500 * M1500_TO_1600 - 251.64) < 5e-3, m1500 * M1500_TO_1600

    # Girls go onto 1500 m. A native 1500 is untouched; a 1600 and a mile are
    # Riegel-shortened. Hand values: 285.88 * (1500/1600)**1.06 = 266.98, and
    # 273.18 * (1500/1609.344)**1.06 = 253.55.
    f = EVENTS["mile"].factors("f")
    assert f["1500r"] == 1.0
    assert abs(parse_time("4:45.88") * f["1600r"] - 266.98) < 5e-3, f["1600r"]
    assert abs(parse_time("4:33.18") * f["1miler"] - 253.55) < 5e-3, f["1miler"]
    assert pool_name("mile", "m") == "1600m" and pool_name("mile", "f") == "1500m"

    # The parser must not "rescue" a comma into a plausible number.
    assert np.isnan(parse_time("2:05,4"))
    assert np.isnan(parse_time("DNF"))
    assert np.isnan(parse_time(""))
    print(f"  conversion self-check passed (boys -> 1600: mile x{MILE_TO_1600},"
          f" 1500 x{M1500_TO_1600:.6f}; girls -> 1500: 1600 x{f['1600r']:.6f},"
          f" mile x{f['1miler']:.6f})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Print every pool's resolution "
                                 "table and cleaning, then self-check.")
    ap.add_argument("--years", default="2026",
                    help="season(s) to pool: 2026, 2025, or 2025,2026")
    ap.add_argument("--region", default="northeast", choices=sorted(REGIONS))
    ap.add_argument("--sex", default="m,f", help="m, f, or m,f")
    args = ap.parse_args()
    years = parse_years(args.years)
    print("=" * 74)
    print(f"  POOLED {dataset_name(years, args.region)} DATA  --  "
          f"{len(REGIONS[args.region])} states ({args.region})")
    print("=" * 74)
    _self_check()
    for event in EVENTS:
        for sex in args.sex.split(","):
            print()
            _, meta = load_pool(event, sex, years=years, region=args.region)
            print(describe_pool(meta))
