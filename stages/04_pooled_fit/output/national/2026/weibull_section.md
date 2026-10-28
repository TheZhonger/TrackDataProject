<!-- weibull-section:start -->

## Weibull-type tail (alternative to the GPD)

Written by `weibull_fit.py` on 2026-10-14 (200 bootstrap resamples). Rerun it if the pools change; `run_all.py` drops this section when the pool sizes no longer match.

**The model.** The GPD above assumes the tail stops at a wall. The Weibull-type tail assumes it never stops but thins out ever faster: P(t or faster | past u) = exp(−((x−μ)/s)^θ + ((u−μ)/s)^θ) with x = −t. θ is the tail weight (2 is a bell curve's tail, larger is lighter, ∞ is the Gompertz tail). No wall, and its local GPD shape is negative at u and creeps to 0 further out, which is the slide the GPD fits here show. Fitted to the top 10% of each pool. Comparison and theory: `stages/04_pooled_fit/references/pooled_method.md` §12, `_config/evt_theory.md` §3.7.

### Fits

| event | u | N_u | θ [95% CI] | local ξ at u → at record | Δ log-lik vs GPD (same u) | 25th-fastest: spread of 1 in N across thresholds, Weibull / GPD |
|---|---|---|---|---|---|---|
| 100m boys | 11.46 | 19,606 | 6.4 [2.9, 50.0] | -0.59 → -0.07 | +85 | 1.15 / 1.95 |
| 100m girls | 13.19 | 15,693 | ≥50 (Gompertz limit) [50.0, 50.0] | -0.46 → -0.09 | +9 | 1.53 / 1.07 |
| 200m boys | 23.36 | 18,112 | ≥50 (Gompertz limit) [25.8, 50.0] | -0.52 → -0.07 | +66 | 1.45 / 2.49 |
| 200m girls | 27.33 | 14,979 | ≥50 (Gompertz limit) [50.0, 50.0] | -0.47 → -0.10 | -1 | 1.86 / 1.23 |
| 400m boys | 52.63 | 13,456 | ≥50 (Gompertz limit) [50.0, 50.0] | -0.56 → -0.09 | +18 | 1.88 / 1.66 |
| 400m girls | 1:02.08 | 9,799 | ≥50 (Gompertz limit) [8.5, 50.0] | -0.50 → -0.10 | +10 | 1.42 / 1.19 |
| 800m boys | 2:04.32 | 11,881 | 40.2 [5.8, 50.0] | -0.88 → -0.10 | +85 | 2.29 / 1.97 |
| 800m girls | 2:28.10 | 8,587 | ≥50 (Gompertz limit) [50.0, 50.0] | -0.68 → -0.09 | +34 | 1.69 / 2.38 |
| 1600m boys | 4:39.36 | 10,866 | ≥50 (Gompertz limit) [50.0, 50.0] | -0.65 → -0.09 | +25 | 1.86 / 2.39 |
| 1500m girls | 5:07.24 | 6,972 | ≥50 (Gompertz limit) [6.3, 50.0] | -0.70 → -0.09 | +46 | 1.75 / 2.47 |

### Return periods, Weibull vs GPD

The same query times as the GPD table above (each pool's 1st, 5th, 25th and 100th fastest marks). "1 in N athlete-seasons". The last columns are an in-sample check: athletes the Weibull fit expects at or under that time, divided by the number who were, and how surprising that is. Under a correct model the expected count z at the k-th best mark is Gamma(k, 1) -- for the record, Exp(1), whose 95% range is 0.025-3.69 -- so p = GammaCDF(z) is uniform: only p below 0.025 or above 0.975 is a real misfit.

| event | rank | time | 1 in (Weibull) [95% CI] | 1 in (GPD) | Weibull ÷ GPD | predicted / actual | p |
|---|---|---|---|---|---|---|---|
| 100m boys | 1 | 9.88 | 457,942 [167,093, 1,101,942] | 432,905,497 | 0.00 | 0.44 | 0.355 |
| 100m boys | 5 | 10.05 | 51,463 [28,027, 86,024] | 129,016 | 0.40 | 0.78 | 0.353 |
| 100m boys | 25 | 10.24 | 6,688 [4,983, 8,612] | 6,291 | 1.06 | 1.20 | 0.845 |
| 100m boys | 100 | 10.36 | 2,233 [1,880, 2,593] | 1,853 | 1.20 | 0.90 | 0.159 |
| 100m girls | 1 | 11.01 | 74,139 [51,641, 103,677] | 214,277,074 | 0.00 | 2.15 | 0.884 |
| 100m girls | 5 | 11.20 | 17,403 [13,289, 22,138] | 75,248 | 0.23 | 1.83 | 0.950 |
| 100m girls | 25 | 11.40 | 4,630 [3,816, 5,456] | 6,141 | 0.75 | 1.38 | 0.961 |
| 100m girls | 100 | 11.59 | 1,555 [1,356, 1,745] | 1,453 | 1.07 | 1.03 | 0.612 |
| 200m boys | 1 | 19.86 | 970,469 [580,329, 1,679,612] | 6,132,694,550 | 0.00 | 0.19 | 0.172 |
| 200m boys | 5 | 20.46 | 22,608 [17,732, 29,540] | 21,509 | 1.05 | 1.62 | 0.906 |
| 200m boys | 25 | 20.73 | 5,966 [5,020, 7,183] | 4,411 | 1.35 | 1.23 | 0.870 |
| 200m boys | 100 | 21.02 | 1,745 [1,559, 1,968] | 1,270 | 1.37 | 1.05 | 0.696 |
| 200m girls | 1 | 22.71 | 29,252 [21,999, 39,105] | 4,801,024 | 0.01 | 5.15 | 0.994 |
| 200m girls | 5 | 23.03 | 10,493 [8,392, 13,210] | 52,447 | 0.20 | 2.87 | 0.999 |
| 200m girls | 25 | 23.34 | 4,286 [3,603, 5,148] | 7,821 | 0.55 | 1.41 | 0.970 |
| 200m girls | 100 | 23.78 | 1,394 [1,240, 1,583] | 1,490 | 0.94 | 1.08 | 0.795 |
| 400m boys | 1 | 45.21 | 80,412 [54,960, 122,445] | 11,116,705 | 0.01 | 1.68 | 0.813 |
| 400m boys | 5 | 45.82 | 18,517 [13,907, 25,259] | 61,555 | 0.30 | 1.46 | 0.851 |
| 400m boys | 25 | 46.61 | 3,694 [3,045, 4,499] | 4,374 | 0.84 | 1.46 | 0.981 |
| 400m boys | 100 | 47.29 | 1,152 [1,008, 1,310] | 1,091 | 1.06 | 1.17 | 0.950 |
| 400m girls | 1 | 51.98 | 23,640 [16,726, 36,035] | 94,642 | 0.25 | 4.16 | 0.984 |
| 400m girls | 5 | 52.31 | 14,501 [10,692, 21,156] | 36,070 | 0.40 | 1.36 | 0.806 |
| 400m girls | 25 | 53.32 | 3,756 [3,071, 4,897] | 4,633 | 0.81 | 1.05 | 0.617 |
| 400m girls | 100 | 54.54 | 949 [831, 1,121] | 922 | 1.03 | 1.04 | 0.649 |
| 800m boys | 1 | 1:47.86 | 45,252 [26,421, 61,791] | 181,991 | 0.25 | 2.63 | 0.928 |
| 800m boys | 5 | 1:48.60 | 19,196 [12,588, 24,907] | 35,192 | 0.55 | 1.24 | 0.741 |
| 800m boys | 25 | 1:49.85 | 5,334 [4,028, 6,446] | 5,780 | 0.92 | 0.89 | 0.311 |
| 800m boys | 100 | 1:51.81 | 1,029 [895, 1,158] | 947 | 1.09 | 1.16 | 0.935 |
| 800m girls | 1 | 2:01.84 | 116,630 [66,940, 205,862] | 598,907,334 | 0.00 | 0.74 | 0.522 |
| 800m girls | 5 | 2:04.52 | 16,122 [10,867, 23,358] | 15,120 | 1.07 | 1.07 | 0.616 |
| 800m girls | 25 | 2:07.48 | 2,737 [2,101, 3,421] | 1,453 | 1.88 | 1.26 | 0.895 |
| 800m girls | 100 | 2:10.07 | 775 [661, 897] | 436 | 1.78 | 1.11 | 0.862 |
| 1600m boys | 1 | 3:55.63 | 88,066 [57,365, 134,013] | 182,065 | 0.48 | 1.23 | 0.709 |
| 1600m boys | 5 | 3:59.32 | 18,189 [13,382, 24,795] | 29,371 | 0.62 | 1.20 | 0.712 |
| 1600m boys | 25 | 4:04.56 | 2,856 [2,380, 3,459] | 3,844 | 0.74 | 1.52 | 0.990 |
| 1600m boys | 100 | 4:08.44 | 926 [815, 1,059] | 1,124 | 0.82 | 1.17 | 0.953 |
| 1500m girls | 1 | 4:09.13 | 232,786 [107,490, 491,751] | 147,324 | 1.58 | 0.30 | 0.259 |
| 1500m girls | 5 | 4:15.67 | 21,635 [14,086, 33,894] | 18,505 | 1.17 | 0.64 | 0.223 |
| 1500m girls | 25 | 4:23.73 | 2,231 [1,832, 2,760] | 2,377 | 0.94 | 1.25 | 0.890 |
| 1500m girls | 100 | 4:29.41 | 635 [561, 742] | 703 | 0.90 | 1.10 | 0.839 |

Figures: `figures/weibull_vs_gpd_<sex>.png`, both models' 1-in-N curves against the data for each event, and each model ÷ the data.

### Reading it

- **The records.** For 9 of 10 events the Weibull calls the fastest mark *less* rare than the GPD does, by a factor of 2 to 6,319 (1500m girls: Weibull ÷ GPD 1.58). The GPD's numbers there are set by where its wall landed ("at the wall" above). The Weibull has no wall, so its record return periods come from the shape of the tail, not from a boundary. Their intervals are still wide: one mark per pool is very little information.
- **Below the records the two models agree** within a factor of 1.88 at the 25th and 100th fastest marks (Weibull ÷ GPD 0.55–1.88), where both are well supported by data.
- **In-sample calibration** (last column): 34 of 40 predictions are within count noise (k ± 2√k). Outside it: 200m girls rank 1 (5.15), 200m girls rank 5 (2.87), 200m girls rank 25 (1.41), 400m boys rank 25 (1.46), 400m girls rank 1 (4.16), 1600m boys rank 25 (1.52). Above 1 means the Weibull expects more athletes that fast than there were: at those ranks it is too heavy.
- **θ is weakly identified.** 100m girls, 200m boys, 200m girls, 400m boys, 400m girls, 800m girls, 1600m boys, 1500m girls ran to the Gompertz limit (θ capped at 50); 100m boys, 200m boys, 400m girls, 800m boys, 1500m girls have θ intervals more than 10 wide. θ and μ trade off along a flat ridge: many pairs draw nearly the same curve over the observed range. So read the return periods, not θ. Every θ is above 2 (lowest 6.4), so the tail is *lighter* than a bell curve's, consistent with the GPD's negative ξ.
- **Threshold stability.** The 25th-fastest mark's 1 in N varies less across thresholds (top 20% to top 1%) under the Weibull than under the GPD for 5 of 10 events.
- **Physical meaning.** The local shape is strongly negative at u (the tail is bending hard there), and less so at the record, but it never reaches a wall. The fast end of a season's list behaves like the top of a talent distribution, not like a population pressing against a physiological limit.

<!-- weibull-section:end -->
