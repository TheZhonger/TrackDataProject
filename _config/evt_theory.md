# The statistics, from the ground up

Layer 3, shared by stages 03 and 04. It is the theory that every fit in the project
rests on. Section numbers are kept from the old CLAUDE.md §3, because code
comments cite them (e.g. "evt_theory.md section 3.5").

---

### 3.1 Why not just fit a distribution to everything

Fit a lognormal to all 8,000 times in an event and you get a curve that matches
the middle beautifully and is wrong where it matters. Maximum likelihood spends
its effort where the data is dense, which is the middle, because that's where
most of the likelihood lives. The 40 fastest athletes contribute almost nothing
to the total likelihood, so the fitted curve is free to be badly wrong out there.
Then you extrapolate to a 10.31 and get a probability that's off by orders of
magnitude.

The fix is to throw the body away and model only the tail.

### 3.2 Pickands–Balkema–de Haan

This is the theorem the whole project rests on. Plain-language version:

> Take any reasonably behaved distribution. Pick a high threshold `u`. Look only
> at the observations above `u`, and measure how far above they are. As `u` gets
> higher, the distribution of those *excesses* converges to a Generalized Pareto
> Distribution — **no matter what distribution you started with.**

It is the tail's answer to the central limit theorem. The CLT says averages
become normal regardless of the parent distribution. PBdH says threshold
excesses become GPD regardless of the parent distribution. That universality is
the license for using the GPD here: we don't have to know or claim that sprint
times are lognormal, gamma, or anything else. We only have to be high enough up
the tail.

In symbols, writing `F` for the true distribution of `X`:

```
P(X - u ≤ y  |  X > u)  →  G(y; ξ, σ)   as u rises
```

Read left to right: "given that a performance already beat the threshold, the
chance it beat it by at most `y`" converges to the GPD `G`.

The GPD survival function, the probability an excess is *bigger* than `y`, is

```
                 ( 1 + ξ·y/σ ) ^ (−1/ξ)      if ξ ≠ 0
  P(Y > y)  =
                 exp( −y/σ )                 if ξ = 0
```

Two parameters:

- **σ (sigma), scale**: how spread out the excesses are. It is in the data's units
  (seconds here). Bigger σ means the tail is stretched out.
- **ξ (xi), shape**: the important one. It controls what the tail does far out.

### 3.3 The three regimes of ξ

- **ξ > 0: heavy tail.** No upper limit. There is always some probability of a
  far more extreme value. Think insurance losses, city sizes.
- **ξ = 0: exponential tail.** No hard limit, but the probability dies
  exponentially fast. The Gumbel case.
- **ξ < 0: bounded tail.** There is a **finite endpoint**. The distribution
  simply stops. This is the regime running data lands in, and it is physically
  sensible: there is a fastest a high schooler can run.

When ξ < 0 the endpoint is

```
  endpoint = u + σ/|ξ|
```

Converted back to seconds, this is the model's **implied wall**: the fastest
time the fitted model says is possible. It is the headline physical output of a
fit, and it's also the best sanity check you have. If the wall lands a hair
faster than the fastest observed runner, the fit is being pinned by one or two
data points and the threshold is too aggressive. (This is exactly what happened
with the 1600m; see `stages/03_tail_fit/CONTEXT.md`.)

### 3.4 Sign convention (read this before debugging anything)

EVT is written for **upper** tails: extreme means big. In running, extreme means
**small**. Rather than rederive every formula with flipped inequalities,
`gpd_tail.py` negates once, near the top of `main()`:

```python
x = -seconds
```

Now fast times are large `x` values, the fast tail *is* an upper tail, and every
textbook formula applies verbatim. Everything is converted back to seconds
before display. **Internal code operates in negated space; printed and plotted
output is in seconds.** Mixing these up is the single easiest way to produce
nonsense here.

### 3.5 From a conditional fit to an actual probability

The GPD gives a *conditional* probability: "given you already beat `u`, how
likely is this?" To make it unconditional, you multiply by the probability of
beating `u` at all. That is estimated by the fraction of the sample above `u`:

```
  ζ  =  N_u / n              # zeta: P(beat the threshold)
  P(X > x)  =  ζ · ( 1 + ξ·(x − u)/σ ) ^ (−1/ξ)
```

where `N_u` is the number of exceedances and `n` the sample size. The return
period is just the reciprocal, `1 / P`, read as "one athlete in that many."

This makes `n` load-bearing. If the CSV is a truncated top-N ranking rather than
a full population, `n` is not the real denominator and every probability is
wrong by that ratio. `gpd_tail.py` has a `POPULATION_SIZE` config knob for
exactly this. Leave it `None` to use the row count, and set it when you know the
true number of athletes who contested the event.

### 3.6 The bias–variance tradeoff in choosing u

This is the central tension of the whole method:

- **u too low:** lots of data (low variance), but the theorem hasn't kicked in
  yet, so the GPD is the wrong shape (high bias).
- **u too high:** the theorem holds well (low bias), but you're fitting two
  parameters to 40 points (high variance), and the fit gets pinned by the single
  most extreme observation.

There is no free lunch. `stages/03_tail_fit/references/threshold_select.md`
covers making this choice defensibly instead of by eye.

### 3.7 Why ξ slides: the penultimate approximation (added 2026-10-09)

**Intuition.** Pickands–Balkema–de Haan says that *far enough* out, excesses
over u look like a GPD. It says nothing about how far is far enough. Suppose the
true tail has no wall but thins out faster and faster, like a bell curve's
(ξ = 0, the "Gumbel domain"). A GPD fitted at any reachable u then sees a tail
that is still bending, and the best GPD to describe a bending tail has a
**negative** ξ. Raise u and the remaining tail bends less, so ξ creeps toward 0.
That is a slide, and every pooled fit in this project shows one (stage 04
`pooled_method.md` §7, §10, §11).

**The math.** Write S(x) = P(X > x) and f for its density, and define the
reciprocal hazard r(x) = S(x)/f(x): the expected extra distance past x, for an
athlete who just reached x. For a GPD, r(x) = σ + ξ(x − u) is a straight line,
and its slope is ξ. For any other tail, the GPD that best matches *at* u has
slope ξ_u = r′(u), the "penultimate" shape. A normal tail gives
ξ_u = u·M(u) − 1 (M = Mills ratio, (1 − Φ)/φ). That is negative, and it tends
to 0 as u → ∞ (−0.40 at the top 20%, −0.13 at the top 1%).

**One caution, learned the hard way.** r′(u) is the *local* shape at u. A GPD
*fitted* above u averages the shape over the whole excess range, so on true
normal data it returns about −0.13 at the top 20%, not −0.40
(`TailFit.implied_gpd_xi` computes the fitted value). Compared on that correct
basis, the pooled fits slide in the same direction as a normal tail
(correlation 0.85 over 30 fits) but sit about 0.12 lower. **The fast tail is
lighter than normal** (on the seconds scale, times are right-skewed, which
shortens the fast side).

**What fits it.** Two tails that are unbounded but lighter than normal:
the Weibull-type S ∝ exp(−((x − μ)/s)^θ) (θ = 2 behaves like a normal tail,
larger θ is lighter), and its θ → ∞ limit, the **Gompertz** S ∝
exp(−c(e^{y/b} − 1)), the classic tail of human mortality. Both have the slide
built in: their local shape is negative at u and goes to 0 further out.
`stages/03_tail_fit/tail_models.py` implements them. Stage 04
`pooled_method.md` §12 has the evidence that they beat the GPD.

**Physical meaning.** A sliding ξ does not measure a physiological wall. High
school marks sit far below the human limit (a 10.3 s 100 m against roughly
9.6 s at world class), so the tail we see is the shape of the *talent
distribution* near its top, not of a ceiling. A wall estimated from a GPD at a
reachable threshold sits too close to the data, and it moves when the data's
top end moves (the 2026 mile record beat 2025's whole wall interval).

### 3.8 Judging a model at the record (added 2026-10-14)

**Intuition.** A record is one number. Even a perfect model can't tell you
exactly how many athletes "should" have beaten it, only the odds. So one record
being far from the model's expectation proves little, while 30 records all
leaning the same way proves a lot.

**The math.** Let the season have n marks, and let S(t) be the model's
probability that one athlete-season is t or faster. The number of athletes the
model expects at or beyond the k-th best mark t_k is z_k = n·S(t_k). If the
model is right, z_k ~ Gamma(k, 1) (for large n). That's because n·S(t_k) is
n times the k-th smallest of n uniform draws.
- **For the record (k = 1), z ~ Exp(1):** median ln 2 = 0.69, central 95% range
  0.025–3.69. A "predicted ÷ actual" of 0.5, or of 2, is ordinary.
- So p_k = GammaCDF(z_k; k) is Uniform(0, 1) under a correct model. Judge a model
  by whether many records' p's look uniform (a KS test, or a QQ plot).
  - **Small p:** the model called the mark too rare. That is the GPD near its wall.
  - **Large p:** the model expected more athletes that fast than there were
    (too heavy).
- Code: `stages/03_tail_fit/tail_models.rank_pit`.
- Results: `stages/04_pooled_fit/references/pooled_method.md` §13.

**Why the threshold matters most here.** A model fitted to the top 10% is
mostly fitted to the bulk of that 10%. If the tail's curvature keeps changing
(it does: §3.7), the fit can be right at rank 100 and wrong at rank 1. Fitting
at the top 1% trades some variance for record accuracy, the usual EVT
bias–variance trade-off, measured where it matters.
