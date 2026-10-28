# Record test report: thresholds, bootstrap and next steps

Date: 2026-10-22. Reader: Daren. Style: ASD-STE100 (approximately 80%).

This report answers five questions:
- the possible next steps;
- why the test uses "the top 1%";
- the threshold for a Gompertz or Weibull tail;
- how the project uses the bootstrap;
- what KS, "audit" and ForwardStop mean.

**Sources of the numbers:**
- *The division test:* `record_calibration.md` section D and `record_division_summary.csv`.
- *All other tables:* exploratory runs, made on 2026-10-22 on the same division pools.
  These runs are **post-hoc**. I looked at many rules on the same 180 records, so the best
  result is optimistic. A new test must confirm it.

## 0. Summary

- The rule "Gompertz, top 1%" failed the division test (180 records the model did not see).
  Too many records were outside the 95% range on the "too rare" side.
- The test is always at the record. The "top 1%" is only the fit threshold.
- The threshold is a balance between bias and variance. Records are too heavy at the top
  10%, and too rare at the top 1% or higher.
- **The Gompertz at the top 5% passes at all ranks and in both directions.** This result
  is post-hoc, so it needs a new test.
- At the top 1% the parameter uncertainty is very large. The 95% range of the expected
  count is ×43, against ×8 at the top 5%.
- Recommended next step: write down "Gompertz, top 5%" (or a minimum N_u) now. Then test
  it on new records. A ForwardStop threshold for the Gompertz is the alternative.

## 1. Two terms

### 1.1 The KS test (Kolmogorov–Smirnov)

**What it tests.** KS compares a set of numbers with a stated distribution. Here the
distribution is "uniform between 0 and 1".

**Why uniform.** For each record we calculate p, the model's probability of a record this
fast or slower.
- If the model is correct, p is a random number between 0 and 1.
- All values are equally probable. So 180 correct p's spread evenly between 0 and 1.

**How it works.**
1. Sort the p's.
2. Plot each sorted p against its expected position (the diagonal on the QQ figures).
3. The statistic D is the largest vertical gap between the points and the diagonal.

**The KS p-value.** This is the probability of a gap as large as D if the model is correct.
- Below 0.05: the model is probably wrong.
- Above 0.05: we have no evidence against the model. That is not proof that the model
  is correct.
- The 95% limit is approximately D = 1.36/√n. For 180 records, a gap above 0.10 gives
  p < 0.05.

**A limit.** KS is most sensitive in the middle and weak at the two ends. The ends are
important for us. For this reason we also count the **tails**:
- p < 0.025: the model called the record too rare;
- p > 0.975: the model called the record too common (the tail is too heavy).

For 180 correct records, each count is between 1 and 9 (95% range, expected 4.5).

### 1.2 "Audit the extreme marks"

**What it means.** Each mark in a ranking list links to a result page on athletic.net.
The ranking list does not show these facts. The result page often shows them:
- **wind:** a sprint with a tailwind above +2.0 m/s is not a legal mark;
- **timing:** hand timing or fully automatic timing (FAT);
- **meet type:** a high-school meet, or an open or professional meet;
- **split:** a time inside a longer race, for example a 1600 m split inside a mile.

**Why it is important.** One wrong record can decide a record test. In the division test,
three records got z ≈ 0, which is the model's value for "almost impossible".

**The marks to audit:**

| mark | athlete | why it is suspect |
|---|---|---|
| 11.30, girls 100 m (RI, Apr 12) | Lisa Raye | 0.32 s faster than all of New England; z ≈ 0 |
| 9.82, boys 100 m (TX, 2025) | — | faster than the national record level |
| 3:57.28, boys 1600 m (IA, 2025) | — | national record level |
| 4:21.81, girls 1600 m (UT, Jun 05) | Jane Hedengren | probably a split in her 4:23.50 mile |
| 3:36.85, boys 1500 m (OR, Jun 15) | Josiah Tostenson | probably a professional meet; z ≈ 0 |
| 1:47.04, boys 800 m (TX, May 03) | Cooper Lutkenhaus | probably correct (a prodigy); z ≈ 0 |

