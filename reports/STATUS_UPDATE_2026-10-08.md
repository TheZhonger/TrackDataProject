# Status update: scraping progress and northeast fit quality

*Written 2026-10-08 (afternoon, PDT) for Daren. This file is meant to be downloaded and deleted; nothing in the repo links to it. The same facts, in durable form, are in the docs (`scraping.md` §7–8, the stage `CONTEXT.md` files, `pooled_method.md`).*

Every number below was computed from the files on disk when this was written: the scrape ledger, `summary.csv`, `summary.md`, `state_fits.csv`, and the last `run_all` log. Nothing was typed by hand.

## The short version

- **Scraping:** the northeast is complete for 2025 and 2026. A national 2026 sweep is about halfway through its **boys** half and **nothing is running right now**. It stopped on `2026-OK-m-1600r` (page 5 error). Boys 100/200/400/800m are done for all 51 states (545,585 rows outside the northeast). Girls outside the northeast, boys mile/1500m, and all of 2025 outside the northeast are untouched.
- **A new problem in that national data:** five boys 800m lists (IN, KS, KY, LA, MD) came back with **5 rows each** instead of thousands. They are real marks from a partial page render, and the scraper marked them `done`. They need a rescrape (command in section 1.3).
- **Fitting, pooled:** of 10 northeast pools, **1 is trustworthy** (100m boys, ξ ≈ −0.334), **6 are usable with a caveat**, and **3 are not reliable yet** (800m girls, 1600m boys, 1500m girls: thin tails or very wide ξ intervals). In 9 of 10 pools the shape parameter ξ keeps drifting toward 0 as the threshold rises, which means the GPD has not been reached anywhere in the data.
- **Fitting, per state:** 90 single-state fits agree in direction with the pooled drift but are too noisy to confirm it, and the small states (RI, VT, ME) cannot carry a tail at all.
- **What you can use today:** return periods for benchmarks a bit slower than each pool's record (e.g. 100m boys 10.61 s is 1 in 1,093). **Not** the return period of any pool's fastest mark.

---

## 1. Scraping

### 1.1 Where it stands

Ledger: **455 jobs, 454 done, 1 failed.** 454 CSVs on disk, none with a blank `time` column (the blank-marks guard from the earlier incident is in place). Last ledger write: 2026-10-08T10:49:24-07:00. The last command run was:

```
scrapeAll.py --states all --years 2026 --sex m,f --events 100m,200m,400m,800m,1600m,1mile,1500m --retry-failed
```

States with data, by event (the northeast is 9 states, so 51 means all of them):

| event file | 2025 boys | 2025 girls | 2026 boys | 2026 girls |
|---|---|---|---|---|
| `100r.csv` | 9 | 9 | 51 | 9 |
| `200r.csv` | 9 | 9 | 51 | 9 |
| `400r.csv` | 9 | 9 | 51 | 9 |
| `800r.csv` | 9 | 9 | 51 | 9 |
| `1600r.csv` | 9 | 9 | 40 | 9 |
| `1miler.csv` | 9 | 9 | 9 | 9 |
| `1500r.csv` | 9 | 9 | 9 | 9 |

(2026 boys `1600r` is 40 = 9 northeast + 31 others, and includes the September WY test run. The DC and VT boys 3200m test files are not in this table.)

**Throughput so far (outside the northeast, 2026):** 202 jobs, 6,254 pages, 11.1 hours of scraping, i.e. **6.4 s per page** including delays and retries.

### 1.2 What remains

The run order is year → sex → event → state, so the sweep does all boys events first (finishing 1600m, then the mile and 1500m), then girls, state by state within each event.

