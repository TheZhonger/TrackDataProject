# Pooled northeast tail analysis — method and findings

Layer 3 reference for stage 04 (this was `pooled2026/README.md` before the
2026-10-07 reorganisation). Companions: [evt_theory.md](../../../_config/evt_theory.md)
(the statistics) and [scraping.md](../../01_scrape/references/scraping.md) (where the CSVs come from).
This stage pools the
scrape across states into one distribution per event × sex, plots it, and
fits a GPD tail to it, for 2026, for 2025, or for both seasons stacked (§10).

Run with the project venv interpreter (the system `python` has no numpy). Paths
are anchored on the repo via `src/paths.py`, so any working directory works:

```bash
.venv/bin/python src/pool_data.py                       # load + report, no fitting
.venv/bin/python stages/04_pooled_fit/plot_pooled.py    # the three histogram figures
.venv/bin/python stages/04_pooled_fit/gpd_pooled.py --event 100m --sex m
.venv/bin/python stages/04_pooled_fit/run_all.py        # everything, plus the summary (2026)
.venv/bin/python stages/04_pooled_fit/run_all.py --years 2025
.venv/bin/python stages/04_pooled_fit/run_all.py --years 2025,2026
.venv/bin/python stages/04_pooled_fit/compare_years.py  # the three datasets side by side
```

Every script takes `--years` (default `2026`).

| File | Role |
|---|---|
| `pool_data.py` | loading, distance conversion, pooling. numpy/pandas only |
| `plot_pooled.py` | histograms, per-state small multiples, conversion QC |
| `gpd_pooled.py` | threshold selection + GPD fit for one event × sex |
| `run_all.py` | all 5 events × 2 sexes for one dataset, the figures, and its `summary.md` |
| `compare_years.py` | 2026 vs 2025 vs stacked: `output/comparisons/northeast_seasons/year_comparison.md` (§10) |
| `output/<dataset>/` | `summary.md`, `summary.csv`, `figures/` for `2026`, `2025`, `2025-2026` |
| `output/` | layout in `output/README.md`: `northeast/<years>/`, `national/<years>/`, `comparisons/`, `_cache/thresholds.json` (selection cache, shared) |

Figures land in `output/<dataset>/figures/histograms/` and `.../figures/gpd/`.
`gpd_pooled.py` imports `gpd_tail` and `threshold_select` from `stages/03_tail_fit/`,
which is the one deliberate cross-stage import.

---

## 1. Scope: the northeast nine, five events

CT MA ME NH NJ NY PA RI VT, both sexes, 2026 (and 2025, §10), five events: 100 m, 200 m,
400 m, 800 m and the metric mile (1600 m-equivalent for boys, 1500 m-equivalent
for girls, §2–3). Ten pools. Before 2026-10-08 only the 100 m and the mile were
pooled, and both sexes' mile went onto 1600 m.

Stage 01's 2026 output now also holds boys 100–800 m for the other 42 states (partial national
sweep, `scraping.md` §7). **None of it is used here.** Without girls or the mile/1500 m lists a
national pool of the same ten events cannot be built, and the northeast list is the guard (`src/northeast.py`).

WY and the DC/VT 3200 m files are scraper test artifacts and are excluded
outright -- there is no `3200m` event spec. The scope is fixed rather than
configurable-to-anything for a reason: **all five events' pools must rest on
the same states.** Return periods are only comparable across events if they
count the same population, and cross-event comparison is the entire point.
`--states` subsets the nine; it cannot reach outside them.

## 2. One mile-variant per state — the rule that matters most

There is no national mile event. Every northeast state and sex contests one of
three distances (verified 2026-10-08 from the complete scrape):

| | 1600 m | 1 mile | 1500 m |
|---|---|---|---|
| boys | CT ME NH NJ NY PA | MA | RI VT |
| girls | CT ME NH NJ PA | MA | NY RI VT |

Every state *also* has small files for the distances it does not contest, and
those are not a separate field -- they are the same athletes' occasional
off-distance races. **MA's `1600r.csv` holds 30 rows and shares 25 of those 30
names with its `1miler.csv`; RI's holds 10 and shares 6 with its `1500r.csv`.**

So the rule: for each `(state, sex)`, take the single mile-variant file with the
most rows, convert it to that sex's **target distance** -- **1600 m for boys,
1500 m for girls** -- and discard the rest. Converting and concatenating every
mile file a state owns would double-count precisely the athletes at the top of
the tail, which is the one place a duplicate does real damage.

Why the targets differ: each sex is expressed in the distance most of its
field actually runs. NY, the largest girls' field (3,004 runners), contests the
1500 m, so the girls' pool needs the least conversion on 1500 m; the boys' pool
is dominated by 1600 m states. A return period is unit-free, so boys' and girls'
results stay comparable even though their mile pools are on different scales.

Being row-count driven rather than a hardcoded state→distance map means it also
resolves states nobody has mapped yet. The rule lives in `src/distances.py`,
shared with stage 03's per-state fits.

## 3. The distance conversions

```
boys  -> 1600 m :  mile x 0.99419               (= 1600 / 1609.344, distance ratio)
                   1500 x (1600/1500)^1.06      = 1.070805   (Riegel)
girls -> 1500 m :  1600 x (1500/1600)^1.06      = 0.933877   (Riegel)
                   mile x (1500/1609.344)^1.06  = 0.928130   (Riegel)
```

Riegel's model, `t2 = t1 * (d2/d1)^1.06`, says pace slows as distance grows.
The mile→1600 factor is the pure distance ratio instead: Riegel would give
0.99384, 0.014 s apart at 4:00, under timing resolution, and keeping the ratio
leaves every earlier boys result unchanged. Across the 100+ m gaps that involve
the 1500 the two methods differ by about a second, so Riegel is used there.

`mile_conversion_check.png` tests them two ways, one row per sex, and
**neither can be conclusive**, which is stated on the figure and in the printed
output:

- The **ECDF overlay** compares different populations: each sex's native
  target-distance states against the converted ones. MA's milers and CT's 1600
  runners are not the same people, so even a perfect conversion leaves a gap
  if one state is deeper. Curves landing on each other is evidence, not proof.
  On the 2026 data both sexes line up closely; the girls' converted 1600 and
  mile fields sit almost exactly on NY/RI/VT's native 1500 field.
- The **within-athlete table** removes that confound -- the same athletes at
  both distances -- but introduces a worse one. An athlete's main-list mark is
  their season best in their main event; their target-distance mark is a
  one-off at a distance their state barely contests, and almost never a peak
  effort. So the converted prediction *should* look faster, and it mostly does
  (median residual MA boys −7.8 s, VT boys −5.3 s, MA girls −4.9 s). Two girls'
  rows go the other way, CT +4.3 s (26 pairs) and NJ +1.5 s (26 pairs): small
  samples, plausibly 1500s run at championship meets, so read them as noise
  rather than a factor error.

Both point the same way: use the physical factors, and do not tune them to this
data.

## 4. Cleaning

**Outlier gate: one-sided log-IQR fence.** `exp(Q3_log + 2·IQR_log)`, slow side
only.

On logs because race times are right-skewed and roughly lognormal through the
body — the same assumption `threshold_select.py`'s mixture model rests on — and
Tukey's fence assumes rough symmetry, so on raw seconds it over-flags the long
side simply for being long.

One-sided because **the fast tail is the object of inference.** A lower fence
would clip exactly the observations the GPD is fitted to. On this data a
two-sided version would put its lower fence at 9.62 s against a 10.44 s record —
safe today, but only by luck. There is no upside to owning that risk: a track
time cannot be erroneously fast.

`n` is load-bearing for ζ = N_u/n, so the fence moves every return period. The
summary reports `n` before and after and the exact factor (about 1.1 % on the
100 m boys pool, under 0.5 % elsewhere) rather than leaving it implicit.

**Placeholder rows** are removed by name. Four `Test Athlete #N` entries sit in
`stages/01_scrape/output/2026/MA/m/100r.csv`, all on team "Acton-Boxborough Reg". They are dropped
by an anchored name match rather than left to the fence, because a fake record
carrying a *plausible* time would sail straight through a distributional filter.
The match is anchored and exact — plenty of real athletes here are named Testa,
Testone, Volpintesta or Testimony.

**Dedupe key is `(state_dir, name, team)`** — the directory state, never the
`state` column, which is blank on up to 65 % of rows in `RI/f/1500r.csv`.

**Every CSV is read as UTF-8 explicitly.** The 2026 scrape contains bytes Windows'
cp1252 default cannot decode, and the failure is a hard `UnicodeDecodeError`
partway through a file.

## 5. The coverage check — an under-collection detector

A state's share of one event's pool should roughly track its share of another's.
Athletes are not spread evenly across states, but the *ratio* of that spread
between two events is stable, because it is the same schools fielding both
squads. Across the well-scraped states here it sits between 0.75 and 1.85.

**It currently flags nothing** (2026-10-08, all ten pools).

Its history is the best illustration of what it does and does not tell you.
When only `1600m` had been scraped it flagged three pools:

| pool | state | rows | share ratio | expected |
|---|---|---|---|---|
| 1600 m girls | NY | 96 | 0.05 | ~2,800 |
| 1600 m boys | VT | 36 | 0.11 | ~320 |
| 1600 m girls | VT | 16 | 0.10 | ~160 |

Those were read at the time as truncated scrapes. They were not: NY girls and VT
run the **1500 m**, and once `1500r.csv` existed (3,004 NY girls, 317 VT boys,
216 VT girls) the row-count rule in §2 picked it up and the warnings cleared.
The detector was right that the pools were missing depth and tail; the
diagnosis of *why* was wrong. A flag means "this state's list is not the field",
which is either a broken scrape or a slug nobody has fetched -- check both.

## 6. Threshold selection

Three methods, reported side by side, with the failure modes detected rather
than papered over.

**A. ForwardStop** (from `threshold_select.py`, reused unchanged) — sequential
Anderson–Darling tests with FDR control.

**B. Mixture profile MLE** (also reused) — lognormal body + GPD tail, profiled
over `u`.

**C. Shape plateau** (added here) — the lowest threshold from which ξ is
statistically constant, by an inverse-variance weighted chi-square. This is the
theorem's own signature: the GPD is threshold-stable, so if the approximation
holds at `u` it holds at every higher threshold *with the same ξ*. Its caveats
are in the docstring — the estimates come from nested samples so they are
correlated and the chi-square reference is approximate, and the test gets easier
to pass as `N_u` shrinks. It formalises reading the stability plot; it does not
make that reading rigorous.

### Guards this folder adds

`threshold_select.compare()` is **not** used. It was missing the first two guards below
(ported back to stage 03 on 2026-10-09). It still lacks the two further guards after them,
and the shape-plateau selector:

- its agreement criterion is a hardcoded `spread < 0.15` seconds — meaningful
  for a 100 m grid, meaningless for a 1600 m grid spanning ninety seconds. Here
  the criterion is 10 % of the candidate grid span.
- `select_forwardstop` flags "everything rejected" but not "nothing rejected".
  When ForwardStop rejects nothing it returns candidate zero and reports
  `note = "ok"`. That is a fallback, not a selection, and it is exactly what
  produced the false 1600 m corroboration in `threshold_select.md`.

Two further guards were added after this data demanded them:

- **Power saturation.** The parametric bootstrap cannot return a p-value below
  `1/(1+n_sim)`. A run of values pinned on that floor means Anderson–Darling is
  detecting *some* departure with certainty — which at N_u in the thousands is
  nearly guaranteed, since no parametric model is exactly right and a large
  enough sample always says so. `threshold_select.md` records the opposite trap ("small
  samples pass almost any test"); this is its twin at the other end, and pooling
  is what walks into it. See §7.
- **"Tail" fraction.** A mixture whose chosen tail holds more than 25 % of the
  sample is not describing a tail — the GPD half has expanded to cover body
  misfit. `threshold_select.md` flags this for grid-edge optima; it happens at interior
  optima too.

**Agreement is only ever reported when both methods actually converged.** Two
methods failing at the same boundary is not corroboration.

Selection is cached in `output/_cache/thresholds.json`, keyed by event, sex, states,
grid parameters and a fingerprint of the pooled data. The first run is slow; `--refit` forces a recompute.

### Bootstrap honesty note

`gpd_tail.bootstrap` re-selects the threshold inside every resample, which is
right — threshold choice is part of the estimator. Re-running the full
ForwardStop 400 times is not affordable, so the chosen `u` is expressed as its
empirical quantile and each resample re-derives `u` at that quantile. The *rule*
is held fixed, not the value. Read the interval as a lower bound on the true
uncertainty: it captures sampling variation in the threshold but not variation
in the selection procedure itself.

## 7. What the 2026 data actually says

Results from `output/northeast/2026/summary.md`, all ten pools (2026-10-08). The 100 m rows
reproduce the 2026-10-07 results exactly, which is the regression check that the
five-event refactor changed nothing it should not have.

| pool | n | u | N_u | ξ | ξ 95% CI | implied wall | fastest | selected by | shape |
|---|---|---|---|---|---|---|---|---|---|
| 100 m m | 28,686 | 11.91 | 5,664 | −0.348 | [−0.364, −0.332] | 10.37 | 10.44 | plateau | **plateau, ξ ≈ −0.334** |
| 100 m f | 25,101 | 13.76 | 4,669 | −0.280 | [−0.324, −0.266] | 11.21 | 11.27 | *fallback* | sliding (t = −5.1) |
| 200 m m | 26,179 | 24.04 | 4,309 | −0.315 | [−0.352, −0.302] | 20.72 | 20.77 | *fallback* | sliding (t = −5.5) |
| 200 m f | 23,393 | 26.45 | 922 | −0.198 | [−0.261, −0.158] | 22.24 | 23.03 | ForwardStop | sliding (t = −6.1) |
| 400 m m | 18,625 | 51.32 | 948 | −0.250 | [−0.305, −0.207] | 45.52 | 46.34 | ForwardStop | sliding (t = −7.2) |
| 400 m f | 14,810 | 1:00.86 | 1,091 | −0.237 | [−0.299, −0.199] | 51.10 | 52.14 | ForwardStop | sliding (t = −5.3) |
| 800 m m | 16,877 | 1:59.49 | 665 | −0.198 | [−0.262, −0.129] | 1:44.82 | 1:49.11 | ForwardStop | sliding (t = −9.6) |
| 800 m f | 14,027 | 2:16.84 | 232 | −0.095 | [−0.244, −0.004] | 1:41.99 | 2:01.84 | ForwardStop | sliding (t = −6.3) |
| 1600 m m | 15,482 | 4:25.65 | 433 | −0.205 | [−0.398, −0.147] | 3:52.62 | 3:57.50 | ForwardStop | sliding (t = −5.5) |
| 1500 m f | 10,467 | 4:42.04 | 173 | −0.130 | [−0.343, −0.025] | 3:47.11 | 4:11.00 | ForwardStop | sliding (t = −5.0) |

Full CIs, query times and the denominator table are in `output/northeast/2026/summary.md`.

***Only the 100 m boys has a stable GPD regime in 2026**: ξ oscillates
around −0.33 without trend (t = −1.4, drift 0.030 across the grid). **It does
not replicate**: the same pool in 2025 slides (t = −7.2), and so do both seasons
stacked (§10). Read it as a chance flattening of one season's sweep. Every pool
added on 2026-10-08 slides, all in the same direction -- ξ rises toward zero as
the threshold rises -- with end-to-end drifts of 0.13 to 0.28, the largest in
the 800 m boys (0.276). The slide is the rule, not the exception, and it is not
specific to distance events: the 200 m slides as clearly as the mile.

**What changed in the mile pools, and why.** Boys gained VT's 1500 m list
(n 15,204 → 15,482); the selected threshold moved from 4:28.55 to 4:25.65 and ξ
from −0.229 to −0.205. Girls changed far more: NY's 3,004 1500 m runners joined
and everything moved onto 1500 m, so the old "1600 m girls" row has no direct
successor. The new girls' pool still slides, with the thinnest tail of all ten
(N_u = 173).

**Three selection regimes.** ForwardStop is power-saturated on the three
largest pools (100 m both sexes, 200 m boys, n ≥ 25k): it rejects every
candidate threshold, so those fall to the shape plateau (100 m boys, converged)
or an explicit fallback (100 m girls, 200 m boys). On every smaller pool
ForwardStop converges. On the girls' 200 m, 800 m and 1500 m the mixture MLE
also converges -- and disagrees with ForwardStop by 2.0 s, 16.1 s and 33.2 s,
each many times the 10%-of-grid tolerance. Two methods that both claim an answer
and land that far apart are themselves evidence that no single threshold is
right, which is what the sliding ξ says.

**None of the ten fastest-mark return periods is identified**: every record sits
closer to its fitted wall than the wall's own confidence interval is wide, so
those numbers report where the endpoint landed rather than how rare the run was.
Do not compare them across events. Score a slightly slower benchmark instead.

**Wall CI (fixed 2026-10-09).** The bootstrap wall interval used to drop resamples
with ξ ≥ 0 and keep near-zero-ξ resamples as numbers. Since the wall is u + σ/ξ,
those produced "intervals" like [−19.5 s, 2:01.5] for the 800 m girls. Now every
resample with no finite wall (ξ ≥ 0, or a wall at or below 0 s) counts as "unbounded"
(`gpd_tail.endpoint_interval`). The interval's fast end is "unbounded" whenever at
least 2.5% of resamples are. In 2026 that is 800 m girls (5.3%) and 1500 m girls
(2.5%): the data cannot rule out "no wall" there. The other eight pools moved by at
most 0.25 s (the percentile method changed). A finite fast end can still be absurd (the stacked
800 m girls read [26.1 s, 2:00.1], with 1.25% unbounded): that is the bootstrap
saying the data allow almost any wall, not a computation error.

**Per state** (`stages/03_tail_fit/output/2026/state_fits.md`, 90 fits), the
picture is consistent with the pooled slide but cannot confirm it. In 33 of the
41 fits on fields over 2,000, ξ rises with threshold more often than it falls.
But a single state's sweep is too noisy at high thresholds to show a slide
cleanly, and fields under 1,000 cannot support a fit at all. The 2026-10-07
version of this section said "every state's 1600 m slides on its own". That
rested on per-state end-to-end ξ ranges, which are dominated by that noise, so
treat it as unproven. Pooling does not obviously manufacture the slide, and it
cannot be shown state by state either.

**ForwardStop is power-saturated on pooled data.** At the full 100 m boys pool
(n = 28,686) it rejected all 18 candidate thresholds, including two whose own
p-values were 0.150 and 0.255 -- the GPD fits those perfectly well. They were
rejected only because the accumulation statistic averages over the whole
preceding run of floor-value p-values. The selection therefore falls to the
shape plateau.

## 8. What to do next

1. **The GPD is not the right family for 9 of 10 pools anywhere in the observed
   range.** A shape parameter that never stabilises means a different model,
   not a different threshold. (r-largest or block-maxima models are *not* the
   fix: they would show the same penultimate slide; `_config/evt_theory.md` §3.7.)
   §12 tests light unbounded tails. The Gompertz is the leading candidate;
   adopting it for scoring is the next decision.
2. ~~Fix the wall CI~~. Done 2026-10-09 (§7).
3. **Cross-event aggregation is not yet safe.** One of ten pools has a valid
   tail, and no fastest-mark return period is identified. Benchmarks a little
   slower than each pool's record are the usable output for now.
4. ~~2025 is scraped but unused.~~ Done 2026-10-08 (§10): the 100 m boys
   plateau does not replicate, and the slide does, in all 20 new fits.
5. **Threshold selection for stacked seasons.** ForwardStop's goodness-of-fit
   p-values assume independent rows. With repeat athletes they are optimistic,
   and with twice the data the test is even more power-saturated. A
   cluster-aware GoF test, or selecting on one season and validating on the
   other, would fix both.

## 9. Known limitation: the pool is a mixture

Nine states pooled is a mixture, not a sample from one population. Its tail is
dominated by whichever component reaches furthest — here NY and PA, which are
about half the rows together. Pickands–Balkema–de Haan still applies, since a
mixture is just another distribution and the theorem does not care which one, so
the GPD remains the right limiting form. But read the fitted tail as describing
the deep states more than the thin ones.

`hist_by_state_<pool>_<sex>.png` is what makes that visible rather than
assumed: shifted panels mean the mixture structure is real.

## 10. A second season: 2025, and both seasons stacked

Added 2026-10-08. `run_all.py --years 2025` fits the same ten pools on the 2025
scrape; `--years 2025,2026` stacks both seasons. `compare_years.py` writes the
comparison to `output/comparisons/northeast_seasons/year_comparison.md`, which is the source of every number
below.

**How stacking is done.** The unit stays the *athlete-season*: one row per
athlete per season, so "1 in N" means the same thing as in a single-season fit,
and stacking two seasons doubles n without doubling any return period. The cost
is dependence. 30–45% of a season's athletes also appear in the other season,
and 33–48% of the fastest 10% of rows are repeat athletes, because a fast
sophomore is usually a fast junior. The likelihood still gives consistent point
estimates when it treats those rows as independent, but a bootstrap that
resamples *rows* would treat one person's two seasons as two independent
people, and its intervals would come out too narrow. So the stacked fits
resample whole **athletes** (a cluster bootstrap: `gpd_tail.bootstrap(...,
groups=athlete_id)`, with the athlete id `state|name|team`). The threshold
selectors' goodness-of-fit p-values have no such fix and are somewhat
optimistic on the stacked data (§8 item 5).

**Finding 1: the slide replicates; the plateau does not.** All ten 2025 pools
slide (trend t from −4.8 to −8.5, end-to-end ξ drift 0.15–0.25), and so do all
ten stacked pools (t from −6.8 to −12.6). That includes the 100 m boys, the one
pool that looked flat in 2026 (t = −1.4); in 2025 it slides with t = −7.2. The trend
t uses approximate errors (the nested exceedance sets are correlated), so one
season's −1.4 beside −7.2 (2025) and −7.1 (stacked) for the same event is better
read as that one sweep's noise than as a regime that comes and goes.
**No event × sex has a stable GPD regime once two seasons are examined.**

**Finding 2: at the same threshold, the seasons agree.** Each season picks its
own u, and because ξ slides, two fits at different u disagree for that reason
alone. Refitting 2025 at 2026's threshold (fixed in seconds) removes that
effect:

| pool | 100m m | 100m f | 200m m | 200m f | 400m m | 400m f | 800m m | 800m f | 1600m m | 1500m f |
|---|---|---|---|---|---|---|---|---|---|---|
| ξ 2026 at u₂₀₂₆ | −0.347 | −0.280 | −0.315 | −0.198 | −0.250 | −0.237 | −0.198 | −0.103 | −0.205 | −0.130 |
| ξ 2025 at u₂₀₂₆ | −0.327 | −0.268 | −0.340 | −0.188 | −0.260 | −0.205 | −0.261 | −0.125 | −0.266 | −0.130 |
| gap in textbook SEs | +1.6 | +0.8 | −1.7 | +0.3 | −0.3 | +0.9 | −1.5 | −0.3 | −1.2 | 0.0 |

Every gap is under 2 textbook standard errors, and the bootstrap ran 1.8–3.3×
wider than the textbook SE, so all ten are well inside the noise. The tail
shape at a given bar (including the slide itself) is a property of the event,
not of one season. At their *own* thresholds only 100 m boys disagrees, and
only because 2025 chose u = 11.64 against 2026's 11.91.

**Finding 3: the implied wall is not a constant of nature.** The two seasons'
100 m boys walls are 10.37 s [10.33, 10.41] (2026) and 10.23 s [10.15, 10.30]
(2025). The intervals do not overlap, and 2025's fastest boy (10.34) is faster
than 2026's point wall. In the mile, 2026's fastest boy (3:57.50) is outside
2025's whole wall interval [3:59.19, 4:06.71]: one season's "impossible" time was
run the next season. This is the slide seen from the endpoint. ξ estimated at a
reachable threshold is too negative, so the wall u − σ/|ξ| lands too close to
the data, and it moves whenever the data's top end moves. Do not report a wall
as a physiological limit.

**Finding 4: one fixed time, three fits.** `year_comparison.md` §3 scores the
stacked pool's 50th-fastest mark (about one season's 25th) under each fit.
Seasons differ by up to 1.7× (100 m boys 10.57 s: 1 in 1,858 in 2026 against
1 in 1,086 in 2025; 400 m boys 47.74 s: 913 against 629), and the stacked fit
lands between them in the eight sprint and 800 m pools. Season-to-season
variation in a return period is therefore at least as large as one season's
bootstrap interval, which is a floor on how precisely any single "1 in N" can be
meant.