**Cost.** About 100–200 pages if we also include the top 5 of each pool. This needs
credentials and your approval.

## 2. "Top 1%": the fit threshold and the test point

**Two different things.**
- The top 1% is where we **fit** the model. Only marks faster than the threshold u
  give data to the tail.
- We always **test** at the record, because the scores of the project are about the
  best marks.

**A test near u is almost automatic.**
- We count the fraction of marks above u: ζ = N_u / n. We do not model it.
- So the model agrees with the data at u by construction.
- A test near u can only show a small error. The difficult part is far from u, at the record.

**The difficulty increases with the distance from u.** Table 1 gives the KS p-value at
rank k. Rank 1 is the record, and rank k is the k-th best mark. Under a correct model,
n·S(t_k) follows a Gamma(k, 1) distribution. (Divisions, Gompertz, 180 marks per cell,
post-hoc.)

Table 1. KS p-value by rank (high = good)

| fit at top | k = 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 10% | 0.015 | 0.000 | 0.001 | 0.000 | 0.126 | 0.178 |
| 5% | **0.666** | 0.109 | 0.493 | 0.285 | 0.411 | 0.196 |
| 1% | 0.039 | 0.059 | 0.020 | 0.243 | 0.100 | 0.184 |
| 0.5% | 0.004 | 0.010 | 0.001 | 0.302 | 0.026 | 0.413 |

- At ranks 25 and 50 (near u), most rows pass.
- At ranks 1–5 (the records), only the top 5% passes.

**A threshold nearer the record makes the result worse.**
- At the top 0.5%, the smallest pool has 14 exceedances. At the top 0.1%, it has 10, and
  58 of the 180 pools cannot be fitted.
- With so little data, the fit is noisy. A noisy fit calls the records too rare: 16 low-tail
  records at 0.5%, and 25 of 122 at 0.1%.

## 3. A threshold for a Gompertz or Weibull tail

### 3.1 Theory

**The GPD.** The GPD has a limit theorem (Pickands–Balkema–de Haan). It says this: above
a sufficiently high u, the excesses follow a GPD. So for the GPD, "higher u" means
"more correct shape". The cost is less data.

**The Gompertz and Weibull.** These two models do not have such a theorem. They are
parametric assumptions about the shape of the tail. We selected them because they include
the ξ slide that the data shows (`pooled_method.md` §12). So no u is "correct" from theory.
The threshold is a **balance between bias and variance:**
- *Low u (for example the top 10%):* a lot of data, so the variance is low. But the body
  of the distribution has an effect on the fit, so the tail is too heavy (bias).
- *High u (for example the top 0.5%):* little data, so the variance is high. A noisy
  estimate, used as if it were exact, calls records too rare.

### 3.2 The threshold sweep (divisions, post-hoc)

Table 2. Record test by model and threshold (180 records)

| model | fit at top | min. N_u | record KS | fit 25→26 | fit 26→25 | tails low / high (1–9) | median z (0.69) |
|---|---|---|---|---|---|---|---|
| Gompertz | 10% | 273 | 0.015 | 0.016 | 0.129 | 1 / 15 | 0.92 |
| Gompertz | 5% | 137 | **0.666** | 0.118 | 0.462 | 3 / 9 | 0.73 |
| Gompertz | 2% | 55 | 0.292 | 0.981 | 0.023 | 11 / 6 | 0.58 |
| Gompertz | 1% | 28 | 0.039 | 0.863 | 0.005 | 13 / 7 | 0.54 |
| Gompertz | 0.5% | 14 | 0.004 | 0.171 | 0.001 | 16 / 6 | 0.50 |
| Weibull | 10% | 273 | 0.000 | 0.000 | 0.041 | 1 / 17 | 1.04 |
| Weibull | 5% | 137 | 0.014 | 0.010 | 0.618 | 2 / 12 | 0.84 |
| Weibull | 2% | 55 | 0.527 | 0.017 | 0.263 | 6 / 7 | 0.77 |
| Weibull | 1% | 28 | 0.825 | 0.273 | 0.102 | 10 / 7 | 0.65 |
| Weibull | 0.5% | 14 | 0.033 | 0.661 | 0.004 | 14 / 5 | 0.56 |

