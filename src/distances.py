"""
distances.py
============
The metric-mile rule, in one place, for every stage that needs it.

THE PROBLEM
-----------
There is no single "mile" event across states (see _config/data_conventions.md).
Each state x sex contests one of three distances, and athletic.net files each
as its own list:

    1600r.csv   1600 m          most of the northeast
    1miler.csv  1 mile          MA (both sexes)
    1500r.csv   1500 m          RI and VT (both sexes), NY girls

A state also keeps small lists for the distances it does NOT contest -- the
same athletes' occasional off-distance races. So the rule is two steps:

  1. per (state, sex), take the variant with the MOST performances; that is the
     event the state actually runs, and the others are discarded rather than
     added (adding them double-counts the athletes at the top of the tail);
  2. convert it to the TARGET distance for that sex:
        boys  -> 1600 m      (what most northeast boys run)
        girls -> 1500 m      (NY, the largest girls' field, runs the 1500)

THE CONVERSION
--------------
Riegel's endurance model:  t2 = t1 * (d2 / d1) ** 1.06.  The exponent > 1 says
pace slows as distance grows, so a longer race costs more than its distance
ratio alone.

One exception, for continuity: mile <-> 1600 m uses the plain distance ratio
1600/1609.344 = 0.99419. The two races differ by 9 m, and Riegel would give
0.99384 -- 0.014 s apart at 4:00, below timing resolution -- and every pooled
boys result before 2026-10-08 used the plain ratio. Over the 100+ m gaps that
involve the 1500 the two methods disagree by about a second at 4:40, so Riegel
is used there:

    1500 -> 1600   x 1.070806          1600 -> 1500   x 0.933877
    mile -> 1500   x 0.928130          mile -> 1600   x 0.99419   (ratio)

The factors are physical, not tuned to this data. Tuning them would absorb the
effort confound described in stages/04_pooled_fit/references/pooled_method.md §3.
"""

from pathlib import Path

RIEGEL_EXPONENT = 1.06

# Filename stem (as scraped) -> distance actually run, in metres.
SLUG_METRES = {"1600r": 1600.0, "1miler": 1609.344, "1500r": 1500.0}
MILE_SLUGS = tuple(SLUG_METRES)

# What each sex's pooled / per-state distance event is expressed in.
TARGET_METRES = {"m": 1600.0, "f": 1500.0}


def factor(src_m: float, dst_m: float) -> float:
    """Multiplier taking a time at src_m metres to its equivalent at dst_m."""
    if src_m == dst_m:
        return 1.0
    if {src_m, dst_m} == {1600.0, 1609.344}:
        # Plain distance ratio, see the module docstring. Kept to the same 5
        # decimals as the historical constant so boys' numbers do not move.
        return 0.99419 if dst_m == 1600.0 else 1 / 0.99419
    return (dst_m / src_m) ** RIEGEL_EXPONENT


def factors_for(sex: str) -> dict[str, float]:
    """slug -> multiplier onto this sex's target distance."""
    target = TARGET_METRES[sex]
    return {slug: factor(m, target) for slug, m in SLUG_METRES.items()}


def target_name(sex: str) -> str:
    """'1600m' for boys, '1500m' for girls -- used in filenames and tables."""
    return f"{int(TARGET_METRES[sex])}m"


def event_stems(sex_dir: Path, suffix: str = "r") -> list[str]:
    """The five events' filename stems for one <ST>/<sex>/ folder.

    Sprints and the 800 are fixed; the mile slot is whichever variant that
    state actually runs (main_mile_slug), unconverted. Used by the stage 02
    plots, which show each event as run.
    """
    sprint = [f"{d}{suffix}" for d in (100, 200, 400, 800)]
    return sprint + [main_mile_slug(sex_dir) or f"1600{suffix}"]


def stem_label(stem: str) -> str:
    """Filename stem -> display name: '100r' -> '100m', '1miler' -> '1 mile'.

    Already-display names ('100m', '1600m eq.' from src/northeast) pass through,
    so callers can key panels by either.
    """
    if stem.endswith(("m", "eq.")):
        return stem
    base = stem[:-1] if stem.endswith("r") else stem
    return "1 mile" if base == "1mile" else f"{base}m"


def _count_rows(path: Path) -> int:
    with open(path, encoding="utf-8") as fh:
        return max(sum(1 for _ in fh) - 1, 0)        # minus the header


def main_mile_slug(sex_dir: Path) -> str | None:
    """The mile variant with the most rows in one <ST>/<sex>/ folder, or None.

    Same rule as src/pool_data.resolve_source, for callers
    that only need the file, not the frame.
    """
    counts = {slug: _count_rows(sex_dir / f"{slug}.csv")
              for slug in MILE_SLUGS if (sex_dir / f"{slug}.csv").exists()}
    return max(counts, key=counts.get) if counts else None
