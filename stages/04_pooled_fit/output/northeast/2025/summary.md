# Pooled 2025 northeast -- GPD tail fits

One row per event x sex. Times in seconds; `rp_of_fastest` is the return period of that pool's own fastest mark, read as "one athlete-season in this many".

## Fits

| event | sex | n | u_sec | N_u | xi | xi_ci_lo | xi_ci_hi | sigma | implied_wall_s | fastest_s | wall_margin_s | rp_of_fastest | rp_identified | wall_ci_lo | wall_ci_hi | plateau | converged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100m | m | 26758 | 11.64 | 3147 | -0.2952 | -0.3176 | -0.2709 | 0.415 | 10.23 | 10.34 | 0.106 | 54015 | False | 10.153 | 10.3 | sliding xi -- no plateau | False |
| 100m | f | 23394 | 13.69 | 4142 | -0.2601 | -0.2942 | -0.2429 | 0.6636 | 11.14 | 11.25 | 0.112 | 948177 | False | 11.007 | 11.381 | sliding xi -- no plateau | True |
| 200m | m | 23554 | 22.36 | 384 | -0.2496 | -0.3291 | -0.1838 | 0.4616 | 20.51 | 20.93 | 0.42 | 23403 | False | 20.053 | 20.868 | sliding xi -- no plateau | True |
| 200m | f | 21806 | 25.79 | 356 | -0.1451 | -0.2468 | -0.0655 | 0.658 | 21.26 | 23.05 | 1.793 | 36468 | False | 16.248 | 22.801 | sliding xi -- no plateau | True |
| 400m | m | 17255 | 52.62 | 1867 | -0.304 | -0.3611 | -0.2819 | 2.0526 | 45.87 | 46.08 | 0.213 | 802882 | False | 45.548 | 46.654 | sliding xi -- no plateau | False |
| 400m | f | 13264 | 59.05 | 371 | -0.1719 | -0.3121 | -0.1075 | 1.7717 | 48.74 | 51.14 | 2.401 | 171599 | False | 43.21 | 52.586 | sliding xi -- no plateau | True |
| 800m | m | 15701 | 2:00.19 | 799 | -0.2547 | -0.3076 | -0.2043 | 3.4347 | 1:46.70 | 1:49.24 | 2.535 | 13892 | False | 104.297 | 108.389 | sliding xi -- no plateau | True |
| 800m | f | 13210 | 2:22.72 | 673 | -0.184 | -0.2633 | -0.1308 | 5.3771 | 1:53.50 | 2:00.11 | 6.605 | 63309 | False | 103.441 | 121.583 | sliding xi -- no plateau | True |
| 1600m | m | 14500 | 4:44.00 | 2235 | -0.3363 | -0.4176 | -0.3192 | 14.6334 | 4:00.49 | 4:01.54 | 1.05 | 417645 | False | 239.189 | 246.709 | sliding xi -- no plateau | False |
| 1500m | f | 10019 | 4:42.81 | 166 | -0.1009 | -0.2565 | 0.0008 | 6.5526 | 3:37.84 | 4:14.95 | 37.105 | 15565 | False | unbounded | 253.039 | sliding xi -- no plateau | True |

## Query times