| piece | jobs | pages (low–high) | hours (low–high) |
|---|---|---|---|
| Boys 1600m, 11 states (OK retry + OR SC SD TN TX UT VA WA WI WV) | 11 | 255 | 0.5 |
| Redo the five partial boys 800m lists (IN KS KY LA MD) | 5 | 66 | 0.1 |
| Boys mile + 1500m, 42 non-NE states | 84 | 168–331 | 0.3–0.6 |
| Girls 100/200/400/800m, 42 states | 168 | 4,724 | 8.4 |
| Girls 1600m, 42 states | 42 | 652 | 1.2 |
| Girls mile + 1500m, 42 states | 84 | 168–331 | 0.3–0.6 |
| **2026 total** | **394** | **6,034–6,360** | **11–11 h** |
| 2025, all 42 non-northeast states, both sexes, 7 event files | 588 | 12,212–12,539 | 22–22 h |

*How the estimate is built:* pages per job are the observed national boys averages for each event (the two partial boys pieces are instead scaled by each state's own 100m size) (100m 42, 200m 38, 400m 28, 800m 23, 1600m 23); girls scale by the northeast girls-to-boys row ratio per event (1600m uses only CT ME NH NJ PA, the states where girls run it) (100m 0.87, 200m 0.89, 400m 0.79, 800m 0.83, 1600m 0.68). The mile and 1500m lists outside the northeast have never been fetched, so I bracket them: low = 2 pages per job (one page plus the end-of-list probe, if most states have small lists), high = 3.9 pages per job (the northeast average). Time uses 6.4 s per page. Treat it as a ±30% figure.

### 1.3 Commands, in order

Run from the repo root. These are zsh-safe (the `scrape` function avoids the unquoted-`$S` problem from earlier).

```bash
cd "/Users/dzhong/Documents/Track Project"
scrape() { .venv/bin/python stages/01_scrape/scrapeAll.py "$@"; }

# 0. Redo the five broken 800m lists. --force is scoped to exactly these five jobs.
scrape --states IN,KS,KY,LA,MD --years 2026 --sex m --events 800m --force

# 1. Resume the national 2026 sweep where it stopped. NO --force.
scrape --states all --years 2026 --sex m,f --events 100m,200m,400m,800m,1600m,1mile,1500m --retry-failed

# 2. Then 2025 outside the northeast.
scrape --states all --years 2025 --sex m,f --events 100m,200m,400m,800m,1600m,1mile,1500m --retry-failed
```

If a run is blocked (exit code 2), rerun the same command later with `--retry-failed` and **without** `--force`. `--force` deletes everything it selects up front, which is what caused the missing files last time. Exit code 3 means the mark cell has moved again (`blank-marks`); rerunning will not help.

### 1.4 Problems found in the national data

1. **Five boys 800m lists are truncated: IN, KS, KY, LA, MD (5 rows each).** The ledger shows all five were scraped back-to-back (06:56:25 to 06:57:07, about 8 s each), fetched one page with 5 rows, then stopped as `duplicate` and were marked `done`. The 5 rows are genuine (IN's leader is 1:47.86), but a state's 800m list has thousands. IN has 2,873 boys in the 100m. This looks like a partial page render during a brief site hiccup. It is the same family of silent failure as the zero-row page and the blank-mark cell: **a short first page looks exactly like a tiny list**, and nothing in the scraper checks it. Apart from HI (item 3), no other national file has this signature.
2. **`2026-OK-m-1600r` failed** at page 5 (`error`, 1 attempt). It resumes from its saved partial on the next run.
3. **HI boys `1600r.csv` has 1 row.** Hawaii very likely contests the mile or 1500m instead, which is the situation VT and NY girls were in. That should resolve once `1mile` and `1500m` are scraped, since the most-rows rule then picks the right file. I can't confirm it until then.
4. **The national "who runs which mile" map does not exist yet.** The non-northeast states have only a `1600r` file, so the most-rows rule would call all of them 1600m runners by default. Do not read a mile map off the data until the mile and 1500m files exist.
5. **Junk rows exist in the national files**, as they do in the northeast. Example: WV's 800m list has `2:37:40.00` for one athlete. These are source errors on the slow side, and stage 4's fence is designed to remove them. They are not scraper bugs.
6. **I scanned all 199 national boys files for wrong-event data** (the §0 slug trap): fastest and median time per file against plausible ranges. Nothing was the wrong event. TX's fast 100m (9.88) and 200m (19.86) are plausible for a state that size.

**A scraper guard worth adding (not done):** flag a job whose first page is short while the same state's other events are large. The cross-event check that already exists in stage 4 (`coverage_check`) has exactly this idea, but it runs after scraping, on pools. It would have flagged all five lists. I have not changed the scraper.

---

## 2. Fitting: how well does it work, northeast only

The fits use only the nine northeast states, 2026. The national data is not modelled yet (and the girls and mile data it would need do not exist yet).

### 2.1 What the symbols mean

Work in terms of how much **faster than a threshold** a run is.

| symbol | meaning | physical reading |
|---|---|---|
| `u` | threshold, in seconds | "only look at runs faster than this" |
| `y = u − t` | how many seconds faster than `u` a time `t` is | the *excess* |
| `N_u` | number of athletes faster than `u` | how much data the tail fit really has |
| `ζ = N_u / n` | fraction of all athletes clearing `u` | the probability of beating `u` at all |
| `σ` | scale, in seconds | how spread out the excesses are |
| `ξ` | shape (unitless) | what the tail does near the record |
| wall `= u − σ/abs(ξ)` (for `ξ < 0`) | the fastest time the model allows | the fitted physiological limit |

**The probability that a random athlete runs time `t` or faster is**

```
P(t) = ζ · (1 + ξ·y/σ) ^ (−1/ξ)          the return period is 1 / P
```

**What ξ means, physically.** Write `d` for how far a time is from the wall. Then the chance of running that fast falls like `d^(1/|ξ|)`. So:

| ξ | exponent 1/\|ξ\| | what halving the gap to the wall does | in words |
|---|---|---|---|
| −0.5 | 2 | makes the run 4× rarer | the tail ends abruptly |
| −0.35 | 2.9 | 7× rarer | a firm wall (100m boys sits here) |
| −0.2 | 5 | 32× rarer | |
| −0.1 | 10 | 1,024× rarer | almost no wall: an exponential, Gumbel-like tail |
| 0 | ∞ | | no wall at all |

So **ξ close to 0 means "I can't see a wall in this data"**, and `σ/|ξ|` then blows up. That is why the wall estimates collapse in the thin pools (section 2.5).

### 2.2 One worked example, so you can check any pool by hand

100m boys: `u = 11.91 s`, `σ = 0.5343`, `ξ = -0.3475`, `N_u = 5,664`, `n = 28,686`.

1. `ζ = N_u/n = 5,664/28,686 = 0.1974`, so about 20% of boys clear `u`.
2. The wall: `u − σ/|ξ| = 11.91 − 0.5343/0.3475 = 10.372 s`. The pipeline reports 10.372.
3. A 10.61 s run: `y = 11.91 − 10.61 = 1.30`; `1 + ξy/σ = 1 − 0.3475×1.30/0.5343 = 0.1545`.
4. `P = 0.1974 × 0.1545^(1/0.3475) = 0.1974 × 0.00463 = 9.150e-04`, a return period of **1 in 1,093**. The pipeline reports 1 in 1,093.

That is the entire model. Everything else is about how far to trust `u`, `σ`, and `ξ`.

### 2.3 The ten pooled fits

| pool | n | N_u | ζ | u | ξ (95% CI) | σ | textbook SE | bootstrap ± | ratio |
|---|---|---|---|---|---|---|---|---|---|
| 100m boys | 28,686 | 5,664 | 0.197 | 11.91 | -0.347 [-0.364, -0.332] | 0.53 | 0.009 | 0.016 | 1.8× |
| 100m girls | 25,101 | 4,669 | 0.186 | 13.76 | -0.280 [-0.324, -0.266] | 0.71 | 0.011 | 0.029 | 2.7× |
| 200m boys | 26,179 | 4,309 | 0.165 | 24.04 | -0.315 [-0.352, -0.302] | 1.05 | 0.010 | 0.025 | 2.4× |
| 200m girls | 23,393 | 922 | 0.039 | 26.45 | -0.198 [-0.261, -0.158] | 0.83 | 0.026 | 0.052 | 2.0× |
| 400m boys | 18,625 | 948 | 0.051 | 51.32 | -0.250 [-0.305, -0.207] | 1.45 | 0.024 | 0.049 | 2.0× |
| 400m girls | 14,810 | 1,091 | 0.074 | 1:00.86 | -0.237 [-0.299, -0.199] | 2.31 | 0.023 | 0.050 | 2.1× |
| 800m boys | 16,877 | 665 | 0.039 | 1:59.49 | -0.198 [-0.262, -0.129] | 2.91 | 0.031 | 0.066 | 2.1× |
| 800m girls | 14,027 | 232 | 0.017 | 2:16.84 | -0.095 [-0.244, -0.004] | 3.29 | 0.059 | 0.120 | 2.0× |
| 1600m boys | 15,482 | 433 | 0.028 | 4:25.65 | -0.205 [-0.398, -0.147] | 6.75 | 0.038 | 0.125 | 3.3× |
| 1500m girls | 10,467 | 173 | 0.017 | 4:42.04 | -0.130 [-0.343, -0.025] | 7.13 | 0.066 | 0.159 | 2.4× |

**Reading it.**
- `N_u` is the real sample size of a tail fit, not `n`. It runs from 173 (1500m girls) to 5,664 (100m boys), a factor of 33. Noise falls like 1/√N_u, so the 1500m girls' ξ is about 6× less certain than the 100m boys' for the same method.
- **The textbook standard error is too optimistic.** `(1+ξ)/√N_u` is the large-sample formula. The bootstrap interval, which also re-selects the threshold on every resample, is 1.8–3.3× wider in every pool. Trust the bootstrap column.
- **ξ is negative in all ten pools and every CI excludes 0**, but the two thinnest only just: 800m girls up to -0.004 and 1500m girls up to -0.025. A bounded tail is supported everywhere, but for those two pools the data barely rule out ξ = 0 (no wall).

### 2.4 "Sliding ξ": what it means in numbers

If the GPD were the right model above some threshold, ξ would stay put as `u` rises (that is the theory in `evt_theory.md` §3.2). The pipeline refits ξ over a grid of thresholds and fits a weighted line of ξ against `log N_u`. The `t` below is that slope divided by its uncertainty. Under a constant ξ it would sit near 0 ± 1.

| pool | trend t | ξ drift across the grid | verdict |
|---|---|---|---|
| 100m boys | -1.4 | 0.030 | **plateau** |
| 100m girls | -5.1 | 0.137 | sliding |
| 200m boys | -5.5 | 0.133 | sliding |
| 200m girls | -6.1 | 0.167 | sliding |
| 400m boys | -7.2 | 0.207 | sliding |
| 400m girls | -5.3 | 0.180 | sliding |
| 800m boys | -9.6 | 0.276 | sliding |
| 800m girls | -6.3 | 0.223 | sliding |
| 1600m boys | -5.5 | 0.181 | sliding |
| 1500m girls | -5.0 | 0.204 | sliding |

- **100m boys is the only plateau** (|t| = 1.4, drift 0.03). The other nine have |t| from 5.0 to 9.6. A |t| of 5 would occur by chance about once in 2 million times. The caveat from `pooled_method.md` §6 stands: the estimates at different thresholds share the same athletes, so they are correlated and the chi-square reference is approximate. Even allowing for that, 5–10 is not marginal.
- **All the slopes are negative per log N_u, which means ξ rises toward 0 as the threshold rises.** The further out into the tail you look, the less like a hard wall it appears.
- **The standard reading is bias.** At a low threshold the GPD is being asked to describe part of the body of the distribution, which pushes ξ more negative and the wall closer. Raising `u` removes that bias but leaves fewer points (the bias–variance trade-off, `evt_theory.md` §3.6). A healthy pool shows ξ settling at some `u`, after which you can stop. Nine of these never settle, so there is no threshold where the bias is gone and the variance is still tolerable. More data alone would not fix that; a different model might. This is the most plausible explanation, not a proven one.
- **A second candidate: the pool is a mixture.** Nine states with different depth, walls and timing methods (hand vs electronic, altitude, wind) blend into one curve whose tail shape differs from any single state's. Section 2.7 tests this.
- **A third, untested:** times are recorded to 0.01 s, so the very top has ties and rounding that distort a fit using only a few hundred points.

### 2.5 The wall, and why its confidence interval explodes

| pool | fastest | fitted wall | margin (fastest − wall) | wall 95% CI | CI width | margin < CI width? |
|---|---|---|---|---|---|---|
| 100m boys | 10.44 | 10.37 | 0.07 s | 10.33 – 10.41 | 0.08 s | yes |
| 100m girls | 11.27 | 11.21 | 0.06 s | 11.12 – 11.47 | 0.35 s | yes |
| 200m boys | 20.77 | 20.72 | 0.05 s | 20.62 – 20.94 | 0.32 s | yes |
| 200m girls | 23.03 | 22.24 | 0.79 s | 21.27 – 23.10 | 1.83 s | yes |
| 400m boys | 46.34 | 45.52 | 0.82 s | 44.73 – 46.37 | 1.64 s | yes |
| 400m girls | 52.14 | 51.10 | 1.04 s | 49.79 – 52.68 | 2.88 s | yes |
| 800m boys | 1:49.11 | 1:44.82 | 4.29 s | 1:39.09 – 1:47.55 | 8.46 s | yes |
| 800m girls | 2:01.84 | 1:41.99 | 19.85 s | -19 s – 2:01.46 | 140.92 s | yes |
| 1600m boys | 3:57.50 | 3:52.62 | 4.88 s | 3:42.22 – 4:06.18 | 23.96 s | yes |
| 1500m girls | 4:11.00 | 3:47.11 | 23.89 s | 36.52 – 4:17.75 | 221.24 s | yes |

**The mechanism, with the worst pool.** The wall is `u − σ/|ξ|`, so a small uncertainty in ξ near 0 turns into a huge one in the wall. 800m girls: `u = 2:16.84`, `σ = 3.29`. Holding σ fixed and letting ξ move across its own CI:

| ξ | σ/\|ξ\| | wall |
|---|---|---|
| -0.244 (low end) | 13 s | 2:03.34 (**slower** than the 2:01.84 record: impossible) |
| -0.095 (estimate) | 35 s | 1:41.99 |
| -0.004 (high end) | 867 s | -730 s (a **negative** time) |

So the interval is not saying "the wall is somewhere between X and Y". It is saying the data cannot pin the wall at all. The same thing, milder, is why every pool's margin is smaller than its CI width: **every `1 in N` for a pool's own fastest mark (`rp_of_fastest`) is reporting where the endpoint landed, not how rare the run was.** Do not compare them across events.

### 2.6 What you can actually use: benchmark return periods

A time a little slower than the record sits where the fit is supported by data. The slowest benchmark in each pool's query table:

| pool | benchmark | 1 in | 95% CI | relative width (hi − lo)/value | near the wall? |
|---|---|---|---|---|---|
| 100m boys | 10.76 | 267 | 238 – 302 | 24% | no |
| 100m girls | 12.18 | 169 | 155 – 211 | 33% | no |
| 200m boys | 21.85 | 184 | 169 – 212 | 23% | no |
| 200m girls | 24.93 | 243 | 208 – 286 | 32% | no |
| 400m boys | 48.88 | 174 | 153 – 207 | 31% | no |
| 400m girls | 56.81 | 131 | 115 – 153 | 29% | no |
| 800m boys | 1:54.77 | 180 | 155 – 217 | 34% | no |
| 800m girls | 2:14.13 | 142 | 122 – 169 | 33% | **yes** |
| 1600m boys | 4:17.36 | 147 | 126 – 173 | 32% | no |
| 1500m girls | 4:37.77 | 113 | 95 – 137 | 37% | **yes** |

- For the eight pools not flagged, the benchmark is "1 in 131–267" and its CI is only 23%–34% wide. That is a number with meaning.
- **For the two thinnest pools (800m girls, 1500m girls) even the slowest benchmark is flagged as sitting at the wall.** They have no usable benchmark yet; the tail is too short to extrapolate from.
- This is the useful output for the project's goal: a comparable "how rare is a 1-in-150 performance" across events. At that level the pools are roughly consistent in how well they are determined, which is more than can be said of the records.

### 2.7 Per state against pooled

Is the pool hiding real differences between states? Among the single-state fits on fields over 2,000 athletes (the only ones with enough data), compare how much ξ varies *between states* with how uncertain a single state's ξ is *by itself* (its bootstrap half-width).

| pool | pooled ξ | states with n ≥ 2,000 | their mean ξ | between-state SD | typical bootstrap ± | SD / ± |
|---|---|---|---|---|---|---|
| 100m boys | -0.347 | 5 | -0.304 | 0.057 | 0.089 | 0.64 |
| 100m girls | -0.280 | 5 | -0.275 | 0.093 | 0.147 | 0.64 |
| 200m boys | -0.315 | 5 | -0.305 | 0.041 | 0.093 | 0.44 |
| 200m girls | -0.198 | 5 | -0.259 | 0.021 | 0.095 | 0.22 |
| 400m boys | -0.250 | 4 | -0.311 | 0.020 | 0.102 | 0.20 |
| 400m girls | -0.237 | 3 | -0.292 | 0.063 | 0.088 | 0.72 |
| 800m boys | -0.198 | 4 | -0.232 | 0.031 | 0.120 | 0.26 |
| 800m girls | -0.095 | 4 | -0.322 | 0.096 | 0.135 | 0.71 |
| 1600m boys | -0.205 | 4 | -0.299 | 0.107 | 0.142 | 0.75 |
| 1500m girls | -0.130 | 2 | -0.356 | 0.055 | 0.071 | 0.77 |

**Reading it.** A ratio under 1 means states differ no more than their own uncertainty would produce, so there is no detectable mixture effect. Over 1 means real differences. No pool is above 1. With only 2–5 states per row the SD is itself rough, so treat this as a screen, not a test. It does not say the slide is *caused* by mixing; it says mixing is not visibly large.

**Is the pooled ξ different from the per-state ξ because of mixing, or because of where the threshold sits?** The slide predicts: the higher the threshold (the smaller ζ), the closer ξ is to 0. Compare each pool's ζ and ξ with the average of its single-state fits (fields ≥ 1,000, ξ > −0.5):

| pool | pooled ζ | states' mean ζ | pooled ξ | states' mean ξ | pooled threshold | pooled ξ is | matches the slide? |
|---|---|---|---|---|---|---|---|
| 100m boys | 0.197 | 0.088 | -0.347 | -0.283 | lower | more negative | yes |
| 100m girls | 0.186 | 0.090 | -0.280 | -0.272 | lower | more negative | yes |
| 200m boys | 0.165 | 0.115 | -0.315 | -0.292 | lower | more negative | yes |
| 200m girls | 0.039 | 0.119 | -0.198 | -0.259 | higher | nearer 0 | yes |
| 400m boys | 0.051 | 0.110 | -0.250 | -0.295 | higher | nearer 0 | yes |
| 400m girls | 0.074 | 0.101 | -0.237 | -0.270 | higher | nearer 0 | yes |
| 800m boys | 0.039 | 0.062 | -0.198 | -0.276 | higher | nearer 0 | yes |
| 800m girls | 0.017 | 0.075 | -0.095 | -0.293 | higher | nearer 0 | yes |
| 1600m boys | 0.028 | 0.069 | -0.205 | -0.284 | higher | nearer 0 | yes |
| 1500m girls | 0.017 | 0.154 | -0.130 | -0.293 | higher | nearer 0 | yes |

**10 of 10 pools match.** Wherever the pooled fit sits at a higher threshold than the per-state fits, its ξ is nearer 0, and wherever it sits lower, ξ is more negative. The largest gaps are the thin pools (800m girls: pooled -0.095 at ζ = 0.017, against a state average of about -0.293). So the disagreement between pooled and per-state ξ is *consistent with* the same slide seen from two thresholds. That is a weaker claim than "pooling does not distort the tail", which this cannot show.

**The caveat, stated plainly:** at the level of individual fits the link is weak. Across the 52 single-state fits, the rank correlation between ζ and ξ is -0.11 (p = 0.46), which is not distinguishable from no relationship. Each state's threshold is noisy (40% of all 90 single-state fits are fixed-count fallbacks), so one fit says little. The 10-of-10 pattern is a sign test across pools, suggestive but not proof, and the pools are not independent of each other.

**Single-state fits overall (90):** 34 used ForwardStop, 20 the mixture method, 36 fell back to a fixed number of exceedances because neither converged. **14 have ξ < −0.5**, mostly RI, VT and ME. Below −0.5 maximum likelihood is non-regular (`_config/lessons.md`): the standard errors and CIs are invalid and the fit is being pinned by the fastest one or two marks. Those are small fields, and this is exactly why the project pools.

Among the 41 fits on fields over 2,000, ξ rose with threshold more often than it fell in 33. That points the same way as the pooled slide, but a single state's sweep is too noisy to show it by itself (the end-to-end drift ranges from 0.12 to 1.3 with no pattern). Consistent, not confirmed.

### 2.8 Verdict per pool

Criteria, so it is mechanical: **GREEN** = plateau (|t| < 2) and a converged threshold. **RED** = fewer than 300 exceedances or a ξ CI half-width above 0.10. **YELLOW** = everything else (enough data, but ξ slides).

| pool | verdict | why |
|---|---|---|
| 100m boys | **GREEN** | plateau; ξ is a measurement |
| 100m girls | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 200m boys | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 200m girls | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 400m boys | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 400m girls | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 800m boys | **YELLOW** | enough data, but ξ slides, so ξ is biased by where u was put |
| 800m girls | **RED** | thin tail (N_u = 232) or wide ξ CI (±0.12) |
| 1600m boys | **RED** | thin tail (N_u = 433) or wide ξ CI (±0.13) |
| 1500m girls | **RED** | thin tail (N_u = 173) or wide ξ CI (±0.16) |

100m girls and 200m boys are YELLOW with a footnote: ForwardStop saturated (so many athletes that it rejects every threshold) and no method converged, so their threshold is a fallback.

---

## 3. Known defects and what I would do next

**Defects, not fixed (report only):**
1. **Wall CI is unusable when ξ is near 0** (800m and 1500m girls), as in section 2.5. A fix: drop or cap bootstrap draws with ξ above about −0.05 before forming the wall interval, and report how many were dropped.
2. **The scraper cannot see a short first page** (section 1.4). Five lists were silently truncated.
3. **`threshold_select.py` (stage 3's script) still has the two missing guards** (the scale-relative agreement test and "nothing rejected" detection). Stage 4 and `run_states.py` work around them; the single-file script does not.
4. **The hardcoded athletic.net password fallback** is still in `individualScrape.py`.

**Next steps, in the order I would do them:**
1. Rescrape the five 800m lists, then resume the sweep (section 1.3). Cost: mostly waiting.
2. Add the short-first-page guard to the scraper before running the girls (hundreds of jobs; the more jobs, the more chances for another hiccup).
3. The modelling question is now bigger than the data question. Nine of ten pools slide, so more states will not fix the shape. The two options already in the docs are the r-largest order statistics per meet, and accepting a penultimate approximation and reporting the drift as a bias term. A cheap first test of the mixture hypothesis: fit the pool restricted to the two or three deepest states and see if ξ stabilises.
4. Use 2025 as a check. It is scraped for the northeast but unused. If 100m boys again plateaus near −0.33, that is real; if it does not, the plateau was luck.