"Median z" is the median expected number of athletes at or faster than the record. A
correct model gives 0.69.

**What the sweep shows:**
- The pattern is monotone. When u goes up, the errors move from "too heavy" (high tail)
  to "too rare" (low tail). The median z goes down from approximately 1 to 0.5.
- The best Gompertz threshold is the top 5%. It passes the overall KS, both directions,
  and all ranks in Table 1. Its high tail (9) is at the limit of the 95% range.
- The best Weibull threshold is near the top 1–2%. The Weibull is heavier than the
  Gompertz, so it needs a higher u to stop the "too heavy" error. At 1% it has 10 low-tail
  records, just above the range.

### 3.3 Why part A selected 1%, and a better form of the rule

- Part A used 30 records from large pools: the northeast nine and the whole US.
- The top 1% of a large pool contains a lot of data. The top 1% of a small division
  contains only 28 marks.
- So a **percentage** rule does not transfer between pool sizes. The important number is
  N_u, the count of exceedances.
- At the top 5%, the smallest division has N_u = 137. A rule like "N_u ≥ 150" (or between
  150 and 300) is probably better than any fixed percentage. This is a hypothesis; a new
  test must confirm it.

## 4. ForwardStop

### 4.1 The problem it solves

We cannot select u by "best fit".
- Each u uses a different set of data.
- So a better fit at one u and a worse fit at another u are not comparable.
- If the model is correct at all u, "the best fit" selects a u at random.

### 4.2 The idea

ForwardStop (Bader, Yan & Zhang, 2018) changes the question.
- It does not ask "which u fits best".
- It asks "which low thresholds does the data reject".
- Then it selects the lowest threshold that the data does not reject. The lowest such u
  keeps the most data.

### 4.3 The procedure (as in `stages/03_tail_fit/threshold_select.py`)

1. Make a list of candidate thresholds, from low to high: u_1 < u_2 < … < u_m.
   `run_all.py` uses 18 thresholds, from the 80% to the 99.5% quantile.
2. At each u_i, fit the model to the exceedances.
3. Measure the misfit with the Anderson–Darling statistic A².
   - A² is a distance between the data and the fitted model, like KS.
   - A² gives more weight to the two ends than KS does.
4. Get a p-value p_i for each u_i with a **parametric bootstrap** (`gof_pvalue`):
   1. Simulate 199 fake data sets from the fitted model, each of the same size.
   2. Fit each fake set again, and calculate its A².
   3. p_i = (1 + the number of fake A² ≥ the real A²) / (1 + 199).
   - We cannot use a standard A² table. We estimated the parameters from the same data,
     and the bootstrap corrects for this.
5. Change each p-value into a score: y_i = −ln(1 − p_i).
   - A small p (a strong misfit) gives a small y.
   - A p near 1 gives a very large y.
6. Calculate the running mean: q_j = (y_1 + … + y_j) / j.
7. Find the last j at which q_j ≤ α (α = 0.05). Reject the thresholds u_1 … u_j as too low.
   - q_j stays below α only while all the thresholds up to j are clearly rejected.
   - One high p in the sequence increases q_j a lot, and ForwardStop stops there.
8. Select u_{j+1}.

**What it controls.** ForwardStop controls the false discovery rate at α. Of the
thresholds that it rejects, at most 5% (on average) are wrongly rejected.

### 4.4 ForwardStop for the Gompertz

- The procedure does not depend on the GPD. It needs only three things: a fit, a misfit
  statistic and a way to simulate from the fit.
- `tail_models.py` already has all three for the Gompertz: `fit_tail`, `sf_excess` (for A²)
  and `isf_excess` (for simulation).
- So a Gompertz version of `gof_pvalue` is a small change. Each pool then gets its own
  threshold from its own data.

**A known limit.** In very large pools, the test sees very small misfits and rejects
almost all thresholds. `pooled_method.md` §7 shows this for the GPD: many p-values were at
the bootstrap floor (1/200). Two corrections are possible:
- a cap on N_u (for example, a sub-sample of the pool for the test only);
- a check of the selected u against Table 2.

