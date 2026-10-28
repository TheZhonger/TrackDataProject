# Stage 03 — single-event tail fit

Fit a Generalized Pareto Distribution to the fast tail of **one** event's CSV,
choose the threshold `u` defensibly, and turn query times into return periods
("one athlete-season in N"). This stage holds the project's core EVT code, and
stage 04 imports it.

## Inputs
| Layer | Path | What to use from it |
|---|---|---|
| 3 (reference) | `../../_config/evt_theory.md` | PBdH, ξ regimes, **sign convention (§3.4)**, ζ = N_u/n |
| 3 (reference) | `../../_config/lessons.md` | ξ < −0.5 boundary, false corroboration |
| 3 (reference) | `references/gpd_tail.md` | CONFIG knobs, non-negotiable design choices, the 4 diagnostic panels |
| 3 (reference) | `references/threshold_select.md` | ForwardStop + mixture MLE, edge detection, the two guards |
| 4 (working) | `../01_scrape/output/legacy/NY/m/100r.csv` | default `EVENT_FILE`; any leaderboard CSV can be passed instead |
| 4 (working) | `../01_scrape/output/2026/<ST>/<sex>/` | `run_states.py`: 100r 200r 400r 800r and the state's main mile file |
| 3 (reference) | `../../src/distances.py` | the mile rule: most-rows variant, onto 1600 m boys / 1500 m girls |
| 3 (reference) | `references/findings_2026.md` | what the 2026 fits show, and how far to trust it |

## Process
1. Edit the CONFIG block in `gpd_tail.py` (file, threshold mode/value, query times).
2. `.venv/bin/python stages/03_tail_fit/threshold_select.py [csv]` picks `u` two
   independent ways and compares them. Read *why* they agree before trusting it.
3. `.venv/bin/python stages/03_tail_fit/gpd_tail.py [csv]` fits, bootstraps CIs,
   prints the report, and draws the diagnostics.
4. Internally `x = -seconds`. Everything printed or plotted is back in seconds.
5. Per-state sweep: `.venv/bin/python stages/03_tail_fit/run_states.py`. It runs
   90 fits (9 northeast states × 2 sexes × 5 events) in about 25 minutes.
   - It reuses the functions above unchanged. `threshold_select` itself now has
     the "nothing rejected" guard and a scale-relative agreement tolerance.
6. `tail_models.py` is a library, not a script: GPD, exponential, Weibull-type and
   Gompertz tails behind one interface (fit, survival, local and implied-GPD ξ).
   Stage 04's `model_compare.py` drives it. `gpd_tail.endpoint_interval` is the
   wall CI (resamples with no finite wall count as unbounded).
   - Narrow a run with `--states NY --sex f --events mile`.

## Outputs
- `output/gpd_diagnostics<EVENT_LABEL>.png`: mean residual life, ξ stability, QQ, log-tail fit.
- A printed report (threshold, N_u, ξ, σ, implied wall, query return periods).
- `output/2026/state_fits.{md,csv}`: one row per state × sex × event. It records
  the selector used, u, N_u, ξ with bootstrap CI, the wall and its CI, the
  fastest mark, the ξ drift and the rise fraction.
- `output/2026/<ST>_<sex>_<pool>.png`: the 4-panel diagnostics for each of the
  90 fits.

## Verify
- ξ stability panel: a **plateau** across thresholds, not a slide.
- Implied wall is not a hair faster than the fastest observed mark. If it is,
  the threshold is too aggressive.
- No ξ < −0.5 warning. If one appears, lower the threshold.
- Regression check: default 100 m run gives `threshold_select` ForwardStop u = 11.480 s, N_u = 580.
  `run_states.py` gives the same for NY boys 2026 100m (same list, 7,972 rows),
  checked 2026-10-08.

## Current state
Read `references/findings_2026.md` for the full findings. In short:
- The NY boys 100m baseline is unchanged (u = 11.48 s, N_u = 580, ξ = −0.270).
- Fields under 1,000 runners can't carry a tail on their own.
- Per state, the data are consistent with the pooled ξ slide but can't confirm it.
