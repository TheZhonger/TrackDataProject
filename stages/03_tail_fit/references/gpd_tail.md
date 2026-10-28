# `gpd_tail.py` — single-event inference

Layer 3 reference for stage 03 (moved from the old CLAUDE.md §4). The theory it
implements is in `../../../_config/evt_theory.md`.

It fits a GPD to one event's tail, scores query times, prints a report, and
writes a 4-panel diagnostic figure to `../output/`. To use it, edit the CONFIG
block at the top and run

```bash
.venv/bin/python stages/03_tail_fit/gpd_tail.py
.venv/bin/python stages/03_tail_fit/gpd_tail.py stages/01_scrape/output/legacy/NY/m/800.csv   # other file
```

It can be run from any directory, because paths come from `src/paths.py`.

## CONFIG knobs

| Knob | Meaning |
|---|---|
| `EVENT_FILE`, `EVENT_LABEL` | which CSV (default `legacy/NY/m/100r.csv`), and a cosmetic label for plots |
| `QUERY_TIMES` | times to score; seconds or `"M:SS.ss"` strings |
| `THRESHOLD_MODE` | `"quantile"` (fraction, 0.98 = fastest 2%), `"count"` (number of exceedances), or `"absolute"` (a time in seconds) |
| `THRESHOLD_VALUE` | interpreted per the mode above |
| `DEDUPE_ATHLETES` | collapse each athlete to their single best mark (default `True`) |
| `POPULATION_SIZE` | override for `n` when the CSV is a top-N list |
| `N_BOOTSTRAP` | bootstrap resamples for CIs; `0` disables |
| `RANDOM_SEED`, `MAKE_PLOTS` | |
| `FIGURE_PATH` | defaults to `output/gpd_diagnostics<EVENT_LABEL>.png` |

## Design decisions that are not negotiable

**`floc=0` in the fit.**

```python
genpareto.fit(excesses, floc=0)
```

The excesses `y = x − u` are measured *from* the threshold, so zero is where
they start by construction. Letting scipy also fit a location would let the
distribution slide sideways and double-count `u`. That produces a fit that looks
fine and means nothing.

**Athlete dedupe is on by default.** The GPD derivation assumes independent
observations. One sprinter with eight races in the file is eight correlated
rows, and the tail looks denser than it is. On the synthetic test file this went
from 18,077 rows to 3,999 athletes, a factor of 4.5. The dedupe key is
name/team/state.

**`parse_time()` deliberately does not strip commas.** `"2:05,4"` would silently
become 174.0 instead of 125.4. A NaN you can see beats a wrong number you can't.

**The bootstrap re-selects the threshold inside each resample.** Threshold choice
is part of the estimator, so it has to be inside the loop or the CIs are too
narrow.

**The ξ < −0.5 warning.** Below −0.5, maximum likelihood is non-regular
(`_config/lessons.md`). The script prints a warning that the standard errors
are untrustworthy and suggests a lower threshold. Don't remove it.

## The four diagnostic panels

1. **Mean residual life plot**: mean excess above `u`, plotted against `u`.
   Theory says that for a GPD this is *linear* in `u`. Find the lowest `u` where
   the plot goes straight and stays straight; that's a valid threshold.
2. **Shape stability plot**: ξ refit at many thresholds, with confidence bands.
   Theory says that once the theorem holds, ξ stops moving. You are looking for
   a **plateau**. A sliding ξ means there is no valid regime yet.
3. **QQ plot**: empirical quantiles against GPD quantiles. Points on the
   diagonal mean the fit is good.
4. **Log-scale tail fit**: empirical exceedance probabilities against the
   fitted curve, on a log y-axis. This is where extrapolation quality shows up.
   The y-axis is deliberately floored two decades below the rarest real point.
   With ξ < 0 the fitted curve dives to ~0 at the endpoint, and would otherwise
   stretch the axis to 1e-14 and squash everything readable.