## 5. How the project uses the bootstrap

### 5.1 The idea

1. Make a new data set of the same size. Take marks at random from the real data, with
   replacement, so some marks appear twice and some do not appear.
2. Do the full fit again on the new data set.
3. Do this many times (for example 400).
4. The spread of the results shows how much the fit changes because of chance in the data.

A **parametric** bootstrap is different. It simulates new data from the fitted model, not
from the real data.

### 5.2 The uses

| where | what it resamples | number | what it gives |
|---|---|---|---|
| `gpd_tail.bootstrap` (stage 03) | athlete-seasons; it selects u again each time | 800 | CIs for ξ, σ, return periods, the wall |
| the same, in `run_all.py` / `gpd_pooled.py` | athlete-seasons | 400 | the CIs in each `summary.md` |
| the same, with `groups=athlete` | complete athletes (cluster), for stacked seasons | 400 | correct CIs when one athlete is in two seasons |
| `run_states.py` | athlete-seasons | — | ξ and wall CIs per state |
| `endpoint_interval` | (uses the draws above) | — | the wall CI; a draw with no wall counts as "no wall" |
| `threshold_select.gof_pvalue` | **parametric:** fake GPD data | 199 per u | A² p-values for ForwardStop |
| `weibull_fit.py` | athlete-seasons, u at the 90% quantile | 200 | CIs for Weibull θ and return periods |
| `model_compare.py`, `record_check.py` part A | the fit season | 50 | 95% predictive-interval coverage (bootstrap + Poisson) |
| `record_check.py` part D | — | 0 (not run) | — |

**Why "select u again each time".** The threshold depends on the data. If we keep u fixed,
the CIs ignore this uncertainty and are too narrow. This is a non-negotiable rule
(CLAUDE.md).

### 5.3 Exploratory use: the "predictive p"

**The problem.** The record test used one fitted model as if its parameters were exact.
This is the **plug-in** p. With few exceedances the parameters are uncertain, and the
plug-in p is too extreme at both ends.

**The correction.**
1. Make 40 bootstrap fits for each pool.
2. Calculate the record's p for each fit.
3. Take the mean. This is the **predictive p**. It includes the parameter uncertainty.

Table 3. Plug-in p and predictive p (divisions, 180 records, post-hoc)

| model, fit at top | plug-in KS | plug-in tails | predictive KS | predictive tails | fit 25→26 / 26→25 (predictive) | 95% range of expected count |
|---|---|---|---|---|---|---|
| Gompertz, 1% | 0.039 | 13 / 7 | 0.005 | 5 / 3 | 0.263 / 0.001 | ×43 |
| Gompertz, 5% | 0.666 | 3 / 9 | **0.951** | **2 / 6** | 0.265 / 0.688 | ×8 |
| Weibull, 1% | 0.825 | 10 / 7 | 0.192 | 4 / 3 | 0.792 / 0.022 | ×25 |

**Results:**
- At the top 1%, the uncertainty is very large. The expected count at the record has a
  95% range of ×43 (for example, from 0.05 to 2 athletes).
- The predictive p removes the excess tails at the top 1%. But the KS still fails,
  because of the 2026 → 2025 direction.
- The Gompertz at the top 5% is the best: the predictive KS is 0.951, the tails are in the
  range, and the range is ×8. That is 5 times narrower than at the top 1%.

### 5.4 Limits of the bootstrap

- **It shows only the noise inside one season.** It does not show the differences between
  seasons. Some seasons have a prodigy (2025: Lutkenhaus, Tostenson, Hedengren). A bootstrap
  of 2026 cannot know this. This is a probable cause of the failure in the 2026 → 2025
  direction.
- **"Coverage of the record" is a weak test.** It was 96–98% for all three rows in Table 3.
  The actual count at the record is always 1. A Poisson count with a mean near 1 almost
  always includes 1. So this value cannot separate good and bad models.

## 6. Possible next steps

The steps are in the recommended order.

