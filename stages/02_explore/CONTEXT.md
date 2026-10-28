# Stage 02 — explore

Descriptive plots and simple regressions, with **no tail inference**. This stage
is for looking at the data before trusting a model on it: the shapes of the
distributions, when in the season marks are set, and how individual athletes
progress. Nothing downstream depends on its outputs.

## Inputs
| Layer | Path | What to use from it |
|---|---|---|
| 4 (working) | `../01_scrape/output/2026/` | `<ST>/<sex>/100r 200r 400r 800r.csv` plus the state's main mile file, for the 2026 northeast runs |
| 4 (working) | `../01_scrape/output/legacy/NY/m/` | `100.csv 100r.csv 200.csv 400.csv 800.csv 1600.csv` (NY boys, Aug 2026). This is the scripts' default when no flags are given |
| 4 (working) | `../01_scrape/output/legacy/CA/m/1600r.csv` | CA vs NY comparison (`plotRandom.py`) |
| 4 (working) | `../01_scrape/output/individual/168546-m-1600m.csv` | career histories (`plotIndividual.py`) |
| 3 (reference) | `../../_config/data_conventions.md` | schema, the dirty `time` column, which mile each state runs |
| 3 (reference) | `references/scripts.md` | the 2026 and `--pool` flags, examples, and what `plot_events.py` draws |
| 3 (reference) | `../../src/northeast.py` | the pooled loader: nine states, mile rule, slow-side fence |
| 3 (reference) | `../../src/pool_data.py`, `../../src/plotstyle.py`, `../../src/plot_groups.py`, `../../src/regions.py` | `density_plots.py`, `group_histograms.py`: national 2025/2026 pools (same cleaning as stage 04), palette, the shared histogram figures, Census groups |

## Process
Each script is standalone with argparse. Run it with `.venv/bin/python stages/02_explore/<script>.py`.

| Script | What it shows | Default output |
|---|---|---|
| `plot_events.py` | time histograms for all five events in a 2×3 grid | `output/event_histograms_density.png` |
| `plotByDate.py` | histograms of *when* marks were set (season weeks) | shows only; writes `output/date_histograms.png` with `--save` |
| `plotRandom.py` | CA vs NY boys 1600 m histograms | shows only (`savefig` is commented out) |
| `dateRegression.py` | time ~ meet date, one OLS per event; `--sweep` tests the top-N cutoff | `output/date_regression.png` with `--save` |
| `density_plots.py` | national KDEs, 2025 vs 2026 overlay + log-scale tail | `output/density/` |
| `group_histograms.py` | national pools (5 events × 2 sexes, one figure), then each state (51), Census region (4) and division (9) vs the pool, per event × sex (`--years` default 2025,2026; `--levels state,region,division`) | `output/<years>/` |
| `plotIndividual.py` | per-athlete progression lines; `--diagnostics` adds a fit-quality figure | `output/individual_progression.png` with `--save` |

2026 per state: `--dir <ST>/<sex> --suffix r` (mile as run, unconverted); pooled: `--pool northeast --sex {m,f}` (mile converted, fenced as in stage 04). Details: `references/scripts.md`.

## Outputs
- `output/2026/<ST>_<sex>/`: one folder per northeast state and sex (18 in all,
  generated 2026-10-08). Each holds `event_histograms.png`,
  `date_histograms.png`, `date_regression.png` and `date_regression.txt` (the
  printed slope/R² table).
- `output/2026/NE_m/`, `output/2026/NE_f/`: the same four files with all nine
  states pooled.
- `output/*.png|pdf`: legacy-NY figures from earlier runs.
- `output/individual/<ST>-<event>[_diagnostics].png`: earlier per-list progression figures.
- `output/density/density_{2025,2026,2025_vs_2026}_{m,f}.png` (`paths.EXPLORE_DENSITY`).
- `output/2025-2026/` (`paths.explore_groups`), national, 2025 + 2026 stacked (one row per athlete-season):
  - `pooled/histogram.png`: all 10 pools.
  - `by_{state,region,division}/{100m,200m,400m,800m,mile}/histogram_{m,f}.png` + `shifts_{m,f}.csv` (51 / 4 / 9 rows); `mile` = 1600 m boys / 1500 m girls.

## Verify
- No panel reads "file missing" (that would be a path regression). In the 2026
  runs every mile slot reads 1600m, 1 mile or 1500m, matching
  `_config/data_conventions.md`.
- Date histograms should sit inside mid-March to late June (the outdoor season).
- `date_regression.txt` slopes are negative (85 of 90 on 2026-10-08; the 5 positive are small RI/VT fields, noise).
