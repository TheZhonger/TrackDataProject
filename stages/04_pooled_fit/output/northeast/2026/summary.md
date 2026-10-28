# Pooled 2026 northeast -- GPD tail fits

One row per event x sex. Times in seconds; `rp_of_fastest` is the return period of that pool's own fastest mark, read as "one athlete-season in this many".

## Fits

| event | sex | n | u_sec | N_u | xi | xi_ci_lo | xi_ci_hi | sigma | implied_wall_s | fastest_s | wall_margin_s | rp_of_fastest | rp_identified | wall_ci_lo | wall_ci_hi | plateau | converged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100m | m | 28686 | 11.91 | 5664 | -0.3475 | -0.3641 | -0.3323 | 0.5343 | 10.37 | 10.44 | 0.068 | 40722 | False | 10.332 | 10.413 | xi flat at -0.334 | True |
| 100m | f | 25101 | 13.76 | 4669 | -0.2803 | -0.3237 | -0.2664 | 0.7145 | 11.21 | 11.27 | 0.059 | 3721176 | False | 11.121 | 11.467 | sliding xi -- no plateau | False |
| 200m | m | 26179 | 24.04 | 4309 | -0.3153 | -0.3525 | -0.3017 | 1.0479 | 20.72 | 20.77 | 0.054 | 2933155 | False | 20.62 | 20.941 | sliding xi -- no plateau | False |
| 200m | f | 23393 | 26.45 | 922 | -0.1984 | -0.2613 | -0.1581 | 0.8347 | 22.24 | 23.03 | 0.787 | 118149 | False | 21.252 | 23.104 | sliding xi -- no plateau | True |
| 400m | m | 18625 | 51.32 | 948 | -0.2501 | -0.3051 | -0.2074 | 1.4491 | 45.52 | 46.34 | 0.817 | 49425 | False | 44.697 | 46.373 | sliding xi -- no plateau | True |
| 400m | f | 14810 | 1:00.86 | 1091 | -0.2366 | -0.2987 | -0.1994 | 2.3091 | 51.10 | 52.14 | 1.039 | 175184 | False | 49.785 | 52.68 | sliding xi -- no plateau | True |
| 800m | m | 16877 | 1:59.49 | 665 | -0.1981 | -0.2623 | -0.1294 | 2.9068 | 1:44.82 | 1:49.11 | 4.292 | 12559 | False | 98.904 | 107.731 | sliding xi -- no plateau | True |
| 800m | f | 14027 | 2:16.84 | 232 | -0.0945 | -0.244 | -0.0038 | 3.2935 | 1:41.99 | 2:01.84 | 19.852 | 23337 | False | unbounded | 121.799 | sliding xi -- no plateau | True |
| 1600m | m | 15482 | 4:25.65 | 433 | -0.2046 | -0.3979 | -0.1473 | 6.7547 | 3:52.62 | 3:57.50 | 4.875 | 412023 | False | 222.054 | 246.224 | sliding xi -- no plateau | True |
| 1500m | f | 10467 | 4:42.04 | 173 | -0.1298 | -0.3427 | -0.0249 | 7.1322 | 3:47.11 | 4:11.00 | 23.89 | 36927 | False | unbounded | 257.887 | sliding xi -- no plateau | True |

## Query times

| event | sex | time | P(this fast or faster) | 1 in | 95% CI on 1 in |
|---|---|---|---|---|---|
| 100m | m | 10.44 | 2.456e-05 | 40,722 **at the wall** | 14,843 - 347,401 |
| 100m | m | 10.47 | 7.068e-05 | 14,147 | 7,177 - 44,156 |
| 100m | m | 10.61 | 9.151e-04 | 1,093 | 870 - 1,414 |
| 100m | m | 10.76 | 3.742e-03 | 267 | 238 - 302 |
| 100m | f | 11.27 | 2.687e-07 | 3,721,176 **at the wall** | unstable |
| 100m | f | 11.59 | 2.070e-04 | 4,831 | 3,300 - 45,294 |
| 100m | f | 11.92 | 1.935e-03 | 517 | 444 - 882 |
| 100m | f | 12.18 | 5.900e-03 | 169 | 155 - 211 |
| 200m | m | 20.77 | 3.409e-07 | 2,933,155 **at the wall** | unstable |
| 200m | m | 21.07 | 1.350e-04 | 7,408 | 4,781 - 59,081 |
| 200m | m | 21.42 | 1.197e-03 | 836 | 702 - 1,329 |
| 200m | m | 21.85 | 5.430e-03 | 184 | 169 - 212 |
| 200m | f | 23.03 | 8.464e-06 | 118,149 **at the wall** | unstable |
| 200m | f | 23.70 | 1.885e-04 | 5,304 **at the wall** | 3,092 - 18,890 |
| 200m | f | 24.33 | 1.153e-03 | 867 | 672 - 1,286 |
| 200m | f | 24.93 | 4.120e-03 | 243 | 208 - 286 |
| 400m | m | 46.34 | 2.023e-05 | 49,425 **at the wall** | unstable |
| 400m | m | 47.10 | 2.803e-04 | 3,567 **at the wall** | 2,195 - 11,334 |
| 400m | m | 47.77 | 1.154e-03 | 866 | 674 - 1,319 |
| 400m | m | 48.88 | 5.746e-03 | 174 | 153 - 207 |
| 400m | f | 52.14 | 5.708e-06 | 175,184 **at the wall** | unstable |
| 400m | f | 53.96 | 4.111e-04 | 2,432 **at the wall** | 1,589 - 8,296 |
| 400m | f | 54.97 | 1.476e-03 | 677 | 526 - 1,135 |
| 400m | f | 56.81 | 7.642e-03 | 131 | 115 - 153 |
| 800m | m | 1:49.11 | 7.962e-05 | 12,559 **at the wall** | 5,580 - 62,649 |
| 800m | m | 1:50.30 | 2.738e-04 | 3,652 **at the wall** | 2,249 - 8,470 |
| 800m | m | 1:52.26 | 1.281e-03 | 781 **at the wall** | 611 - 1,128 |
| 800m | m | 1:54.77 | 5.554e-03 | 180 | 155 - 217 |
| 800m | f | 2:01.84 | 4.285e-05 | 23,337 **at the wall** | 8,301 - 88,038,730 |
| 800m | f | 2:06.04 | 3.266e-04 | 3,062 **at the wall** | 1,867 - 11,562 |
| 800m | f | 2:09.70 | 1.462e-03 | 684 **at the wall** | 510 - 1,060 |
| 800m | f | 2:14.13 | 7.022e-03 | 142 **at the wall** | 122 - 169 |
| 1600m | m | 3:57.50 | 2.427e-06 | 412,023 **at the wall** | unstable |
| 1600m | m | 4:08.23 | 7.167e-04 | 1,395 **at the wall** | 967 - 7,824 |
| 1600m | m | 4:11.17 | 1.667e-03 | 600 **at the wall** | 465 - 1,143 |
| 1600m | m | 4:17.36 | 6.812e-03 | 147 | 126 - 173 |
| 1500m | f | 4:11.00 | 2.708e-05 | 36,927 **at the wall** | unstable |
| 1500m | f | 4:21.66 | 4.646e-04 | 2,153 **at the wall** | 1,277 - 12,547 |
| 1500m | f | 4:29.88 | 2.405e-03 | 416 **at the wall** | 311 - 624 |
| 1500m | f | 4:37.77 | 8.858e-03 | 113 **at the wall** | 95 - 137 |