| # | step | why | cost | needs |
|---|---|---|---|---|
| 1 | **Write down the rule "Gompertz, top 5%" (or "N_u ≥ 150"). Then test it on new records.** | Table 2 and Table 3 are post-hoc. Only new records can confirm the rule. | small (code); data below | your choice of data |
| 2 | **ForwardStop for the Gompertz** (section 4.4) | Each pool gets its own threshold from its data, with no percentage to select | approx. half a day | — |
| 3 | **Make the predictive p the standard yardstick** in `record_check.py`, and run part D with the bootstrap | The plug-in p is too extreme when N_u is small (Table 3) | small; a run of approx. 10 min | — |
| 4 | **A between-season term** | The bootstrap does not show season-to-season differences (5.4). Make the predictive interval wider by the spread between 2025 and 2026. | medium | — |
| 5 | **Audit the extreme marks** (section 1.2) | One wrong mark can decide a record test | approx. 100–200 pages | credentials and your approval |
| 6 | **Change `run_all.py` to the selected rule** | Only after steps 1–3 pass | medium | steps 1–3 |

**Data for step 1:**
- **Per-state pools** (51 states × 10 pools × 2 directions ≈ 1,000 records). This needs no
  scrape. But the state records are inside the divisions, so they are not fully new. Small
  states also have very small N_u.
- **A 2024 scrape.** This is the best choice: a new season and new athletes. It also adds a
  third season for the between-season term (step 4). The cost is one more national scrape
  (approximately 18 hours for each sex).

**My recommendation:**
1. Write down the rule now, then do step 3 with it.
2. Do step 2 in parallel, as the alternative rule.
3. For step 1, start the 2024 scrape.

## 7. Result of steps 2 and 3 (added 2026-10-22, later the same day)

### 7.1 What we changed

- **Step 3: the predictive p is now the standard yardstick.** `record_check.py` part D
  runs the bootstrap (40 refits per record) and judges on the predictive p. The plug-in p
  is still in the table.
- **Step 2: ForwardStop for the Gompertz.** `threshold_select.py` now has a `model`
  parameter ("gpd" or "gompertz"). The GPD results did not change (same seed, same values).
  - A new profile-likelihood fit (`tail_models.fit_gompertz_excess`) agrees with the old
    fit to 1e-7 and is approximately 50 times faster.
  - Unit check: on true Gompertz data, the test rejects 5% of the time at α = 0.05
    (KS p = 0.37). So it is correctly calibrated.
- **The new rule under test** is `gompertz-fs`: the Gompertz threshold that ForwardStop
  selects on the fit season. Its settings are the same as the GPD's in `run_all`: 18
  thresholds from 80% to 99.5%, α = 0.05, 199 simulations. We wrote them down before the
  run, so this is a fair test.

### 7.2 Result: `gompertz-fs` fails

Table 4. Division test, 180 records, predictive p (section D of `record_calibration.md`)

| rule | role | predictive KS | 25→26 | 26→25 | tails low / high (1–9) | median z (0.69) |
|---|---|---|---|---|---|---|
| **gompertz-fs** | under test | **0.006** | 0.011 | 0.126 | 3 / **13** | 1.01 |
| gompertz 1% | failed before | 0.016 | 0.404 | 0.001 | 6 / 3 | 0.54 |
| gompertz 5% | post-hoc | 0.824 | 0.346 | 0.796 | 2 / 6 | 0.73 |
| gpd 1% | contrast | 0.000 | 0.003 | 0.000 | 25 / 2 | 0.37 |

- `gompertz-fs` fails four of the five checks. Its errors are on the "too heavy" side:
  13 records are in the high tail.
- **The predictive p helps the top-1% rule.** Its tails are now in the range (6 / 3,
  before 13 / 7). It still fails the KS in the 2026 → 2025 direction (the prodigy season).
- **Gompertz 5% passes all checks again** (KS 0.824, tails 2 / 6, rank-5 KS 0.875). It
  was selected on these records, so this is still not proof.
