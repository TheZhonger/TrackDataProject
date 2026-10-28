# Pooled 2025-2026 northeast -- GPD tail fits

One row per event x sex. Times in seconds; `rp_of_fastest` is the return period of that pool's own fastest mark, read as "one athlete-season in this many".

**Stacked seasons.** `n` counts athlete-seasons, so return periods are in the same unit as a single-season fit. Many athletes appear in both seasons, and their two marks are not independent, so the bootstrap resamples whole athletes; the intervals below are cluster-bootstrap intervals. The threshold selectors' goodness-of-fit p-values still treat rows as independent and are somewhat optimistic.

| event | sex | athlete-seasons | distinct athletes | in both seasons |
|---|---|---|---|---|
| 100m | m | 55,444 | 45,886 | 9,558 |
| 100m | f | 48,494 | 40,133 | 8,361 |
| 200m | m | 49,726 | 41,496 | 8,230 |
| 200m | f | 45,200 | 37,414 | 7,786 |
| 400m | m | 35,881 | 30,264 | 5,617 |
| 400m | f | 28,075 | 23,419 | 4,656 |
| 800m | m | 32,580 | 26,155 | 6,425 |
| 800m | f | 27,243 | 21,613 | 5,630 |
| 1600m | m | 29,985 | 23,099 | 6,886 |
| 1500m | f | 20,485 | 15,793 | 4,692 |

## Fits

| event | sex | n | u_sec | N_u | xi | xi_ci_lo | xi_ci_hi | sigma | implied_wall_s | fastest_s | wall_margin_s | rp_of_fastest | rp_identified | wall_ci_lo | wall_ci_hi | plateau | converged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100m | m | 55444 | 11.73 | 7809 | -0.3137 | -0.3258 | -0.2999 | 0.4535 | 10.28 | 10.34 | 0.056 | 228778 | False | 10.244 | 10.329 | sliding xi -- no plateau | False |
| 100m | f | 48494 | 13.70 | 8548 | -0.2682 | -0.2878 | -0.2556 | 0.6774 | 11.17 | 11.25 | 0.076 | 2700302 | False | 11.085 | 11.296 | sliding xi -- no plateau | True |
| 200m | m | 49726 | 23.66 | 5913 | -0.3024 | -0.3256 | -0.2873 | 0.8927 | 20.71 | 20.77 | 0.062 | 3012962 | False | 20.626 | 20.859 | sliding xi -- no plateau | False |
| 200m | f | 45200 | 25.78 | 740 | -0.1664 | -0.2526 | -0.0978 | 0.6717 | 21.74 | 23.03 | 1.286 | 58914 | False | 19.356 | 22.877 | sliding xi -- no plateau | True |
| 400m | m | 35881 | 51.88 | 2640 | -0.2776 | -0.3128 | -0.2506 | 1.7026 | 45.75 | 46.08 | 0.334 | 487154 | False | 45.285 | 46.212 | sliding xi -- no plateau | False |
| 400m | f | 28075 | 1:00.08 | 1424 | -0.1924 | -0.2739 | -0.1484 | 1.9988 | 49.69 | 51.14 | 1.448 | 552438 | False | 47.082 | 52.112 | sliding xi -- no plateau | True |
| 800m | m | 32580 | 1:59.44 | 1283 | -0.234 | -0.2824 | -0.1894 | 3.1072 | 1:46.16 | 1:49.11 | 2.951 | 15735 | False | 104.031 | 107.767 | sliding xi -- no plateau | True |
| 800m | f | 27243 | 2:17.00 | 449 | -0.1182 | -0.2222 | -0.0352 | 3.6595 | 1:46.03 | 2:00.11 | 14.075 | 47837 | False | 39.546 | 119.382 | sliding xi -- no plateau | True |
| 1600m | m | 29985 | 4:41.60 | 3934 | -0.2876 | -0.377 | -0.2755 | 12.8576 | 3:56.90 | 3:57.50 | 0.605 | 23915423 | False | 235.656 | 244.721 | sliding xi -- no plateau | False |
| 1500m | f | 20485 | 5:15.35 | 3626 | -0.3005 | -0.3597 | -0.284 | 19.6945 | 4:09.82 | 4:11.00 | 1.179 | 3616896 | False | 247.335 | 258.072 | sliding xi -- no plateau | True |

## Query times

