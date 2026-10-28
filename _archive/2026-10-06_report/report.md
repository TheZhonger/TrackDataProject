# Project report — Track Times Research

Generated 2026-10-06 from a scan of the working tree. Paths are relative to the
project root. Virtualenv contents (`Lib/`, `Scripts/`, `Include/`, `share/`),
`__pycache__/`, `.DS_Store` and lock files are excluded from every count below.

## 1. What the project is

A research codebase that scores high school track performances (100 m – 1600 m)
on one cross-event scale of "how rare is this?" It fits a **Generalized Pareto
Distribution** to the fast tail of each event (extreme value theory) and turns
a query time into a return period: "one athlete-season in N". The data is
scraped from athletic.net.

Most of the documentation is in three Markdown files. They are thorough and
should be read before the code:

| Doc | Covers |
|---|---|
| `CLAUDE.md` | The statistics: PBdH theorem, ξ regimes, sign convention, threshold selection, lessons learned |
| `SCRAPING.md` | athletic.net quirks, the scrapers, the event-slug pitfall |
| `pooled2026/README.md` | The pooled northeast pipeline and what the 2026 fits actually say |

`README.md` holds two lines of scratch notes and no project description.

## 2. Directory structure

```
.
├── CLAUDE.md, SCRAPING.md, README.md      docs
├── scrapeAll.py                           current scraper (resumable, many states/years)
├── individualScrape.py                    per-athlete career histories
├── scrape.py                              legacy scraper — never import it
├── util.py                                parseDate helper
├── dateRegression.py, plotByDate.py,      exploratory analysis / plotting
│   plotIndividual.py, plotRandom.py,
│   plot_events.py
├── gpd testing/                           single-event EVT inference
│   ├── gpd_tail.py                        GPD fit + scoring + 4-panel diagnostics
│   ├── threshold_select.py                ForwardStop + mixture-MLE threshold choice
│   └── gpd_diagnostics.png
├── pooled2026/                            pooled 9-state pipeline (newest work)
│   ├── pool_data.py, plot_pooled.py,
│   │   gpd_pooled.py, run_all.py
│   └── out/  summary.md, summary.csv, thresholds.json
├── data/
│   ├── 2025/<ST>/<sex>/*.csv              36 files, northeast nine
│   ├── 2026/<ST>/<sex>/*.csv              41 files, northeast nine + WY, DC test runs
│   ├── NY/m, CA/m, TX/m                   older state/sex layout
│   ├── individual/                        3 career-history CSVs
│   ├── html/                              503 cached athlete pages + rosters
│   └── _progress/progress.json            scraper job ledger
├── graphs/                                pooled2026 + individual figures (16 PNG)
├── random graphs/                         earlier figures (10 PNG, 1 PDF)
├── trash/                                 6 abandoned scripts
├── State ID List - Sheet1.csv             athletic.net state → list-ID map
└── data.json                              early scrape output (names list)
```

**File counts (656 project files):** 500 HTML (all in `data/html`), 97 CSV,
26 PNG, 21 Python (6 of them in `trash/`), 5 Markdown, 4 JSON, 1 PDF, 2 config.

## 3. Key files

| File | Lines | Role |
|---|---|---|
| `scrapeAll.py` | 879 | SeleniumBase UC-mode scraper. Writes one row per athlete. Resumable through the progress ledger |
| `individualScrape.py` | 513 | Full performance history for the top N on a list. Also exports `EMAIL`, `PASSWORD`, `page_url`, `parse_roster` to `scrapeAll.py` |
| `gpd testing/gpd_tail.py` | 505 | Core inference. Negates times so the fast tail becomes an upper tail, fits the GPD with `floc=0`, bootstraps CIs |
| `gpd testing/threshold_select.py` | 328 | Two threshold selectors (ForwardStop, mixture profile MLE) |
| `pooled2026/gpd_pooled.py` | 812 | Reuses both modules through a `sys.path` insert. Adds a third selector (shape plateau) and the guards for saturation and grid edges |
| `pooled2026/pool_data.py` | 529 | Loads files, converts mile and 1500 m times to 1600 m, applies a one-sided log-IQR fence, dedupes |
| `pooled2026/out/summary.md` | — | Latest results: 4 pools (100 m / 1600 m × m / f) |

### Current scientific state (from `pooled2026/out/summary.md`)

- Only the **100 m boys** pool has a stable GPD regime (ξ ≈ −0.33 plateau,
  n = 28,686).