- **The rank-25/100 check.** A perfect model gets 0.093 (95% range 0.083–0.104). All
  rules get 0.108–0.118. So all rules have a small error at ranks 25 and 100.
  `gompertz-fs` gets 0.1107 and misses the limit of 0.11 by a very small amount.

### 7.3 Why ForwardStop fails: the fallback, not the selection

ForwardStop has three possible results in each pool:

Table 5. `gompertz-fs` by ForwardStop result (180 division records; post-hoc split)

| ForwardStop result | pools | threshold used | median N_u | predictive KS | tails low / high | median z |
|---|---|---|---|---|---|---|
| a real selection ("ok") | 77 | between | 1,147 | **0.642** | 3 / 5 | 0.83 |
| nothing rejected | 89 | the lowest: top 20% | 1,882 | 0.000 | 0 / 7 | 1.34 |
| all rejected | 14 | the highest: top 0.5% | 129 | 0.437 | 0 / 1 | 0.56 |

- **When ForwardStop makes a real selection, the records are calibrated.**
- **In half of the pools (89), it rejects nothing.** It then uses the lowest threshold
  (the top 20%). This is a fallback, not a selection. At the top 20% the Gompertz tail is
  too heavy, as at the top 10% (Table 2).
- **Why it rejects nothing.** The Anderson–Darling test sees the full set of exceedances.
  The body misfit at the top 20% is small in the A² distance. But it becomes a large error
  when we extrapolate to the record. So the test has low power against the error that is
  important to us. (Power check: against GPD data with ξ = −0.3 and N = 1,000, the
  Gompertz test rejects only 20% of the time.)
- **"All rejected" is mostly the boys' 100 m (12 of 14).** A probable cause is ties.
  - 100 m times have only hundredths, so many athletes have the same time.
  - With large N, a test for a continuous model sees the ties as misfit.
  - This is a hypothesis; we did not test it.

### 7.4 What this means, and possible next steps

- The **ForwardStop idea works** where the test has power. The **fallback rule** is the
  problem.
- The best rule so far is still "Gompertz, top 5%" (or a minimum N_u). It is not
  validated, because we selected it on these records.

Possible next steps (your choice):
1. **Change the ForwardStop fallback.** For example: "nothing rejected" → use a fixed
   top-5% threshold, not the lowest grid point. Or start the grid at 90%, not at 80%.
   - Both changes look at these results, so they also need a test on new records.
2. **Test the tie hypothesis.** Add a small random jitter (±0.005 s) to the times before
   the A² test for the 100 m, and see if the boys' 100 m stops "rejecting everything".
3. **Get new records.** A 2024 scrape gives a fair test for any rule that we selected on
   2025–2026. This is now the most important step: every candidate rule has seen these
   180 records.

## 8. Fallback fix, stacked national model, densities (added 2026-10-22)

### 8.1 What we changed

- **The fallback.** When ForwardStop rejects nothing, the rule now uses the top 5%, not
  the lowest grid point. The new rule is `gompertz-fs5`.
- **Ties.** Times have only hundredths. In a large pool, 94–99% of the sprint excesses
  have the same value as another mark. The Anderson–Darling test is for continuous data,
  so it saw the ties as misfit:
  - national boys' 100 m, raw times: p = 0.01 at every threshold;
  - the same times spread by ±0.005 s: p = 0.13–0.79.
  So ForwardStop now spreads each time by ±0.005 s before the test. The fits themselves
  use the raw times.

### 8.2 The division test with the new rule

Table 6. `gompertz-fs5` on the 180 division records (predictive p)

| version | predictive KS | 25→26 | 26→25 | tails low / high (1–9) | median z | passes |
|---|---|---|---|---|---|---|
| fallback fix, raw times | **0.921** | 0.305 | 0.726 | 3 / 9 | 0.77 | 4 of 5 |
| fallback fix + spread times (final code) | 0.079 | 0.099 | 0.717 | 3 / 9 | 0.82 | 4 of 5 |
| fixed top 5% (reference) | 0.937 | 0.301 | 0.491 | 2 / 6 | 0.73 | 4 of 5 |

