# Pooled 2026 US -- GPD tail fits

One row per event x sex. Times in seconds; `rp_of_fastest` is the return period of that pool's own fastest mark, read as "one athlete-season in this many".

## Fits

| event | sex | n | u_sec | N_u | xi | xi_ci_lo | xi_ci_hi | sigma | implied_wall_s | fastest_s | wall_margin_s | rp_of_fastest | rp_identified | wall_ci_lo | wall_ci_hi | plateau | converged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100m | m | 201026 | 11.22 | 10022 | -0.2169 | -0.245 | -0.2053 | 0.2983 | 9.84 | 9.88 | 0.036 | 416653490 | False | 9.779 | 9.973 | xi flat at -0.207 | True |
| 100m | f | 159462 | 13.55 | 27876 | -0.2603 | -0.2758 | -0.2531 | 0.6683 | 10.98 | 11.01 | 0.028 | 201359964 | False | 10.933 | 11.098 | xi flat at -0.252 | True |
| 200m | m | 183071 | 23.11 | 13464 | -0.2224 | -0.2688 | -0.2142 | 0.7315 | 19.82 | 19.86 | 0.04 | 5776362325 | False | 19.725 | 20.301 | sliding xi -- no plateau | False |
| 200m | f | 150736 | 28.05 | 24843 | -0.2757 | -0.286 | -0.2675 | 1.5079 | 22.58 | 22.71 | 0.129 | 4884633 | False | 22.475 | 22.728 | xi flat at -0.267 | True |
| 400m | m | 134828 | 50.92 | 5305 | -0.2515 | -0.2802 | -0.2369 | 1.493 | 44.98 | 45.21 | 0.227 | 10968781 | False | 44.705 | 45.478 | sliding xi -- no plateau | False |
| 400m | f | 98298 | 1:00.24 | 4996 | -0.2361 | -0.2564 | -0.2165 | 2.2548 | 50.69 | 51.98 | 1.292 | 94346 | True | 50.048 | 51.28 | sliding xi -- no plateau | True |
| 800m | m | 118971 | 1:58.61 | 3323 | -0.2482 | -0.2747 | -0.2263 | 3.0329 | 1:46.39 | 1:47.86 | 1.468 | 182644 | False | 105.59 | 107.34 | sliding xi -- no plateau | True |
| 800m | f | 86001 | 2:33.68 | 15228 | -0.3091 | -0.3443 | -0.3043 | 9.8747 | 2:01.74 | 2:01.84 | 0.102 | 674735039 | False | 121.532 | 124.071 | sliding xi -- no plateau | True |
| 1600m | m | 108716 | 4:15.00 | 543 | -0.1253 | -0.2036 | -0.0651 | 4.2273 | 3:41.27 | 3:55.63 | 14.364 | 182139 | False | 193.939 | 232.795 | sliding xi -- no plateau | False |
| 1500m | f | 69720 | 4:36.12 | 349 | -0.1067 | -0.206 | -0.0346 | 5.6952 | 3:42.72 | 4:09.13 | 26.405 | 147173 | False | 106.102 | 245.25 | sliding xi -- no plateau | False |

## Query times

