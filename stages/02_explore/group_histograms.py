"""
group_histograms.py
===================
The national pools, drawn whole and then split by geography. For each event x
sex:

  pooled/histogram.png              the ten national pools (5 events x 2 sexes),
                                    with mean, median, n, sd and fastest mark
  by_state/<event>/                 each of the 51 states against the pool
  by_region/<event>/                each of the 4 Census regions against the pool
  by_division/<event>/              each of the 9 Census divisions against the pool

Every by_* folder holds histogram_<sex>.png and shifts_<sex>.csv (the numbers
behind the figure). Event folders are 100m 200m 400m 800m mile; "mile" holds
1600 m boys and 1500 m girls, as converted by the pooled loader.

WHAT THE SHIFTS MEAN (and do not)
---------------------------------
"median -0.30 s" is this group's median minus the national median: negative is
faster. Three cautions decide how to read it:
  * The mean is pulled by the slow tail, so (mean shift - median shift) is a
    skew signal, not a second estimate of speed.
  * These are LISTS, not populations. A state whose athletic.net list stops
    short of its real field looks faster at the median than it is. Ohio's 2025
    lists, for example, are about half the size of its 2026 lists
    (stages/01_scrape/references/scraping.md section 7).
  * A region is a mixture of its states, weighted by list size. A big, deep
    state (California in the West, Texas in the South) can set its region's
    shift almost alone -- check by_state before reading a region as a whole.

With 2025 and 2026 stacked, each row is one athlete-season, so an athlete who
ran both seasons counts twice -- the same unit the stage 04 fits use.

Data: src/pool_data.load_pool(region="us") -- the same cleaned pools as stage
04 (fence, athlete dedupe, mile conversion). The figures are
src/plot_groups.figure_pooled / figure_by_group, the code behind stage 04's
hist_pooled and hist_by_{state,region,division}_* figures, so the two stages
draw identical panels. Groups are src/regions.CENSUS_REGIONS / CENSUS_DIVISIONS.

    python stages/02_explore/group_histograms.py [--years 2025,2026] [--sex m,f]
                                                 [--levels state,region,division]

Writes stages/02_explore/output/<years>/ (paths.explore_groups).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import explore_groups  # noqa: E402
from plot_groups import figure_by_group, figure_pooled  # noqa: E402
from pool_data import EVENTS, load_pool, parse_years  # noqa: E402
from regions import CENSUS_DIVISIONS, CENSUS_REGIONS  # noqa: E402

# level -> state-to-group map; None means every state is its own group.
LEVELS = {"state": None, "region": CENSUS_REGIONS, "division": CENSUS_DIVISIONS}


def main() -> None:
    ap = argparse.ArgumentParser(description="National pooled and by-group histograms.")
    ap.add_argument("--years", default="2025,2026")
    ap.add_argument("--sex", default="m,f")
    ap.add_argument("--levels", default="state,region,division")
    ap.add_argument("--dpi", type=int, default=140)
    args = ap.parse_args()
    years = parse_years(args.years)
    levels = args.levels.split(",")
    root = explore_groups(years)
    (root / "pooled").mkdir(parents=True, exist_ok=True)

    pools = {}
    for sex in args.sex.split(","):
        for ev in EVENTS:
            df, meta = load_pool(ev, sex, years=years, region="us")
            pools[(ev, sex)] = (df, meta)
            for level in levels:
                out = root / f"by_{level}" / ev    # "mile": 1600 m boys / 1500 m girls
                out.mkdir(parents=True, exist_ok=True)
                groups = LEVELS[level] or {st: st for st in meta["per_state"]}
                tab = figure_by_group(df, meta, groups, level,
                                      out / f"histogram_{sex}.png", args.dpi)
                tab.round(3).to_csv(out / f"shifts_{sex}.csv", index=False)
                # A state missing from the group map would silently drop its
                # marks from every panel; refuse rather than draw a short pool.
                if int(tab["n"].sum()) != len(df):
                    raise SystemExit(f"{ev} {sex} {level}: panels hold "
                                     f"{tab['n'].sum()} marks, pool has {len(df)}")
    # Both sexes on one figure (rows events, columns sexes), as in stage 04's
    # hist_pooled.png; one sex alone makes a single tall, narrow column.
    figure_pooled(pools, root / "pooled" / "histogram.png", args.dpi, meta["dataset"])


if __name__ == "__main__":
    main()