- **All three pass every record check.** All three fail only the rank-25/100 check.
  - Every rule fails that check (0.11–0.12 against 0.093 for a perfect model).
  - So it is a common error in the body, not a fault of the tail rule. A probable cause is
    that the depth of the lists changes from season to season.
- **The spread times make ForwardStop worse here.**
  - Without ties, the test rejects less, so ForwardStop accepts lower thresholds. Its real
    selections have a median at the top 12%, and the top 10% is too heavy at the record
    (Table 2).
  - The KS falls from 0.921 to 0.079. It still passes, but only just.
- **Conclusion.** The A² test checks the fit of all the excesses. It does not check the
  accuracy at the record. A threshold that it accepts can still be too low for the record.
  In this test, the fixed top 5% is as good as, or better than, every ForwardStop version.

**Possible next rule (your choice):** ForwardStop with a floor at the top 5%.
- Start the grid at the 95% quantile, so ForwardStop can only move u higher.
- It can then react to real misfit, for example the boys' 800 m and 1600 m below.
- It can never select a threshold that is too low.

### 8.3 The national Gompertz model on 2025 + 2026

File: `output/national/2025-2026/gompertz/gompertz.md`, with figures `gompertz_tail_{m,f}.png`.
The bootstrap uses 200 resamples of complete athletes.

Table 7. Thresholds that ForwardStop selected (national, stacked)

| pool | ForwardStop | threshold | N_u |
|---|---|---|---|
| 100m m | ok | top 6.2% | 23,834 |
| 200m m | ok | top 1.6% | 5,620 |
| 400m m | ok | top 3.9% | 10,113 |
| 800m m | all rejected → top 0.5% | top 0.5% | 1,138 |
| 1600m m | all rejected → top 0.5% | top 0.5% | 1,045 |
| 100m f | ok | top 5.0% | 15,557 |
| 200m f | ok | top 5.1% | 14,713 |
| 400m f | nothing rejected → top 5% | top 5.0% | 9,431 |
| 800m f | ok | top 6.2% | 10,420 |
| 1500m f | ok | top 0.5% | 680 |

**What the model says.** Examples, as "one athlete-season in N", with the 95% CI:
- boys' 100 m, 10.30 (rank 100): 1 in 4,160 (3,850–5,202);
- boys' 400 m, 45.21 (the record): 1 in 184,126 (120,930–371,256);
- girls' 800 m, 2:00.11 (the record): 1 in 737,943 (328,003–1,626,390).

**The in-sample check of the records** (z under Exp(1); 20 records):
- **All 20 are in the 95% range.** The lowest predictive p is 0.050 (boys' 200 m, 2026,
  19.86). The highest is 0.978 (girls' 400 m, 2026).
- **The boys' 100 m 9.82 (2025) gets p = 0.058.** The model calls it rare, but possible.
- **The girls' sprints of 2026 sit high (200 m 0.959, 400 m 0.978).** The model expects
  more athletes that fast than there were. This agrees with the old girls' sprint result:
  a fit at a low threshold is slightly too heavy for the girls.

**Bootstrap check.** All 20 point estimates of c and b are inside their 95% CIs. This
needed one fix: the main fit must use the same threshold rule as the bootstrap (the raw
quantile at the selected level).

### 8.4 Density plots

Files: `stages/02_explore/output/density/` (made by `stages/02_explore/density_plots.py`):
- `density_2025_{m,f}.png`;
- `density_2026_{m,f}.png`;
- `density_2025_vs_2026_{m,f}.png`.

**What they show:**
- **The two seasons have almost the same shape.** On a linear scale, the densities of
  2025 and 2026 are on top of each other in all 10 pools.
- **The differences are only in the far tail.** The log-scale row shows that the curves
  separate only below a share of approximately 10⁻⁴: the top 10–20 athletes.
  - Examples: the boys' 800 m and the girls' 400 m and 800 m. In each, 2025 has a few
    marks far ahead of the rest.
  - This is the same "prodigy season" effect that the record tests found.
- **The boys' 1600 m has a peak at 5:00.** Many athletes run just under 5 minutes.
  This is a real target effect, not an error in the data.
