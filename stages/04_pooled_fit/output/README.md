# Stage 04 output — index

All folders are made by scripts in `stages/04_pooled_fit/`. Paths come from
`src/paths.py` (`pooled_dataset`, `POOLED_*`). Reorganised on 2026-10-22.

## Fits: `<region>/<seasons>/`

| folder | states | seasons | model | made by | open first |
|---|---|---|---|---|---|
| `northeast/2026/` | 9 northeast | 2026 | GPD | `run_all.py` | `summary.md` |
| `northeast/2025/` | 9 northeast | 2025 | GPD | `run_all.py --years 2025` | `summary.md` |
| `northeast/2025-2026/` | 9 northeast | 2025 + 2026 stacked | GPD | `run_all.py --years 2025,2026` | `summary.md` |
| `national/2026/` | all 51 | 2026 | GPD + Weibull section | `run_all.py --region us`, `weibull_fit.py --region us` | `summary.md` |
| `national/2025-2026/` | all 51 | 2025 + 2026 stacked | **Gompertz only** | `gompertz_pooled.py`; `gompertz_fit_quality.py`; queried by `gompertz_query.py` | `gompertz/gompertz.md`, then `gompertz/fit_quality.md` |

**`northeast/2025-2026` versus `national/2025-2026`:**
- Both stack the two seasons: each row is one athlete-season, and the bootstrap resamples
  whole athletes.
- They differ in two ways:
  - **States:** the northeast folder has 9 states (CT MA ME NH NJ NY PA RI VT); the
    national folder has all 50 + DC.
  - **Model:** the northeast folder has the GPD pipeline (`summary.md`, `figures/gpd/`);
    the national folder has only the Gompertz model (`gompertz/`).

**Dataset IDs.** Code, summaries and figure names use an ID, not the folder name:
- northeast: `2026`, `2025`, `2025-2026`;
- national: the same with a `us-` prefix (`us-2026`, `us-2025-2026`). `--region us`
  selects it.
- So `xi_overlay_us-2026.png` belongs to `national/2026/`.

**What each fit folder holds:**
- GPD folders: `summary.md`, `summary.csv`, `group_shifts.csv`, `figures/histograms/`,
  `figures/gpd/`.
- `national/2025-2026/gompertz/`: `gompertz_fit.csv`, `gompertz_queries.csv`, `gompertz_boot.csv`
  (every bootstrap draw's u, ζ, c, b; read by `gompertz_query.py`), `gompertz_counts.csv` (time × season
  counts, written by `gompertz_query.py --build-counts`), `gompertz_forwardstop.csv`,
  `fit_quality.*`.
- `national/2026/`: also `weibull_fit.csv`, `weibull_queries.csv`, `weibull_section.md`,
  `figures/weibull_vs_gpd_{m,f}.png`.

**Not made yet:**
- `national/2025/`: `run_all.py --region us --years 2025` has not been run.
- A GPD summary for `national/2025-2026/`.

## Comparisons: `comparisons/`

| folder | what | made by | open first |
|---|---|---|---|
| `northeast_seasons/` | northeast 2025 vs 2026 vs stacked: does the tail shape replicate | `compare_years.py` | `year_comparison.md` |
| `northeast_vs_national/` | northeast 2026 vs national 2026 | `compare_regions.py` | `region_comparison.md` |
| `tail_models/` | GPD vs exponential vs Weibull vs Gompertz: AIC, threshold stability, out-of-sample, ξ overlays, predicted vs actual | `model_compare.py` | `model_comparison.md` |
| `record_tests/` | accuracy at the record: Exp(1) yardstick, thresholds, grades, division test, ForwardStop cache | `record_check.py` | `record_test_report_2026-10-22.md`, then `record_calibration.md` |

`tail_models/.Rhistory` is not made by a script. It moved here with the old
`model_comparison/` folder.

## Caches: `_cache/`
- `_cache/thresholds.json`: the GPD threshold-selection cache for `gpd_pooled.py`. It is keyed on
  the settings and a data fingerprint, so datasets cannot collide. `run_all.py --refit`
  ignores it.
- Other caches stay next to their results:
  - `comparisons/record_tests/forwardstop_gompertz.csv`;
  - `national/2025-2026/gompertz/gompertz_forwardstop.csv`.

## Elsewhere
- Density plots (2025 vs 2026, national): `stages/02_explore/output/density/`.
- National 2025 + 2026 histograms: `stages/02_explore/output/2025-2026/`: `pooled/`,
  `by_state/`, `by_region/` (4 Census regions), `by_division/` (9 Census divisions).
- The method and the findings: `stages/04_pooled_fit/references/pooled_method.md`.