| event | sex | time | P(this fast or faster) | 1 in | 95% CI on 1 in |
|---|---|---|---|---|---|
| 100m | m | 10.34 | 1.851e-05 | 54,015 **at the wall** | 16,443 - 513,555 |
| 100m | m | 10.38 | 5.475e-05 | 18,264 **at the wall** | 7,999 - 66,470 |
| 100m | m | 10.55 | 7.486e-04 | 1,336 | 1,027 - 1,834 |
| 100m | m | 10.76 | 4.206e-03 | 238 | 213 - 272 |
| 100m | f | 11.25 | 1.055e-06 | 948,177 **at the wall** | unstable |
| 100m | f | 11.53 | 1.316e-04 | 7,596 | 4,403 - 59,196 |
| 100m | f | 11.88 | 1.533e-03 | 652 | 525 - 1,019 |
| 100m | f | 12.17 | 5.453e-03 | 183 | 162 - 218 |
| 200m | m | 20.93 | 4.273e-05 | 23,403 **at the wall** | 10,083 - 484,441 |
| 200m | m | 21.14 | 2.172e-04 | 4,604 **at the wall** | 2,907 - 11,175 |
| 200m | m | 21.46 | 1.127e-03 | 887 | 702 - 1,250 |
| 200m | m | 21.84 | 4.343e-03 | 230 | 197 - 276 |
| 200m | f | 23.05 | 2.742e-05 | 36,468 **at the wall** | 12,816 - 2,220,869 |
| 200m | f | 23.63 | 1.890e-04 | 5,290 **at the wall** | 3,203 - 16,148 |
| 200m | f | 24.33 | 1.122e-03 | 892 **at the wall** | 685 - 1,234 |
| 200m | f | 25.04 | 4.696e-03 | 213 **at the wall** | 181 - 253 |
| 400m | m | 46.08 | 1.246e-06 | 802,882 **at the wall** | unstable |
| 400m | m | 46.98 | 2.872e-04 | 3,482 | 2,220 - 32,849 |
| 400m | m | 47.68 | 1.430e-03 | 699 | 554 - 1,324 |
| 400m | m | 48.85 | 7.359e-03 | 136 | 121 - 159 |
| 400m | f | 51.14 | 5.828e-06 | 171,599 **at the wall** | unstable |
| 400m | f | 53.70 | 3.974e-04 | 2,516 **at the wall** | 1,465 - 13,779 |
| 400m | f | 55.41 | 2.226e-03 | 449 **at the wall** | 351 - 652 |
| 400m | f | 56.84 | 6.890e-03 | 145 **at the wall** | 125 - 173 |
| 800m | m | 1:49.24 | 7.198e-05 | 13,892 **at the wall** | 5,684 - 142,272 |
| 800m | m | 1:50.07 | 2.188e-04 | 4,570 **at the wall** | 2,552 - 13,819 |
| 800m | m | 1:52.02 | 1.317e-03 | 760 | 591 - 1,118 |
| 800m | m | 1:54.71 | 6.572e-03 | 152 | 131 - 181 |
| 800m | f | 2:00.11 | 1.580e-05 | 63,309 **at the wall** | unstable |
| 800m | f | 2:05.96 | 4.957e-04 | 2,017 **at the wall** | 1,243 - 7,601 |
| 800m | f | 2:09.51 | 1.936e-03 | 516 **at the wall** | 401 - 819 |
| 800m | f | 2:14.12 | 7.661e-03 | 131 | 113 - 155 |
| 1600m | m | 4:01.54 | 2.394e-06 | 417,645 **at the wall** | unstable |
| 1600m | m | 4:07.81 | 7.696e-04 | 1,299 **at the wall** | 960 - 22,445 |
| 1600m | m | 4:12.04 | 2.985e-03 | 335 | 283 - 691 |
| 1600m | m | 4:16.70 | 8.182e-03 | 122 | 109 - 154 |
| 1500m | f | 4:14.95 | 6.425e-05 | 15,565 **at the wall** | 5,774 - 2,551,198 |
| 1500m | f | 4:22.06 | 3.659e-04 | 2,733 **at the wall** | 1,580 - 8,754 |
| 1500m | f | 4:32.28 | 2.872e-03 | 348 **at the wall** | 259 - 478 |
| 1500m | f | 4:39.29 | 9.536e-03 | 105 **at the wall** | 88 - 127 |

## Denominator sensitivity

The slow-side log-IQR fence removes rows from `n`, and every return period scales with `n` through zeta = N_u/n. `rp_sensitivity` is the factor by which the unfenced pool would change them.

| event | sex | n before fence | n after | factor |
|---|---|---|---|---|
| 100m | m | 27,051 | 26,758 | x1.0109 |
| 100m | f | 23,510 | 23,394 | x1.0050 |
| 200m | m | 23,790 | 23,554 | x1.0100 |
| 200m | f | 21,924 | 21,806 | x1.0054 |
| 400m | m | 17,407 | 17,255 | x1.0088 |
| 400m | f | 13,350 | 13,264 | x1.0065 |
| 800m | m | 15,750 | 15,701 | x1.0031 |
| 800m | f | 13,244 | 13,210 | x1.0026 |
| 1600m | m | 14,536 | 14,500 | x1.0025 |
| 1500m | f | 10,048 | 10,019 | x1.0029 |

## Who is in the tail

Each state's share of the exceedances (the athletes faster than u, which are what the GPD is fitted to) against its share of the pool. Ratio > 1 means over-represented among the fast. A pool is a mixture, and this is whose tail it really is. Top 8 per pool.

