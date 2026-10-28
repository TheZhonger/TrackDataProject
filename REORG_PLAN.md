# Reorganisation record — 2026-10-07

**Shape: Mixed ICM.** The work is a pipeline (scrape → explore → fit → pool),
but stages share code. So each script lives in the stage that runs it, and
helpers used by more than one stage live in `src/`.

## Moves (47; machine-readable in `.icm/moves.json`, reversible with `bash .icm/undo_moves.sh`)

| From | To | Why |
|---|---|---|
| `scrapeAll.py`, `individualScrape.py` | `stages/01_scrape/` | scraping stage |
| `SCRAPING.md` | `stages/01_scrape/references/scraping.md` | stage-01 reference |
| `State ID List - Sheet1.csv` | `stages/01_scrape/references/` | stable scraper input |
| `data/2025`, `data/2026`, `data/individual`, `data/html`, `data/_progress` | `stages/01_scrape/output/…` | the scrape's product |
| `data/CA`, `data/NY`, `data/TX` | `stages/01_scrape/output/legacy/` | older layout, kept apart from the current one |
| `plot_events.py`, `plotByDate.py`, `plotRandom.py`, `dateRegression.py`, `plotIndividual.py` | `stages/02_explore/` | descriptive, no inference |
| `graphs/individual`, `random graphs/{event_histograms*, individual_progression*}` | `stages/02_explore/output/` | those scripts' figures |
| `gpd testing/{gpd_tail,threshold_select}.py` | `stages/03_tail_fit/` | single-event EVT |
| `gpd testing/gpd_diagnostics.png`, `random graphs/gpd_diagnostics{100m,1600m}.png` | `stages/03_tail_fit/output/` | gpd_tail's figures |
| `pooled2026/*.py` | `stages/04_pooled_fit/` | pooled pipeline |
| `pooled2026/README.md` | `stages/04_pooled_fit/references/pooled_method.md` | stage-04 reference |
| `pooled2026/out/*`, `graphs/pooled2026/{histograms,gpd}` | `stages/04_pooled_fit/output/{…,figures/}` | its outputs |
| `util.py` | `src/util.py` | shared by stages 01 and 02 |
| `scrape.py`, `data.json`, `trash/`, `random graphs/{Figure_1, figure boys, gpd_diagnostics}.png`, `report.md`, `summary.json` | `_archive/` | superseded, unknown provenance, or a stale snapshot |

## Also changed

- **Windows venv removed from the root.** `Lib/ Scripts/ Include/ share/
  pyvenv.cfg` were moved to `~/.Trash/track-windows-venv-2026-10-07/`, which
  is recoverable until the Trash is emptied. It was replaced by `.venv/`
  (macOS, Python 3.15) and `requirements.txt`.
- **CLAUDE.md split by layer.** Theory went to `_config/evt_theory.md`, data
  rules to `_config/data_conventions.md`, and lessons to `_config/lessons.md`.
  The tool docs went to `stages/03_tail_fit/references/`, and the state and open
  questions to the stage and root `CONTEXT.md` files. The original is archived
  at `_archive/2026-10-06_report/CLAUDE.pre-reorg.md`.
- **New `src/paths.py`.** Every location is anchored on the repo, so scripts run
  from any directory.
- **`parse_time` and `seconds_formatter` moved** from `plotByDate.py` into
  `src/util.py`, so the scraper no longer imports a plotting script.
- **Fixed broken scripts.** `plot_events.py` and `plotRandom.py` pointed at
  `output*.csv` files that no longer existed.
- **scraping.md corrected.** §0 (wrong-event files) is marked resolved, and §7
  data state is refreshed. Both were verified against the files.

## Risks handled

- The scraper ledger stores old `data\…` paths in each job's `out` field. That
  field is metadata only, and paths are recomputed from `--out-root`, so resume
  still works (`--dry-run` shows all jobs `done`).
- `gpd_pooled.py` imports stage 03's code through a `sys.path` insert. This is
  the one deliberate cross-stage import, now pointed at `src/paths.TAILFIT_DIR`.
