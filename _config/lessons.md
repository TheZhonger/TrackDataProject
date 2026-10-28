# Rejected approaches and hard-won lessons

Layer 3, shared by every stage. Read this before proposing a new method. Several
of these ideas were tried and failed for reasons that are easy to forget.

(Moved from the old CLAUDE.md §1 and §7.)

## Approaches already tried and rejected

| Approach | Why it was dropped |
|---|---|
| Truncated normal (scipy `minimize` on a truncated log-likelihood) | Built for a truncated top-N list; the data turned out to be complete, so truncation wasn't needed |
| Lognormal z-scores on the whole distribution | Fits the body fine, but the body is not what we care about — it systematically misses the tail (`evt_theory.md` §3.1) |
| Rank-based normalization | **Fundamental flaw.** Rank cannot see margin of victory. Winning by 0.01s and winning by 1.5s produce the same rank-1 z-score. Impressiveness is exactly the thing rank throws away. Do not reintroduce this. |

The code for the first and last is kept in `_archive/trash/` (`fitCurve*.py`,
`performancezscores`) as a record, not for reuse.

**The approach that stuck** is extreme value theory. Model only the **tail** of
each event's distribution with a GPD, then convert any query time into an
exceedance probability and a return period ("a performance this fast happens
about once in N athlete-seasons"). Return periods are unit-free, so they compare
across events.

## Hard-won lessons — do not relearn these

- **ξ < −0.5 is the MLE regularity boundary.** Near the endpoint the Fisher
  information integrand behaves like `(τ − y)^(α−3)`, which converges only when
  α > 2, i.e. ξ > −0.5. Below that the integral diverges: standard errors and
  asymptotic confidence intervals are not just imprecise, they're invalid. A
  simulation check confirmed it. Nominal 95% intervals achieved ~83% coverage
  at ξ = −0.30 and collapsed to ~21% at ξ = −0.85.
- **Bootstrap is the fallback below the boundary**, but it struggles too. It
  resamples a dataset whose most extreme points do all the work, so resamples
  that omit the fastest runner give very different fits. You get a wide
  interval: honest, but not reliable. The real fix is always to lower the
  threshold.
- **Trust bootstrap intervals over the asymptotic bands** on the stability plot.
- **Coincident failure modes produce false corroboration.** Two methods agreeing
  because both hit the same grid edge tells you nothing. Check *why* they agree.
- **Small samples pass almost any test, and huge samples fail every test.** The
  second half was learned in stage 04: at N_u in the thousands, ForwardStop's
  Anderson–Darling test is power-saturated and rejects everything
  (`stages/04_pooled_fit/references/pooled_method.md` §6).
- **Rank-based normalization can never capture margin of victory.** Closed
  question.
- **A cell that parses to empty is the same silent failure as a page that
  parses to zero rows.** Check for a positive value (a mark is present), and stop
  loudly when it's missing. On 2026-10-07 a markup change blanked every time in
  68 files while the run reported success (`scraping.md` §2).
- **A short first page looks exactly like a tiny list.** Five boys 800m lists came back with
  5 rows each and were marked done. Compare a list's size with the same state's other events,
  not just with a fixed page size (`scraping.md` §2).
- **Absence of an expected element is a bad render check** (scraping). Prefer a
  positive marker. See `stages/01_scrape/references/scraping.md` §3.
- **A cache key must describe the data, not just the settings.** Stage 04's
  threshold cache was keyed on event, sex and grid parameters only. When the
  2026-10-07 rescrape changed which files fed the mile pools, an unchanged key
  would have silently served the old pools' thresholds. The key now includes a
  hash of the pooled sample.
- **A flag is a symptom, not a diagnosis.** The coverage check flagged NY
  girls' and VT's mile pools as under-collected. It was right that the pools
  were missing their fields, and the stated reason (truncated scrapes) was
  wrong: they run the 1500 m. Check every explanation the evidence allows.
- **A wrong event slug fails silently.** athletic.net falls back to a default
  event and returns a healthy-looking list. Always pass slugs with units
  (`100m`, `1600m`). `scrapeAll.py` now refuses unconfirmed slugs.
- **Dropping the bootstrap draws that disagree with your model conditions on the
  answer.** The wall CI kept only resamples with ξ < 0, i.e. only those that
  agreed a wall exists, and kept near-zero-ξ ones as "walls" at −19 s. Map every
  draw onto the same extended scale (no wall = −∞) and let the percentiles say
  "unbounded".
- **matplotlib date histograms** convert all date types to fractional float days
  via `date2num` before binning. Calendar-aligned bin edges need explicit
  construction (e.g. `pd.date_range`).
- **`np.var()` vs `pd.Series.var()`** default to `ddof=0` and `ddof=1`
  respectively. Easy silent discrepancy.