**Finding 5: stacking did not rescue threshold selection, and the stacked mile
fits are not better fits.** With twice the data, ForwardStop rejects every
candidate threshold in more pools (stacked: 4 of 10 by ForwardStop, 2 by the
mixture MLE, 4 fallbacks; 2025: 6, 1, 3). In the two mile pools that pushed the
threshold deep into the body: u = 4:41.6 for boys (N_u = 3,934) and 5:15.4 for
girls (N_u = 3,626, 18% of the pool), against 4:25.7 and 4:42.0 in 2026. Their
ξ intervals are narrow (width 0.41× and 0.25× of 2026's) because N_u is huge and
ξ sits lower on the slide, not because the extra season added information. Read
the stacked 1600 m and 1500 m rows as describing the upper body, not the tail.
In the other eight pools the width ratio runs 0.64–1.37 against the 0.71 that
twice the independent data would give.

**What this means for the project.** A second season makes the case of §8 item
1 stronger, not weaker: the GPD-with-one-threshold model is wrong in a
reproducible way, in every event, in both seasons. The usable output is still a
benchmark slower than the record, scored with season-to-season spread in mind.
Stacking seasons helps once a model that accounts for the slide exists. Until
then it mostly lowers the selected threshold.

## 11. National boys 2026: all 51 states

Added 2026-10-09. `run_all.py --region us --sex m` pools all 50 states plus DC
(`src/regions.py`). Boys first; national girls were added the same day
(`--sex m,f`; boys' numbers reproduced exactly), and the text below covers boys.
Output: `output/national/2026/` (dataset id `us-2026`); the northeast comparison is in
`output/comparisons/northeast_vs_national/region_comparison.md` (`compare_regions.py`). Same cleaning, mile rule
and guards as the northeast. No state is flagged under-collected.

**The pools.** n = 201,026 (100 m), 183,071 (200 m), 134,828 (400 m), 118,971
(800 m) and 108,716 (1600 m-equivalent), about 7× the northeast. Mile sources: 46
states run the 1600 m, HI/OR/RI/VT the 1500 m and MA the mile (`data_conventions.md`).

| pool | u | N_u | ξ [95% CI] | shape | threshold from | wall [95% CI] | fastest |
|---|---|---|---|---|---|---|---|
| 100 m | 11.22 | 10,022 | −0.217 [−0.245, −0.205] | flat at −0.207 | plateau | 9.84 [9.78, 9.97] | 9.88 |
| 200 m | 23.11 | 13,464 | −0.222 [−0.269, −0.214] | slides (t = −10.3) | fallback | 19.82 [19.73, 20.30] | 19.86 |
| 400 m | 50.92 | 5,305 | −0.252 [−0.280, −0.237] | slides (t = −9.9) | fallback | 44.98 [44.71, 45.48] | 45.21 |
| 800 m | 1:58.61 | 3,323 | −0.248 [−0.275, −0.226] | slides (t = −19.8) | ForwardStop | 1:46.39 [1:45.59, 1:47.34] | 1:47.86 |
| 1600 m | 4:15.00 | 543 | −0.125 [−0.204, −0.065] | slides (t = −12.8) | fallback (top of grid) | 3:41.27 [3:13.94, 3:52.79] | 3:55.63 |

**Findings.**
- **A bigger population does not make the slide go away.** Four of five pools slide,
  more steeply than in the northeast (t = −9.9 to −19.8). The 100 m is flat at
  ξ ≈ −0.207 over its top five thresholds. Read that like 2026's northeast 100 m
  plateau, which failed to replicate in 2025: one season, unconfirmed. Its tail also
  contains the questionable 9.88 (`scraping.md` §7).
- **The northeast is slow at the top in the sprints and representative in the
  distances.** At the northeast's 25th-fastest mark, US/NE return-period ratios
  are 0.27 (100 m), 0.42 (200 m), 0.59 (400 m), 0.88 (800 m) and 0.87 (1600 m).
  The empirical ratios (no model) are 0.29, 0.39, 0.78, 1.06 and 0.86. A 10.61 s
  100 m is about 3.6× more common nationally than in the northeast. Fitted and
  empirical agree everywhere except the 400 m (0.59 against 0.78), where the two
  fits are at different heights on the slide.
- **At the northeast's threshold, the national 100 m and 200 m tails are heavier**
  (ξ −0.264 vs −0.347 and −0.251 vs −0.315; 9.0 and 5.7 textbook SEs). That is
  the mixture effect: the national tail is dominated by a few deep sprint states.
  "Who is in the tail" (`us-2026/summary.md`) shows TX holding 12% of the 100 m
  exceedances on 5% of the athletes (×2.2), with GA ×1.7 and FL ×1.8. In the
  1600 m, OR (×3.1), CO (×3.2) and UT (×2.8) play that role. The 400–1600 m ξ at
  matched thresholds agree within noise.
- **Group shifts** (`us-2026/group_shifts.csv`, figures `hist_by_{state,region,division}_*`):
  by median, the South is fastest in the sprints (−0.30 s 100 m, −0.87 s 400 m
  against the national median). The Northeast region is 4.1 s faster than the
  national median in the 1600 m (Middle Atlantic −6.0 s), while East South Central
  is 7.6 s slower. Per-state extremes are mostly **list-depth artifacts**: AR's
  100 m list has 252 boys and its median is 0.57 s fast. A state whose list is
  short relative to its real field looks fast. Read state medians as statements
  about lists, not populations.

## 12. Which tail family? GPD vs light unbounded tails

Added 2026-10-09. `model_compare.py` (models in `stages/03_tail_fit/tail_models.py`)
compares four tail models on 25 pools: northeast 2025 and 2026 (both sexes) and
national boys 2026. Full tables are in `output/comparisons/tail_models/model_comparison.md`;
the theory is in `_config/evt_theory.md` §3.7.

The candidates, all fitted to the same exceedances:
- **GPD**, the current model, with a wall when ξ < 0;
- **exponential**, the GPD with ξ = 0;
- **Weibull-type**, S ∝ exp(−((x − μ)/s)^θ), with tail weight θ;
- **Gompertz**, S ∝ exp(−c(e^{y/b} − 1)), the θ → ∞ limit. It was added because
  most Weibull fits ran to that limit (θ capped at 50).

The last three have no wall, and the last two have the slide built in.

**Results.**
1. **In-sample (top 10%, AIC): Gompertz best in 22 of 25 pools**, Weibull 2, GPD 1
   (2026 northeast 100 m boys, the pool that is genuinely flat that season). The
   Gompertz has the same two parameters as the GPD. Margins are 1–26 AIC units
   in the northeast and 38–169 nationally. The exponential is far worse
   everywhere (+81 to +1,453).
2. **Threshold stability.** Refitted at every threshold from the top 20% to the
   top 1%, the return period of each pool's 25th-fastest mark varies by a
   median factor of 1.22 under Gompertz or Weibull, against 1.60 under the GPD
   and 6.6 under the exponential. The national 400 m and 800 m are the
   exceptions: there the GPD is steadier (1.66, 1.97 against about 1.85, 2.25).
3. **Out of sample** (fit one northeast season, score the other season's marks
   above the same threshold). Gompertz and Weibull beat the GPD's log score in
   **18 of 20** season pairs. The margins are small, 0.000–0.011 nats per mark
   (a few standard errors at most), because in the bulk of the tail all three
   agree. The difference is at the top. Four next-season marks fell past the
   GPD's wall, where it gives zero probability. At each season's **record**,
   the GPD predicted a median 0.09 of the athletes who actually got there
   (Weibull 0.80, Gompertz 0.59; both are consistent with the 0.69 a correct
   model gives, see §13). At ranks 5–100 Weibull and Gompertz are
   calibrated to within 2% (0.98–1.01); the GPD ranges 0.87–1.20. The graphs
   `comparisons/tail_models/predicted_vs_actual_{2025_to_2026,2026_to_2025,us-2026}.png`
   plot this for every rank up to 300: predicted athletes that fast against the
   actual count, with a ±2√k count-noise band.
4. **The slide is reproduced.** A Gompertz or Weibull fitted once at the top 20%
   predicts the GPD ξ a refit at each higher threshold would find
   (`xi_overlay_<dataset>.png`). In 2026 the curve runs through the observed
   sweep for most pools, and it misses the 100 m boys (flat that season) and
   partly the 200 m boys.

**Interpretation.** The fast tail behaves like a light, unbounded (Gompertz-like)
tail, not a bounded GPD tail. The GPD's negative ξ and its wall are what
fitting the wrong family at a finite threshold produces. The practical cost is
at the extreme: the GPD makes the very fastest marks look far rarer than the
next season shows them to be. That is exactly where cross-event scores live.

**Not yet done.**
- Bootstrap intervals for Gompertz return periods (they would reuse
  `gpd_tail.bootstrap`'s design with `tail_models.fit_tail`).
- A threshold rule for it (stability suggests the top 10–20% is fine).
- Switching `run_all.py`'s scoring over. That should be Daren's call once the
  intervals exist.

## 13. Accuracy at the record

Added 2026-10-14. `record_check.py` writes `output/comparisons/record_tests/record_calibration.{md,csv}`
and `record_pit_qq.png`. Yardstick: `_config/evt_theory.md` §3.8. Under a correct
model the expected count at or beyond a season's record is Exp(1), so each record
gives a p that should be Uniform(0, 1). Many records are judged together.

**Records used:**
- 20 out of sample: fit one northeast season, score the other's record, for
  10 pools in both directions;
- 10 national 2026 records, in sample.
- Thresholds tried: the top 10%, 5%, 2%, 1% and 0.5%, for the GPD, Weibull and
  Gompertz.

**Results.**
- **The GPD fails at the record at every threshold:**
  - all 30 records together reject uniformity (KS p ≤ 0.031) at every threshold
    except the top 0.5% (0.064, borderline);
  - at the top 10%, 16 of 30 records fall in the "far too rare" 2.5% tail;
  - it improves as the threshold rises, but still fails on the national
    records at the top 1% (KS p = 0.012).
- **The Gompertz fitted to the top 1% is the best record model found:**
  - KS p = 0.946 over all 30 records (0.956 out of sample, 0.999 national);
  - one record in each 2.5% tail (about 0.75 expected);
  - median z 0.67 (0.69 expected); 5th-best marks KS p = 0.859;
  - still calibrated at ranks 25 and 100 (median error about 11%);
  - 95% predictive-interval coverage 96.2%.
- **At the top 10% the Gompertz and Weibull are already consistent overall**
  (KS 0.81 and 0.49), but 3 records sit in the "too heavy" tail.
  - Those are the national girls' sprints; at the top 1% they become ordinary.
- The "Weibull 0.80 vs Gompertz 0.59" record-ratio contrast in §12 is noise:
  both are consistent with the Exp(1) median of 0.69.

**The girls' sprints: threshold, not grade mixture.** National 2026 girls'
100/200/400m records, fitted grade by grade (9–12, 12 records):
- At the top 10% they lean "too heavy" (KS p = 0.018, median p 0.76).
- At the top 1% they are fine (KS p = 0.737).
- The boys' grade records are fine at both thresholds.

So near the very top the girls' sprint tail bends harder than the top 10% as a
whole suggests, and a fit closer to the record captures it. The boys' 9.88 (grade
10, p = 0.12) is unremarkable under the model.

**Caveats.**
- Choosing the best of 15 model × threshold combinations on the same 30 records
  is mildly optimistic.
- At the top 1%, small pools have only about 100 exceedances, so marks slower
  than u must be scored empirically.
- The decisive test is out of sample at **Census-division** level once national
  2025 is rescraped: about 180 records.

**Provisional rule:** score with a Gompertz tail fitted to each pool's top 1%,
and score marks slower than that threshold empirically (rank / n). Confirm it
with the division-level test before switching `run_all.py`.

### 13.1 The division test (2026-10-22): the provisional rule fails

Each of the 9 Census divisions is its own pool, fitted on one national season and
scored on the other, both directions: 180 out-of-sample records
(`record_check.py --part d`; section D of `output/comparisons/record_tests/record_calibration.md`).

The rule and the pass criterion were fixed beforehand. Gompertz at the top 1%:

| | record KS p | tails low / high (95% range 1–9) | median z (0.69) |
|---|---|---|---|
| all 180 | 0.039 | 13 / 7 | 0.54 |
| fit 2025 → score 2026 | 0.863 | | 0.74 |
| fit 2026 → score 2025 | 0.005 | | 0.42 |

- Rank-5 KS is 0.020; ranks 25/100 are within 11.2% (criterion 11%).
- The 4 regions do better (KS 0.236, 6 / 2 tails), but still fail on the low tail.

**It is still the best candidate tested.**
- The GPD is far worse at both thresholds: 36–60 records called too rare.
- The Gompertz at the top 10% errs the other way: 15 too heavy.

**Diagnosis.**
- *Not data coverage.* The share of elite marks (top 1% / 0.1% of both seasons)
  per pool is the same in 2025 and 2026: a median ratio of 0.97–1.02 relative to
  pool size.
- *It is the most extreme records.* Three are called essentially impossible
  (z ≈ 0):
  - Cooper Lutkenhaus, 1:47.04 800 m (TX, 2025);
  - Josiah Tostenson, 3:36.85 1500 m (OR, 2025, likely a professional meet);
  - Lisa Raye, 11.30 100 m (RI, 2025; 0.32 s clear of New England, worth auditing).
- Without those three, the KS is 0.086, but the 2026 → 2025 direction still
  fails (0.016).
- So some seasons produce individual prodigies beyond what a Gompertz fitted to a
  "normal" season's top 1% allows. Either the true extreme tail is heavier than
  Gompertz, or the extreme varies between seasons more than one season's fit can
  know.

**Consequence.** `run_all.py` stays on the GPD for now. The Gompertz at the top 1%
remains the best record model found, but it is not validated. Next candidates
for Daren to choose from (not tried here, to avoid fitting the test):
- a Weibull at the top 1%;
- a between-season variance term in the predictive interval;
- an audit of the extreme marks.

### 13.2 ForwardStop for the Gompertz and the predictive p (2026-10-22)

**Changes:**
- `threshold_select.py` has a `model` parameter (gpd / gompertz); the GPD results are
  unchanged.
- `record_check.py` part D judges on the **predictive p**: the record's p averaged over 40
  bootstrap refits, which includes the parameter uncertainty.
- The rule under test was `gompertz-fs`: the threshold that ForwardStop selects on the fit
  season. The settings are the same as for the GPD, fixed before the run.

**Result:** `gompertz-fs` fails.
- Predictive KS is 0.006. The tails are 3 / 13, so the misses are on the too-heavy side.

**The cause is the fallback, not the selection:**
- In the 77 division pools with a real selection, it is calibrated (KS 0.642, tails 3 / 5).
- In 89 pools ForwardStop rejected nothing and fell back to the top 20%, which is too heavy.
- The A² test has low power against the body misfit that matters at the record.
- 12 of the 14 "all rejected" pools are boys' 100 m. Ties at hundredths are a probable cause
  (not tested).

**Other rules in the same run:**
- *Gompertz 1%:* the predictive p fixes its tails (6 / 3), but it still fails 2026 → 2025.
- *Gompertz 5%:* it passes everything (KS 0.824, tails 2 / 6), but it was selected on these
  records.

Details are in section 7 of `output/comparisons/record_tests/record_test_report_2026-10-22.md`.
The next fair test needs new records: a 2024 season.

### 13.3 Fallback fix and de-tying (2026-10-22)

**Changes:**
- `threshold_select.select_forwardstop(..., fallback_u=)`: when nothing is rejected,
  return `fallback_u` instead of the lowest candidate.
- `threshold_select.dequantize(x, 0.01, rng)`: jitter ForwardStop's input by ±0.005 s.
  - Ties at 0.01 s made the A² test reject a continuous model at every threshold in large
    pools: national boys' 100 m, p = 0.01 raw vs 0.13–0.79 jittered.
  - Fits use the raw times.
- `record_check.py`: the rule `gompertz-fs5` (ForwardStop, "nothing rejected" → q = 0.95)
  is `D_RULE`.

**Division test, `gompertz-fs5`, predictive p:**

| version | KS | 25→26 | 26→25 | tails | median z |
|---|---|---|---|---|---|
| raw | 0.921 | 0.305 | 0.726 | 3 / 9 | 0.77 |
| de-tied (current code) | 0.079 | 0.099 | 0.717 | 3 / 9 | 0.82 |
| fixed top 5% | 0.937 | 0.301 | 0.491 | 2 / 6 | 0.73 |

- **Both pass all the record checks** and fail only the rank-25/100 check. Every rule fails
  that check: 0.11–0.12 against 0.093 (95% 0.083–0.104) for a perfect model, so it is a
  body or season effect.
- **De-tying lowers the rejection rate:**
  - divisions: nothing rejected 123, ok 57 (raw: 89 / 77 / 14 all rejected);
  - the real selections have a median at the top 12%, which is too low for the record.
- **The A² test measures the fit of the excesses, not the accuracy at the record.**
- **Candidate next rule (not implemented):** ForwardStop on a grid of 95% to 99.5%, i.e. a
  floor at the top 5%.

## 14. National Gompertz, 2025 + 2026 stacked (`gompertz_pooled.py`)

**Method:**
- `load_pool(years=(2025, 2026), region="us")`.
- ForwardStop (Gompertz, de-tied, `fallback_u` = q 0.95, grid 0.80–0.995 × 18, α 0.05,
  199 sims, min 25).
- The fit uses the raw-data quantile at the selected level.
- 200 athlete-cluster bootstrap resamples; each one re-takes u at the same level.
- The selections are cached in `gompertz_forwardstop.csv`.
- Outputs are in `output/national/2025-2026/gompertz/` (dataset id `us-2025-2026`).

**Selected thresholds:**
- ok in 7 pools (top 0.5–6.2%);
- all rejected (→ 0.5%) for boys' 800 m and 1600 m;
- nothing rejected (→ 5%) for girls' 400 m.

**In-sample records (20):**
- all are inside the Exp(1) 95% range; the predictive p is 0.050–0.978;
- boys' 100 m 9.82: p = 0.058;
- girls' 200 m / 400 m 2026: p = 0.96 / 0.98 (too heavy).

**Check:** all c and b point estimates are inside their bootstrap CIs. Before the
raw-quantile fix, the boys' 100 m c was outside its CI: the jittered u included or
excluded a tie block differently from the resamples.

**Density plots:** `stages/02_explore/density_plots.py` → `stages/02_explore/output/density/` (moved from stage 04 on 2026-10-22).
- The 2025 and 2026 bodies are almost identical.
- The seasons differ only at S < ~1e-4 (the top 10–20 athletes).

**Goodness of fit (`gompertz_fit_quality.py` → `output/national/2025-2026/gompertz/fit_quality.md`, 2026-10-22).**

Views:
- detrended QQ of the excesses, with a band from a parametric bootstrap that rounds,
  cuts at u and refits each sample;
- expected ÷ actual at every distinct tail time (Gamma(c,1)/c band; S read at t + 0.005 s
  for 0.01 s rounding);
- de-tied A² p;
- out of sample 2025↔2026 against a correct-model yardstick (two seasons simulated from
  the stacked fit, 20 reps).

Results:
- In sample: 95–100% of the ratios are in the band, with a typical error of 0.5–2.5%.
  This matches a correct model.
- Out of sample: a typical error of 3.6–13%, against 2.4–10.9% for a correct model.
  The largest excess is 400m m (+1.9 pt) and 800m m (+1.9 pt).
- All 10 pools are "good" under the stated rules; 800m m is the weakest.
- A² p = 0.025–0.83.
- Records: see §13.3.

Method notes (each was needed to make a correct model pass the checks on simulated
rounded tails):
- jitter only the fitted excesses, not the pool;
- the QQ band must refit each sample;
- the worst ratio is only meaningful at counts ≥ 100.

**Queries (`gompertz_query.py`, 2026-10-22).** Scores any time against these fits.
- Formula: RP(t) = 1 / (ζ · exp(−c · expm1((u − t)/b))), t and u in seconds. Valid only
  for t ≤ u; slower times print "outside the tail model". GPD and Gompertz return periods
  are not interchangeable: they come from different tails and thresholds.
- Intervals: percentiles of RP(t) over the 200 cluster-bootstrap draws in
  `gompertz_boot.csv` (each draw = its own u, ζ, c, b). Default levels 80% and 95%
  (`--level`). The marginal c/b CIs in `gompertz_fit.csv` cannot be combined (c, b
  correlated).
- Expected count per season = mean(n_2025, n_2026) / RP (`n_2025`, `n_2026` columns in
  `gompertz_fit.csv`).
- Field size: each query prints mean(n_2025, n_2026) for its pool, plus the expected count
  in one season.
- Equivalent times (same sex, the other 4 events): solve S_E(t) = 1/RP, so
  t = u_E − b_E · log1p(−ln q / c_E), with q = 1/(RP · ζ_E). This is valid only when q ≤ 1;
  otherwise the time is "slower than E's threshold". The interval comes from E's draws at
  the point RP (E's fit uncertainty only). `--no-equiv` turns it off.
- `--check`: the closed form reproduces `TailFit.return_period` and the rank rows of
  `gompertz_queries.csv` (point and 95% CI). The inverse returns the queried time.
- Counts (2026-10-22): slower than u, the headline is counted, RP = n/k over the stacked
  pool, with an exact Poisson 95% CI; faster than u, the count is printed under the model,
  and a model RP outside the count's range is flagged. Each season's own "k of n = 1 in X"
  is shown. Equivalents below another event's u are counted (time at the same share).
  Source: `gompertz_counts.csv` (distinct time × season counts, 4 dp so converted mile
  marks keep their values), written by `gompertz_query.py --build-counts`. Its n must equal
  `gompertz_fit.csv`'s n.
- Why counts slower than u and the model faster: below u, k ≳ 1,000, so a count is within
  ~3% with no model risk. Near the record, k is tiny: a count is capped at 1 in n, cannot
  see the margin (rank-based), and is 0 past the record.
