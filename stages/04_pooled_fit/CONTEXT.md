# Stage 04 — pooled fit

Pools states into one distribution per event × sex (10 pools: 100–800m + mile → 1600m boys / 1500m girls) for a **dataset**: `2026` (default), `2025`, `2025-2026` (stacked, §10) for the northeast; `us-<years>` with `--region us` (§11). Scopes: `src/regions.py`. Loader: `src/pool_data.py` (moved to `src/` 2026-10-22; shared with stage 02).

## Inputs
| Layer | Path | What to use from it |
|---|---|---|
| 4 (working) | `../01_scrape/output/2026/`, `../01_scrape/output/2025/` | `<ST>/<sex>/100r 200r 400r 800r.csv` plus the mile variants `1600r`, `1miler`, `1500r` for CT MA ME NH NJ NY PA RI VT |
| 3 (reference) | `references/pooled_method.md` | mile rule, cleaning, guards; findings §7 (2026), §10 (seasons), §11 (national), §12 (tail models), §13 (record tests), §14 (national Gompertz) |
| 3 (reference) | `../../src/pool_data.py`, `../../src/plotstyle.py` | the pooled loader; the palette/axis helpers |
| 3 (reference) | `../../src/distances.py` | the mile rule in code: target per sex, conversion factors |
| 3 (reference) | `../../src/regions.py` | `REGIONS` (northeast / us), Census regions and divisions |
| 3 (reference) | `../../_config/evt_theory.md` | the statistics |
| 3 (reference) | `../03_tail_fit/references/threshold_select.md` | the two selectors reused here |
| 4 (working) | `output/_cache/thresholds.json` | GPD threshold-selection cache, keyed on settings *and* a data fingerprint |
| 4 (working) | `output/README.md` | index of every output folder; read it before navigating `output/` |

## Process
1. `src/pool_data.py` loads and cleans each pool (largest mile variant per state, converted; drops `Test Athlete`; fence; athlete-season dedupe; coverage check). `python src/pool_data.py [--years ...]` prints the source table and runs the self-check.
2. `plot_pooled.py` draws the pooled histograms (5 × 2), per-state small
   multiples, and the conversion QC figure (one row per sex).
3. `gpd_pooled.py`: GPD threshold selection (ForwardStop, mixture MLE, shape plateau) + fit; one pool via `--event --sex [--years] [--region us]`.
4. `run_all.py [--years 2025,2026] [--region us --sex m]`: a whole dataset (~40 s warm, ~5–7 min cold; `--refit`, `--quick`). `--quick` overwrites that dataset's summary.
5. Comparisons: `compare_years.py`, `compare_regions.py`, `model_compare.py` (§12),
   `record_check.py` (§13; `--part d` = the division test, §13.1); `weibull_fit.py` adds a Weibull section to `summary.md`.
6. `gompertz_pooled.py` (§14): national Gompertz on 2025+2026 stacked, ForwardStop threshold (de-tied, top-5% fallback), athlete-cluster bootstrap → `output/national/2025-2026/gompertz/`; `gompertz_fit_quality.py`: goodness of fit of those fits (QQ, expected/actual by rank, A², out of sample vs a correct-model yardstick) → same folder, `fit_quality.md`; `gompertz_query.py <event> <sex> <time>...`: return period of any time with 80%/95% bootstrap CIs, the field size, and the equally rare time in the other events of the same sex (`--no-equiv` to skip); slower than u it counts instead (`gompertz_counts.csv`, `--build-counts`), from `gompertz_fit.csv` + `gompertz_boot.csv` (`--check` self-test). (Density plots: `../02_explore/density_plots.py`.)

## Outputs
Full index: `output/README.md`.
- `output/northeast/<years>/` (dataset id `<years>`) and `output/national/<years>/` (id `us-<years>`); `<years>` ∈ `2025`, `2026`, `2025-2026`. GPD folders hold `summary.{md,csv}`, `group_shifts.csv`, `figures/{histograms,gpd}/`; `national/2025-2026/` holds only `gompertz/`.
- `output/comparisons/{northeast_seasons,northeast_vs_national,tail_models,record_tests}/`
- `output/_cache/thresholds.json` (keyed on a data fingerprint; datasets never collide)

## Verify
- `src/pool_data.py` self-check passes. Its source table shows NY girls, RI and VT
  on `1500r`, and MA on `1miler`.
- Each `summary.md` "Cross-event checks" lists no under-collected state.
- `output/northeast/2026/summary.csv` reproduced the pre-2025 run exactly on 2026-10-08;
  a default run must still do so unless the 2026 files change.
- Do not compare `rp_of_fastest` across events. None of the ten is identified
  (each record sits at its fitted wall), so use a slightly slower benchmark.
- The wall CIs on pools with ξ > −0.15 (800m girls, 1500m girls) are bootstrap
  artifacts (`pooled_method.md` §7).