| event | sex | time | P(this fast or faster) | 1 in | 95% CI on 1 in |
|---|---|---|---|---|---|
| 100m | m | 9.88 | 2.400e-09 | 416,653,490 **at the wall** | unstable |
| 100m | m | 10.05 | 7.790e-06 | 128,366 | 66,833 - 1,500,510 |
| 100m | m | 10.24 | 1.593e-04 | 6,279 | 5,081 - 10,690 |
| 100m | m | 10.36 | 5.403e-04 | 1,851 | 1,648 - 2,420 |
| 100m | f | 11.01 | 4.966e-09 | 201,359,964 **at the wall** | unstable |
| 100m | f | 11.20 | 1.337e-05 | 74,783 | 46,605 - 572,783 |
| 100m | f | 11.40 | 1.633e-04 | 6,125 | 5,033 - 11,214 |
| 100m | f | 11.59 | 6.891e-04 | 1,451 | 1,306 - 1,901 |
| 200m | m | 19.86 | 1.731e-10 | 5,776,362,325 **at the wall** | unstable |
| 200m | m | 20.46 | 4.657e-05 | 21,471 | 16,808 - 512,652 |
| 200m | m | 20.73 | 2.269e-04 | 4,407 | 3,793 - 14,026 |
| 200m | m | 21.02 | 7.877e-04 | 1,270 | 1,154 - 2,054 |
| 200m | f | 22.71 | 2.047e-07 | 4,884,633 **at the wall** | unstable |
| 200m | f | 23.03 | 1.899e-05 | 52,665 | 32,298 - 142,145 |
| 200m | f | 23.34 | 1.276e-04 | 7,837 | 6,076 - 11,891 |
| 200m | f | 23.78 | 6.703e-04 | 1,492 | 1,313 - 1,796 |
| 400m | m | 45.21 | 9.117e-08 | 10,968,781 **at the wall** | unstable |
| 400m | m | 45.82 | 1.629e-05 | 61,405 | 34,131 - 457,343 |
| 400m | m | 46.61 | 2.288e-04 | 4,371 | 3,554 - 6,646 |
| 400m | m | 47.29 | 9.172e-04 | 1,090 | 974 - 1,287 |
| 400m | f | 51.98 | 1.060e-05 | 94,346 | 41,571 - 422,960 |
| 400m | f | 52.31 | 2.779e-05 | 35,990 | 19,776 - 84,934 |
| 400m | f | 53.32 | 2.160e-04 | 4,629 | 3,540 - 6,335 |
| 400m | f | 54.54 | 1.084e-03 | 922 | 815 - 1,042 |
| 800m | m | 1:47.86 | 5.475e-06 | 182,644 **at the wall** | 74,015 - 1,950,379 |
| 800m | m | 1:48.60 | 2.836e-05 | 35,261 | 21,271 - 93,889 |
| 800m | m | 1:49.85 | 1.728e-04 | 5,785 | 4,531 - 8,449 |
| 800m | m | 1:51.81 | 1.055e-03 | 948 | 837 - 1,091 |
| 800m | f | 2:01.84 | 1.482e-09 | 674,735,039 **at the wall** | unstable |
| 800m | f | 2:04.52 | 6.593e-05 | 15,167 | 12,431 - 1,007,534 |
| 800m | f | 2:07.48 | 6.874e-04 | 1,455 | 1,319 - 2,993 |
| 800m | f | 2:10.07 | 2.292e-03 | 436 | 406 - 583 |
| 1600m | m | 3:55.63 | 5.490e-06 | 182,139 **at the wall** | 68,354 - 5,152,453 |
| 1600m | m | 3:59.32 | 3.404e-05 | 29,377 **at the wall** | 17,510 - 93,723 |
| 1600m | m | 4:04.56 | 2.601e-04 | 3,845 **at the wall** | 3,016 - 5,264 |
| 1600m | m | 4:08.44 | 8.894e-04 | 1,124 **at the wall** | 963 - 1,303 |
| 1500m | f | 4:09.13 | 6.795e-06 | 147,173 **at the wall** | 50,270 - 7,033,435 |
| 1500m | f | 4:15.67 | 5.406e-05 | 18,498 **at the wall** | 10,975 - 57,795 |
| 1500m | f | 4:23.73 | 4.207e-04 | 2,377 **at the wall** | 1,831 - 3,248 |
| 1500m | f | 4:29.41 | 1.422e-03 | 703 **at the wall** | 595 - 817 |

## Denominator sensitivity

The slow-side log-IQR fence removes rows from `n`, and every return period scales with `n` through zeta = N_u/n. `rp_sensitivity` is the factor by which the unfenced pool would change them.

| event | sex | n before fence | n after | factor |
|---|---|---|---|---|
| 100m | m | 203,989 | 201,026 | x1.0147 |
| 100m | f | 160,520 | 159,462 | x1.0066 |
| 200m | m | 185,022 | 183,071 | x1.0107 |
| 200m | f | 151,578 | 150,736 | x1.0056 |
| 400m | m | 136,056 | 134,828 | x1.0091 |
| 400m | f | 98,986 | 98,298 | x1.0070 |
| 800m | m | 119,419 | 118,971 | x1.0038 |
| 800m | f | 86,342 | 86,001 | x1.0040 |
| 1600m | m | 109,131 | 108,716 | x1.0038 |
| 1500m | f | 69,986 | 69,720 | x1.0038 |

## Who is in the tail

Each state's share of the exceedances (the athletes faster than u, which are what the GPD is fitted to) against its share of the pool. Ratio > 1 means over-represented among the fast. A pool is a mixture, and this is whose tail it really is. Top 8 per pool.

