"""
paths.py
========
Every canonical location in the workspace, in one place.

The project is laid out as numbered stages (see CLAUDE.md): each stage's
scripts live in stages/NN_name/ and write only into that stage's output/.
Scripts used to build paths relative to the current directory ("data/NY/m/"),
which meant they only worked when launched from the repo root and broke
silently whenever a folder moved. Everything here is anchored on this file's
own location instead, so a script finds its data no matter where it is run
from, and a future reorganisation is an edit to this file rather than a hunt
through a dozen scripts.

Scripts reach this module with one line at the top:

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

(parents[2] of stages/NN_name/script.py is the repo root.)
"""

from pathlib import Path

ROOT   = Path(__file__).resolve().parent.parent
STAGES = ROOT / "stages"

# ----------------------------------------------------------------------
# 01_scrape -- athletic.net leaderboards. Its output/ is the project's data.
# ----------------------------------------------------------------------
SCRAPE_DIR = STAGES / "01_scrape"
SCRAPE_REF = SCRAPE_DIR / "references"
SCRAPE_OUT = SCRAPE_DIR / "output"

STATE_ID_CSV = SCRAPE_REF / "State ID List - Sheet1.csv"   # state -> list id per year

DATA_2025  = SCRAPE_OUT / "2025"          # <ST>/<sex>/<event>.csv, current layout
DATA_2026  = SCRAPE_OUT / "2026"
LEGACY     = SCRAPE_OUT / "legacy"        # <ST>/<sex>/<event>.csv from scrape.py (Aug 2026)
INDIVIDUAL = SCRAPE_OUT / "individual"    # individualScrape.py career histories
HTML_CACHE = SCRAPE_OUT / "html"          # cached athlete bios + rosters
PROGRESS   = SCRAPE_OUT / "_progress"     # scrapeAll.py resume ledger + partials

# ----------------------------------------------------------------------
# 02_explore -- descriptive plots, no inference
# ----------------------------------------------------------------------
EXPLORE_DIR = STAGES / "02_explore"
EXPLORE_OUT = EXPLORE_DIR / "output"
EXPLORE_DENSITY = EXPLORE_OUT / "density"   # national KDEs, 2025 vs 2026 (density_plots.py)

# ----------------------------------------------------------------------
# 03_tail_fit -- single-event GPD fit and threshold selection. Its code is
# also imported by 04 (the one deliberate cross-stage import).
# ----------------------------------------------------------------------
TAILFIT_DIR = STAGES / "03_tail_fit"
TAILFIT_OUT = TAILFIT_DIR / "output"

# ----------------------------------------------------------------------
# 04_pooled_fit -- pooled fits. Datasets are grouped by REGION, then seasons:
#   output/northeast/<years>/   the nine northeast states  (dataset id "<years>")
#   output/national/<years>/    all 50 states + DC         (dataset id "us-<years>")
# with <years> = "2025", "2026" or "2025-2026" (stacked). The dataset ids are
# unchanged from before 2026-10-22 (they appear in summaries, figure names and
# cache keys); only the folder they map to changed. Cross-dataset comparisons
# live under output/comparisons/, caches under output/_cache/.
# output/README.md indexes all of it.
# ----------------------------------------------------------------------
POOLED_DIR     = STAGES / "04_pooled_fit"
POOLED_OUT     = POOLED_DIR / "output"
POOLED_CACHE   = POOLED_OUT / "_cache" / "thresholds.json"   # GPD threshold cache
POOLED_COMPARE = POOLED_OUT / "comparisons"
POOLED_SEASONS = POOLED_COMPARE / "northeast_seasons"       # compare_years.py
POOLED_REGIONS = POOLED_COMPARE / "northeast_vs_national"   # compare_regions.py
POOLED_MODELS  = POOLED_COMPARE / "tail_models"             # model_compare.py
POOLED_RECORDS = POOLED_COMPARE / "record_tests"            # record_check.py


def explore_groups(years) -> Path:
    """Stage 02's national histograms for a set of seasons: output/<years>/
    (e.g. output/2025-2026/). group_histograms.py writes pooled/ and
    by_state/, by_region/, by_division/ under it, one folder per event with
    histogram_<sex>.png and shifts_<sex>.csv."""
    return EXPLORE_OUT / "-".join(str(y) for y in sorted(years))


def scrape_year(year) -> Path:
    """Stage 01's folder for one season: output/<year>/<ST>/<sex>/<event>.csv."""
    return SCRAPE_OUT / str(year)


def pooled_dataset(name: str) -> Path:
    """
    Stage 04's output folder for one dataset id:
        "2026", "2025", "2025-2026"        -> output/northeast/<id>/
        "us-2026", "us-2025-2026", ...     -> output/national/<years>/
    """
    if name.startswith("us-"):
        return POOLED_OUT / "national" / name.removeprefix("us-")
    return POOLED_OUT / "northeast" / name


# The national stacked Gompertz fits (gompertz_pooled.py), their fit-quality
# report (gompertz_fit_quality.py) and the query tool (gompertz_query.py).
POOLED_GOMPERTZ = pooled_dataset("us-2025-2026") / "gompertz"