| event | sex | state: tail share (pool share, ratio) |
|---|---|---|
| 100m | m | PA 27% (17%, x1.6), NY 23% (30%, x0.8), NJ 20% (14%, x1.4), MA 13% (17%, x0.8), CT 10% (11%, x0.9), NH 2% (3%, x0.8), ME 2% (5%, x0.4), RI 1% (1%, x1.1) |
| 100m | f | NY 26% (30%, x0.9), PA 25% (17%, x1.5), NJ 19% (13%, x1.5), MA 12% (18%, x0.7), CT 10% (11%, x0.9), ME 2% (4%, x0.5), NH 2% (3%, x0.8), VT 1% (2%, x0.7) |
| 200m | m | PA 30% (17%, x1.7), NY 23% (32%, x0.7), NJ 21% (14%, x1.5), MA 12% (14%, x0.8), CT 7% (11%, x0.6), NH 3% (3%, x1.1), ME 2% (4%, x0.4), RI 1% (2%, x0.7) |
| 200m | f | PA 29% (17%, x1.8), NY 25% (32%, x0.8), NJ 24% (14%, x1.8), MA 8% (16%, x0.5), CT 7% (11%, x0.6), NH 2% (3%, x0.8), RI 2% (1%, x1.6), VT 1% (2%, x0.6) |
| 400m | m | NY 26% (33%, x0.8), PA 24% (19%, x1.3), NJ 23% (16%, x1.4), MA 12% (13%, x0.9), CT 9% (10%, x0.9), NH 3% (3%, x1.0), RI 2% (1%, x1.4), ME 1% (3%, x0.4) |
| 400m | f | PA 27% (19%, x1.4), NY 26% (33%, x0.8), NJ 25% (16%, x1.6), MA 8% (13%, x0.6), CT 8% (10%, x0.8), NH 2% (2%, x1.0), RI 2% (1%, x1.5), VT 1% (2%, x0.4) |
| 800m | m | PA 25% (21%, x1.2), NY 24% (31%, x0.8), NJ 22% (15%, x1.4), MA 12% (14%, x0.9), CT 9% (9%, x1.0), NH 3% (3%, x1.0), ME 2% (4%, x0.5), RI 2% (1%, x1.4) |
| 800m | f | NY 25% (32%, x0.8), PA 23% (19%, x1.2), NJ 22% (15%, x1.5), MA 15% (15%, x1.0), CT 6% (9%, x0.6), RI 2% (1%, x1.9), NH 2% (3%, x0.8), ME 2% (4%, x0.6) |
| 1600m | m | NY 25% (29%, x0.9), PA 24% (20%, x1.2), NJ 20% (18%, x1.1), MA 15% (14%, x1.0), CT 7% (8%, x0.9), NH 3% (3%, x0.9), ME 2% (4%, x0.6), RI 2% (2%, x1.2) |
| 1500m | f | NY 29% (29%, x1.0), PA 23% (22%, x1.0), NJ 19% (18%, x1.1), MA 14% (13%, x1.1), CT 4% (8%, x0.5), ME 4% (3%, x1.1), RI 3% (2%, x1.9), NH 2% (2%, x1.0) |

## Cross-event checks

- **Exceedance counts** span 166 to 4,142 (a factor of 25.0).
  A tail estimated from a few dozen athletes is far noisier than one estimated from several hundred, so these return periods are not equally trustworthy even where each fit passes its own diagnostics. Compare the sparsest event's confidence interval against the densest before reading anything into a difference between them.
- **No selection method converged** for: 100m m, 400m m, 1600m m. Those thresholds are fallbacks, not selections, and the fits resting on them describe this dataset rather than estimating a tail.
- **The shape parameter never stabilises** for: 100m m, 100m f, 200m m, 200m f, 400m m, 400m f, 800m m, 800m f, 1600m m, 1500m f. xi drifts monotonically across the entire candidate grid, which means the Pickands-Balkema-de Haan limit is not reached anywhere in it -- there is no threshold at which the GPD is the right shape, so no choice of threshold rescues these fits. Widening the grid does not help; the drift continues in both directions.
- **The return period of the fastest mark is NOT identified** for: 100m m (1 in 54,015), 100m f (1 in 948,177), 200m m (1 in 23,403), 200m f (1 in 36,468), 400m m (1 in 802,882), 400m f (1 in 171,599), 800m m (1 in 13,892), 800m f (1 in 63,309), 1600m m (1 in 417,645), 1500m f (1 in 15,565). Those marks sit closer to the fitted wall than the wall's own confidence interval is wide, so with xi < 0 the survival probability is collapsing toward zero and the number is reporting where the endpoint landed rather than how rare the performance is. Do not compare these across events -- that comparison is the goal of the project, and these particular numbers cannot serve it. Score a slightly slower benchmark instead, where the fit is still supported by data.
- **Implied walls sit close to the fastest athlete** for: 100m m (+0.11 s), 100m f (+0.11 s), 200m m (+0.42 s), 400m m (+0.21 s) -- expected, not alarming. With a bounded tail the sample maximum converges to the endpoint as n grows, and these pools have tens of thousands of athletes. The wall is still the most fragile number the model produces; read the `wall_ci_*` columns, not the point estimate.
- **No finite fast end to the wall interval** for: 1500m f (4% of resamples). That share of bootstrap resamples had xi >= 0 or a wall at or below 0 s, i.e. no wall at all, so the data cannot rule out an unbounded tail. Read the point wall as meaningless here.