| event | sex | state: tail share (pool share, ratio) |
|---|---|---|
| 100m | m | TX 12% (5%, x2.2), CA 11% (12%, x0.9), GA 6% (3%, x1.7), FL 5% (3%, x1.8), OH 4% (5%, x0.9), IL 4% (5%, x0.8), NC 3% (2%, x1.6), MI 3% (6%, x0.5) |
| 100m | f | CA 10% (12%, x0.8), TX 10% (6%, x1.7), GA 5% (3%, x1.5), OH 4% (5%, x0.9), IL 4% (4%, x0.9), FL 4% (2%, x1.6), NY 3% (4%, x0.8), PA 3% (3%, x1.1) |
| 200m | m | CA 10% (12%, x0.8), TX 10% (6%, x1.7), GA 6% (3%, x1.6), OH 4% (5%, x0.9), FL 4% (2%, x1.8), IL 4% (5%, x0.8), NC 3% (2%, x1.6), PA 3% (3%, x1.2) |
| 200m | f | CA 10% (12%, x0.8), TX 10% (6%, x1.6), OH 5% (5%, x0.9), GA 4% (3%, x1.4), IL 4% (5%, x0.9), FL 4% (2%, x1.6), NY 4% (5%, x0.8), PA 3% (3%, x1.2) |
| 400m | m | TX 10% (6%, x1.6), CA 9% (12%, x0.8), GA 5% (3%, x1.5), OH 5% (5%, x1.0), FL 5% (3%, x1.5), NY 4% (4%, x0.8), NC 3% (2%, x1.4), PA 3% (3%, x1.2) |
| 400m | f | TX 10% (7%, x1.4), CA 9% (11%, x0.8), NJ 5% (3%, x1.8), OH 5% (5%, x0.9), PA 4% (3%, x1.4), FL 4% (3%, x1.3), NY 4% (5%, x0.8), GA 4% (3%, x1.2) |
| 800m | m | CA 11% (13%, x0.8), TX 7% (6%, x1.3), OH 5% (5%, x1.1), IL 5% (5%, x1.1), PA 4% (3%, x1.3), MI 4% (5%, x0.7), WA 4% (3%, x1.1), NY 3% (4%, x0.8) |
| 800m | f | CA 11% (12%, x0.9), TX 7% (6%, x1.1), OH 5% (5%, x1.0), NY 5% (5%, x0.9), IL 4% (4%, x1.0), PA 4% (3%, x1.3), MI 4% (4%, x0.8), MN 3% (4%, x0.9) |
| 1600m | m | CA 13% (14%, x0.9), OR 6% (2%, x3.1), WA 6% (4%, x1.5), CO 6% (2%, x3.2), OH 5% (5%, x1.0), NC 4% (3%, x1.7), IL 4% (5%, x0.9), UT 4% (1%, x2.8) |
| 1500m | f | CA 13% (14%, x1.0), PA 6% (3%, x1.7), NJ 5% (3%, x2.0), NY 5% (4%, x1.2), FL 4% (3%, x1.3), NC 4% (2%, x1.8), TX 4% (7%, x0.6), OH 4% (5%, x0.9) |

## Cross-event checks

- **Exceedance counts** span 349 to 27,876 (a factor of 79.9).
  A tail estimated from a few dozen athletes is far noisier than one estimated from several hundred, so these return periods are not equally trustworthy even where each fit passes its own diagnostics. Compare the sparsest event's confidence interval against the densest before reading anything into a difference between them.
- **No selection method converged** for: 200m m, 400m m, 1600m m, 1500m f. Those thresholds are fallbacks, not selections, and the fits resting on them describe this dataset rather than estimating a tail.
- **The shape parameter never stabilises** for: 200m m, 400m m, 400m f, 800m m, 800m f, 1600m m, 1500m f. xi drifts monotonically across the entire candidate grid, which means the Pickands-Balkema-de Haan limit is not reached anywhere in it -- there is no threshold at which the GPD is the right shape, so no choice of threshold rescues these fits. Widening the grid does not help; the drift continues in both directions.
- **The return period of the fastest mark is NOT identified** for: 100m m (1 in 416,653,490), 100m f (1 in 201,359,964), 200m m (1 in 5,776,362,325), 200m f (1 in 4,884,633), 400m m (1 in 10,968,781), 800m m (1 in 182,644), 800m f (1 in 674,735,039), 1600m m (1 in 182,139), 1500m f (1 in 147,173). Those marks sit closer to the fitted wall than the wall's own confidence interval is wide, so with xi < 0 the survival probability is collapsing toward zero and the number is reporting where the endpoint landed rather than how rare the performance is. Do not compare these across events -- that comparison is the goal of the project, and these particular numbers cannot serve it. Score a slightly slower benchmark instead, where the fit is still supported by data.
- **Implied walls sit close to the fastest athlete** for: 100m m (+0.04 s), 100m f (+0.03 s), 200m m (+0.04 s), 200m f (+0.13 s), 400m m (+0.23 s), 800m f (+0.10 s) -- expected, not alarming. With a bounded tail the sample maximum converges to the endpoint as n grows, and these pools have tens of thousands of athletes. The wall is still the most fragile number the model produces; read the `wall_ci_*` columns, not the point estimate.

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