| event | sex | time | P(this fast or faster) | 1 in | 95% CI on 1 in |
|---|---|---|---|---|---|
| 100m | m | 10.34 | 4.371e-06 | 228,778 **at the wall** | 65,801 - 14,912,563 |
| 100m | m | 10.38 | 2.454e-05 | 40,754 | 19,875 - 172,082 |
| 100m | m | 10.51 | 3.781e-04 | 2,645 | 2,051 - 3,837 |
| 100m | m | 10.66 | 1.919e-03 | 521 | 461 - 603 |
| 100m | f | 11.25 | 3.703e-07 | 2,700,302 **at the wall** | unstable |
| 100m | f | 11.32 | 4.245e-06 | 235,579 **at the wall** | 67,826 - 40,723,396 |
| 100m | f | 11.75 | 7.112e-04 | 1,406 | 1,128 - 2,149 |
| 100m | f | 12.04 | 3.255e-03 | 307 | 276 - 370 |
| 200m | m | 20.77 | 3.319e-07 | 3,012,962 **at the wall** | unstable |
| 200m | m | 21.02 | 7.031e-05 | 14,223 | 9,291 - 61,429 |
| 200m | m | 21.23 | 3.860e-04 | 2,590 | 2,081 - 4,456 |
| 200m | m | 21.62 | 2.445e-03 | 409 | 370 - 491 |
| 200m | f | 23.03 | 1.697e-05 | 58,914 **at the wall** | 19,001 - 8,264,733 |
| 200m | f | 23.46 | 9.603e-05 | 10,413 **at the wall** | 5,676 - 52,302 |
| 200m | f | 24.05 | 5.669e-04 | 1,764 **at the wall** | 1,348 - 2,763 |
| 200m | f | 24.64 | 2.228e-03 | 449 **at the wall** | 381 - 555 |
| 400m | m | 46.08 | 2.053e-06 | 487,154 **at the wall** | unstable |
| 400m | m | 46.60 | 6.047e-05 | 16,536 **at the wall** | 8,337 - 74,587 |
| 400m | m | 47.41 | 6.689e-04 | 1,495 | 1,180 - 2,115 |
| 400m | m | 48.36 | 3.405e-03 | 294 | 258 - 345 |
| 400m | f | 51.14 | 1.810e-06 | 552,438 **at the wall** | unstable |
| 400m | f | 53.56 | 2.988e-04 | 3,347 **at the wall** | 1,951 - 13,311 |
| 400m | f | 54.39 | 8.206e-04 | 1,219 **at the wall** | 873 - 2,397 |
| 400m | f | 55.98 | 3.733e-03 | 268 | 226 - 340 |
| 800m | m | 1:49.11 | 6.355e-05 | 15,735 **at the wall** | 7,572 - 57,085 |
| 800m | m | 1:49.94 | 1.833e-04 | 5,455 | 3,441 - 10,766 |
| 800m | m | 1:51.29 | 6.759e-04 | 1,479 | 1,133 - 2,122 |
| 800m | m | 1:53.37 | 2.895e-03 | 345 | 295 - 418 |
| 800m | f | 2:00.11 | 2.090e-05 | 47,837 **at the wall** | 12,562 - 40,577,851 |
| 800m | f | 2:03.61 | 1.368e-04 | 7,307 **at the wall** | 3,647 - 43,540 |
| 800m | f | 2:08.22 | 9.821e-04 | 1,018 **at the wall** | 747 - 1,621 |
| 800m | f | 2:12.06 | 3.791e-03 | 264 **at the wall** | 223 - 328 |
| 1600m | m | 3:57.50 | 4.181e-08 | 23,915,423 **at the wall** | unstable |
| 1600m | m | 4:05.30 | 3.928e-04 | 2,546 **at the wall** | 1,926 - 410,535 |
| 1600m | m | 4:09.87 | 1.778e-03 | 563 | 482 - 1,424 |
| 1600m | m | 4:13.60 | 4.279e-03 | 234 | 209 - 339 |
| 1500m | f | 4:11.00 | 2.765e-07 | 3,616,896 **at the wall** | unstable |
| 1500m | f | 4:19.29 | 2.837e-04 | 3,525 **at the wall** | 2,391 - 239,995 |
| 1500m | f | 4:27.52 | 2.272e-03 | 440 | 370 - 863 |
| 1500m | f | 4:35.06 | 7.401e-03 | 135 | 121 - 170 |

## Denominator sensitivity

The slow-side log-IQR fence removes rows from `n`, and every return period scales with `n` through zeta = N_u/n. `rp_sensitivity` is the factor by which the unfenced pool would change them.

| event | sex | n before fence | n after | factor |
|---|---|---|---|---|
| 100m | m | 56,064 | 55,444 | x1.0112 |
| 100m | f | 48,715 | 48,494 | x1.0046 |
| 200m | m | 50,204 | 49,726 | x1.0096 |
| 200m | f | 45,440 | 45,200 | x1.0053 |
| 400m | m | 36,176 | 35,881 | x1.0082 |
| 400m | f | 28,250 | 28,075 | x1.0062 |
| 800m | m | 32,709 | 32,580 | x1.0040 |
| 800m | f | 27,318 | 27,243 | x1.0028 |
| 1600m | m | 30,079 | 29,985 | x1.0031 |
| 1500m | f | 20,556 | 20,485 | x1.0035 |

## Who is in the tail

Each state's share of the exceedances (the athletes faster than u, which are what the GPD is fitted to) against its share of the pool. Ratio > 1 means over-represented among the fast. A pool is a mixture, and this is whose tail it really is. Top 8 per pool.

