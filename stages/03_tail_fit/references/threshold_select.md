# `threshold_select.py` — automatic threshold choice

Layer 3 reference for stage 03 (moved from the old CLAUDE.md §5). Code comments
in stage 04 cite this file. It addresses the bias–variance tension in
`_config/evt_theory.md` §3.6.

```bash
.venv/bin/python stages/03_tail_fit/threshold_select.py [csv_path]   # default: gpd_tail.EVENT_FILE
```

The script runs two independent methods side by side, plus a comparison verdict.

## Why the obvious approach fails

The naive idea is to sweep `u`, fit a GPD at each, and keep the `u` with the
best goodness-of-fit or the highest likelihood. This is wrong for two reasons:

1. **Changing `u` changes the dataset.** A likelihood computed on 891 points
   isn't comparable to one computed on 74 points. Higher thresholds have fewer
   terms and will usually look "better" for no real reason.
2. **Small samples pass almost any test.** Push `u` high enough and the GoF test
   has no power. It will happily accept a bad fit on 40 points.

Both implemented methods exist specifically to dodge these traps.

## Method A — ForwardStop (sequential hypothesis testing)

Walk the candidate thresholds from **lowest to highest**. At each one, test the
null hypothesis "the excesses above this `u` really are GPD" with an
**Anderson–Darling statistic**, calibrated by **parametric bootstrap** (simulate
from the fitted GPD, recompute the statistic, see where the observed one falls).
AD is chosen over Kolmogorov–Smirnov because it weights the tail of the excesses
more heavily, which is where the misfit is.

Because this is many tests in sequence, raw p-values would inflate the false
positive rate. The **ForwardStop** accumulation statistic controls the false
discovery rate across the ordered sequence: keep rejecting low thresholds until
the accumulated evidence says stop, and take the first non-rejected threshold.

**Other tail models (2026-10-22).** `gof_pvalue` and `select_forwardstop` take
`model="gpd"` (the default) or `model="gompertz"`. The procedure does not depend on
the model; each model supplies a fit, a CDF and a simulator (`GOF_MODELS`). The
Gompertz fit is `tail_models.fit_gompertz_excess` (profile likelihood).
- On true Gompertz data, the test rejects 5% of the time at α = 0.05.
- Its power against small body misfit is low. In the division test, 89 of 180 pools
  rejected nothing and fell back to the lowest grid point
  (`stages/04_pooled_fit/references/pooled_method.md` §13.2).

The defaults are `alpha=0.05` and 199 bootstrap simulations per candidate
threshold. The 199 is a cost/precision tradeoff. It makes the smallest achievable
p-value 0.005, which is fine for this purpose and keeps the runtime sane.

Sample output (100m, reproduced 2026-10-07 after the reorg):

```
   u (s)    N_u   p-value
  11.950   1568     0.005
  ...
  11.480    580     0.190  <-- selected
```

## Method B — Mixture profile MLE

Fit a **lognormal body + GPD tail** as a single joint model, where the split
point is `u`. The key property is that *every observation enters the likelihood
at every candidate threshold*. Points below `u` are scored by the lognormal and
points above by the GPD. The dataset never changes, so **log-likelihoods are
genuinely comparable across rows**, and you can just take the maximum. This is
the direct fix for failure mode (1) above.

Profile over `u` on the candidate grid, and take the `u` with the best joint
log-likelihood.

## Edge detection (added after a real bug)

If the best value sits at the **edge of the candidate grid**, the likelihood
never turned around, which means it's not a real optimum. The script warns
explicitly. Usually it means the lognormal body is wrong for the data, and the
more flexible GPD is expanding to cover the misfit. The response is to widen the
grid and lean on the ForwardStop answer.

The same class of bug applies to ForwardStop: if it rejects nothing, it falls
back to the grid edge.

## The agreement criterion

The two methods' answers are compared. **The criterion should be 10% of the
candidate grid span, not a fixed number of seconds**, because a fixed 0.15s is
meaningful for the 100m and meaningless for the 1600m. Any new comparison logic
must be scale-relative for the same reason.

Crucially, **agreement is only informative if both methods actually converged.**
On the 1600m both returned 291.450s and the harness announced close agreement.
But ForwardStop had rejected nothing and hit the grid edge, and the mixture had
also hit its edge. Two coincident failures at the same boundary are not
corroboration.

## The two guards (ported back 2026-10-09)

`compare()` used to hardcode `spread < 0.15` seconds, and `select_forwardstop`
flagged "everything rejected" but not "nothing rejected". Stage 04 found both
and built its own guards (`stages/04_pooled_fit/references/pooled_method.md` §6).
They are now in this file too:

- the agreement tolerance is **10% of the candidate-grid span**, so it scales
  with the event;
- rejecting **nothing** is a fallback (`note` says so, `converged` is False), as
  rejecting everything already was;
- `compare()` reports agreement only when **both** methods converged.

Check: on the legacy NY boys 1600 m file, the case above, `compare()` now prints
"No agreement to report: ForwardStop and mixture MLE did not converge" instead of
"Close agreement". Stage 04 still uses its own `select_threshold`, which adds
three guards this script lacks: power saturation, an oversized mixture "tail",
and the shape plateau.

**`fallback_u` and `dequantize` (2026-10-22).**
- `select_forwardstop(..., fallback_u=u)`: when nothing is rejected, return u with the
  note "nothing rejected -- fixed fallback u used". The default None keeps the
  lowest-candidate fallback.
- `dequantize(x, resolution, rng)`: add U(−r/2, r/2) noise. Apply it to ForwardStop's
  input for any large pool of times recorded to 0.01 s. Ties otherwise make A² reject a
  continuous model everywhere.
- Results: `stages/04_pooled_fit/references/pooled_method.md` §13.3–14.