- 100 m girls and both 1600 m pools show ξ **sliding monotonically** across the
  whole grid, so there is no valid threshold. The README argues the 1600 m
  needs a different model, not a wider grid.
- The return periods of the fastest marks are **not identified** in any of the
  four pools, because each record sits at the fitted wall.
- NY girls' 1600 m (96 rows) and VT's mile were under-collected.

## 4. Findings and improvement suggestions

Ordered by how much each one matters.

### Correctness and data integrity

1. **A plaintext password in source.** `individualScrape.py:46-47` uses
   `os.environ.get(...)` but falls back to a hardcoded email and password.
   Remove the fallback defaults so the scraper fails loudly when the
   environment variables are missing, and change that athletic.net password,
   since it has existed in plaintext on disk.
2. **SCRAPING.md §0 looks out of date.** It warns that the 18 `data/2026/*/1600r.csv`
   files hold 100 m data. In the current tree every one of them starts with a
   mile-range time (for example NY boys 4:08.19, 4,430 rows), and the ledger
   records a run on 2026-09-13, after that warning was written. Re-verify the
   files, then mark the warning resolved so readers don't avoid good data.
3. **CLAUDE.md points to the wrong locations.** It places `gpd_tail.py` and
   `threshold_select.py` at the repo root, but they live in `gpd testing/`.
   It also doesn't mention `pooled2026/`, where the newest results are.
   §8 ("state as of last session") predates the pooled findings.
4. **`threshold_select.py` is missing two guards that CLAUDE.md §5 calls done**,
   according to `pooled2026/README.md` §6. These are the scale-relative agreement
   criterion (it is still a hardcoded `0.15` s) and detection of the
   "nothing rejected" fallback. `pooled2026` works around this, but anyone who
   runs the single-event script still gets the old behaviour. Port the guards
   back.
5. **Broken plotting scripts.** `plot_events.py`, `plotByDate.py` and
   `plotRandom.py` expect `output100.csv … output1600.csv`, which no longer
   exist. `plotRandom.py` hardcodes `data/NY/m/output1600.csv`. Point them at
   the `data/<year>/<ST>/<sex>/` layout, or move them to `trash/`.

### Organization

6. **The virtualenv shares the project root.** `Lib/`, `Scripts/`, `Include/`,
   `share/` and `pyvenv.cfg` account for about 2,500 of the 3,155 files in the
   folder. It is also a Windows venv (`home = C:\Users\...`), so it won't run
   on this Mac. Move it to `.venv/` or outside the project, and add a
   `requirements.txt`. None exists today, and the dependencies (numpy, pandas,
   scipy, matplotlib, seaborn, seleniumbase, bs4) are recorded only in import
   lines.
7. **The project isn't under version control, and `.gitignore` contains `*`.**
   Given how often CLAUDE.md cites past bugs as precedent, git history would
   pay for itself. Run `git init` and replace the ignore-everything rule with
   real exclusions: the venv, `__pycache__/`, `data/html/`, `downloaded_files/`,
   `.DS_Store`.
8. **Three data layouts coexist** (`data/NY/m`, `data/CA/m`, `data/TX/m` vs
   `data/<year>/…`). Move the older ones under `data/legacy/` so the current
   layout is unambiguous. Also move the WY and DC/VT `3200r` test artifacts out
   of `data/2026/`, since `pool_data.py` already excludes them by hand.
9. **Rename the directories with spaces** (`gpd testing/`, `random graphs/`,
   `State ID List - Sheet1.csv`). They force quoting everywhere and complicate
   the `sys.path` insert. Something like `gpd/`, `figures/archive/`,
   `state_ids.csv` would avoid that.
10. **Root-level odds and ends:** `data.json` (an early scrape),
    `trash/`, and `random graphs/` could go into one `archive/` folder.
    `trash/performancezscores` has no `.py` extension even though it is
    Python, and its rank/z-score approach is the one CLAUDE.md marks as closed.
11. **`README.md` is a scratchpad.** Replace it with a one-paragraph project
    description that links to the three real docs.

### Missing infrastructure

12. **No tests and no CI.** The best first tests are the ones that would have
    caught past bugs:
    - each `parse_time()` against the dirty inputs (`4:31.02h`, `10.31a`,
      `DNF`, `2:05,4` → NaN)
    - the GPD sign convention, by round-tripping a known tail
    - a data-sanity check that fails when an event file's median time is wrong
      for the event, which would have caught the §0 slug bug automatically
13. **Several copies of `parse_time()`.** CLAUDE.md says every script has its
    own. A single shared version in `util.py` would keep the comma-handling
    rule in one place.