| event | sex | state: tail share (pool share, ratio) |
|---|---|---|
| 100m | m | PA 26% (18%, x1.4), NY 25% (28%, x0.9), NJ 20% (14%, x1.4), MA 13% (17%, x0.8), CT 10% (11%, x0.9), NH 2% (3%, x0.7), ME 2% (5%, x0.5), RI 2% (1%, x1.1) |
| 100m | f | NY 27% (29%, x0.9), PA 25% (18%, x1.4), NJ 18% (13%, x1.4), MA 12% (18%, x0.7), CT 10% (11%, x0.9), ME 2% (4%, x0.6), NH 2% (3%, x0.8), VT 1% (2%, x0.6) |
| 200m | m | PA 26% (18%, x1.4), NY 26% (31%, x0.8), NJ 21% (15%, x1.4), MA 12% (14%, x0.8), CT 9% (11%, x0.8), NH 2% (3%, x0.8), ME 2% (4%, x0.4), RI 1% (2%, x0.9) |
| 200m | f | PA 28% (17%, x1.6), NY 26% (31%, x0.8), NJ 24% (14%, x1.7), MA 10% (16%, x0.6), CT 7% (11%, x0.6), RI 2% (1%, x1.5), NH 2% (3%, x0.6), ME 1% (4%, x0.2) |
| 400m | m | NY 26% (32%, x0.8), PA 24% (19%, x1.3), NJ 24% (16%, x1.5), MA 11% (13%, x0.8), CT 9% (10%, x0.9), NH 2% (3%, x0.9), RI 2% (1%, x1.5), ME 1% (3%, x0.4) |
| 400m | f | NJ 27% (17%, x1.6), PA 26% (20%, x1.3), NY 24% (33%, x0.7), MA 9% (12%, x0.7), CT 7% (10%, x0.8), NH 3% (3%, x1.0), RI 1% (1%, x1.4), VT 1% (2%, x0.5) |
| 800m | m | PA 25% (21%, x1.2), NY 24% (30%, x0.8), NJ 23% (16%, x1.4), MA 12% (14%, x0.9), CT 8% (9%, x0.8), NH 2% (3%, x0.8), RI 2% (1%, x1.6), ME 2% (4%, x0.5) |
| 800m | f | PA 25% (20%, x1.2), NY 24% (31%, x0.8), NJ 24% (16%, x1.5), MA 13% (15%, x0.9), CT 5% (9%, x0.5), NH 3% (3%, x1.0), RI 3% (1%, x2.2), ME 2% (3%, x0.5) |
| 1600m | m | NY 25% (29%, x0.9), PA 25% (21%, x1.2), NJ 21% (18%, x1.2), MA 15% (14%, x1.0), CT 7% (8%, x0.9), NH 2% (3%, x0.8), RI 2% (2%, x1.3), VT 2% (2%, x0.9) |
| 1500m | f | NY 28% (29%, x1.0), PA 22% (22%, x1.0), NJ 19% (18%, x1.1), MA 13% (13%, x1.0), CT 7% (8%, x0.9), NH 3% (3%, x1.0), ME 2% (3%, x0.7), RI 2% (2%, x1.6) |

## Cross-event checks

- **Exceedance counts** span 449 to 8,548 (a factor of 19.0).
  A tail estimated from a few dozen athletes is far noisier than one estimated from several hundred, so these return periods are not equally trustworthy even where each fit passes its own diagnostics. Compare the sparsest event's confidence interval against the densest before reading anything into a difference between them.
- **No selection method converged** for: 100m m, 200m m, 400m m, 1600m m. Those thresholds are fallbacks, not selections, and the fits resting on them describe this dataset rather than estimating a tail.
- **The shape parameter never stabilises** for: 100m m, 100m f, 200m m, 200m f, 400m m, 400m f, 800m m, 800m f, 1600m m, 1500m f. xi drifts monotonically across the entire candidate grid, which means the Pickands-Balkema-de Haan limit is not reached anywhere in it -- there is no threshold at which the GPD is the right shape, so no choice of threshold rescues these fits. Widening the grid does not help; the drift continues in both directions.
- **The return period of the fastest mark is NOT identified** for: 100m m (1 in 228,778), 100m f (1 in 2,700,302), 200m m (1 in 3,012,962), 200m f (1 in 58,914), 400m m (1 in 487,154), 400m f (1 in 552,438), 800m m (1 in 15,735), 800m f (1 in 47,837), 1600m m (1 in 23,915,423), 1500m f (1 in 3,616,896). Those marks sit closer to the fitted wall than the wall's own confidence interval is wide, so with xi < 0 the survival probability is collapsing toward zero and the number is reporting where the endpoint landed rather than how rare the performance is. Do not compare these across events -- that comparison is the goal of the project, and these particular numbers cannot serve it. Score a slightly slower benchmark instead, where the fit is still supported by data.
- **Implied walls sit close to the fastest athlete** for: 100m m (+0.06 s), 100m f (+0.08 s), 200m m (+0.06 s), 400m m (+0.33 s), 1600m m (+0.60 s) -- expected, not alarming. With a bounded tail the sample maximum converges to the endpoint as n grows, and these pools have tens of thousands of athletes. The wall is still the most fragile number the model produces; read the `wall_ci_*` columns, not the point estimate.