## Denominator sensitivity

The slow-side log-IQR fence removes rows from `n`, and every return period scales with `n` through zeta = N_u/n. `rp_sensitivity` is the factor by which the unfenced pool would change them.

| event | sex | n before fence | n after | factor |
|---|---|---|---|---|
| 100m | m | 29,013 | 28,686 | x1.0114 |
| 100m | f | 25,205 | 25,101 | x1.0041 |
| 200m | m | 26,414 | 26,179 | x1.0090 |
| 200m | f | 23,516 | 23,393 | x1.0053 |
| 400m | m | 18,769 | 18,625 | x1.0077 |
| 400m | f | 14,900 | 14,810 | x1.0061 |
| 800m | m | 16,959 | 16,877 | x1.0049 |
| 800m | f | 14,074 | 14,027 | x1.0034 |
| 1600m | m | 15,543 | 15,482 | x1.0039 |
| 1500m | f | 10,508 | 10,467 | x1.0039 |

## Cross-event checks

- **Exceedance counts** span 173 to 5,664 (a factor of 32.7).
  A tail estimated from a few dozen athletes is far noisier than one estimated from several hundred, so these return periods are not equally trustworthy even where each fit passes its own diagnostics. Compare the sparsest event's confidence interval against the densest before reading anything into a difference between them.
- **No selection method converged** for: 100m f, 200m m. Those thresholds are fallbacks, not selections, and the fits resting on them describe this dataset rather than estimating a tail.
- **The shape parameter never stabilises** for: 100m f, 200m m, 200m f, 400m m, 400m f, 800m m, 800m f, 1600m m, 1500m f. xi drifts monotonically across the entire candidate grid, which means the Pickands-Balkema-de Haan limit is not reached anywhere in it -- there is no threshold at which the GPD is the right shape, so no choice of threshold rescues these fits. Widening the grid does not help; the drift continues in both directions.
- **The return period of the fastest mark is NOT identified** for: 100m m (1 in 40,722), 100m f (1 in 3,721,176), 200m m (1 in 2,933,155), 200m f (1 in 118,149), 400m m (1 in 49,425), 400m f (1 in 175,184), 800m m (1 in 12,559), 800m f (1 in 23,337), 1600m m (1 in 412,023), 1500m f (1 in 36,927). Those marks sit closer to the fitted wall than the wall's own confidence interval is wide, so with xi < 0 the survival probability is collapsing toward zero and the number is reporting where the endpoint landed rather than how rare the performance is. Do not compare these across events -- that comparison is the goal of the project, and these particular numbers cannot serve it. Score a slightly slower benchmark instead, where the fit is still supported by data.
- **Implied walls sit close to the fastest athlete** for: 100m m (+0.07 s), 100m f (+0.06 s), 200m m (+0.05 s), 200m f (+0.79 s), 400m m (+0.82 s) -- expected, not alarming. With a bounded tail the sample maximum converges to the endpoint as n grows, and these pools have tens of thousands of athletes. The wall is still the most fragile number the model produces; read the `wall_ci_*` columns, not the point estimate.
- **No finite fast end to the wall interval** for: 800m f (5% of resamples), 1500m f (2% of resamples). That share of bootstrap resamples had xi >= 0 or a wall at or below 0 s, i.e. no wall at all, so the data cannot rule out an unbounded tail. Read the point wall as meaningless here.
