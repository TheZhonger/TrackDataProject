<!-- Archived 2026-10-07: the root CLAUDE.md as it stood before the ICM reorganisation.
     Its content now lives in CLAUDE.md, CONTEXT.md, _config/*.md and the stage
     references/ + CONTEXT.md files. Paths below are the OLD layout. Do not edit. -->

# CLAUDE.md — Track Times Research

Background for Claude Code working in this repo. Read this before touching the
statistics. Everything about file paths and "current state" should be
re-verified against the working tree — this doc describes intent and reasoning,
which changes slower than code.

---

## 1. What the project is trying to do

Score and compare high school track & field performances **across events**
(100m, 200m, 400m, 800m, 1600m) on a single scale of "impressiveness."

The hard part is the cross-event comparison. A 10.31 in the 100m and a 4:08 in
the 1600m are both good, but "good" means something different in each event
because the fields have different depth, different spread, and different
physiological ceilings. The goal is a number that says *how rare* a performance
is, in a way that's comparable between events.

### Approaches already tried and rejected

| Approach | Why it was dropped |
|---|---|
| Truncated normal (scipy `minimize` on a truncated log-likelihood) | Built for a truncated top-N list; the data turned out to be complete, so truncation wasn't needed |
| Lognormal z-scores on the whole distribution | Fits the body fine, but the body is not what we care about — it systematically misses the tail |
| Rank-based normalization | **Fundamental flaw.** Rank cannot see margin of victory. Winning by 0.01s and winning by 1.5s produce the same rank-1 z-score. Impressiveness is exactly the thing rank throws away. Do not reintroduce this. |

### The approach that stuck

Extreme value theory. Model only the **tail** of each event's distribution with
a Generalized Pareto Distribution (GPD), then convert any query time into an
exceedance probability and a return period ("a performance this fast happens
about once in N athlete-seasons"). Return periods are unit-free, so they compare
across events.

---

## 2. Repo layout

Scripts (all Python, all standalone, all with a CONFIG block or argparse):

- **`gpd_tail.py`** — the main inference script. Fits a GPD to one event's tail,
  scores query times, prints a report, writes a 4-panel diagnostic figure.
- **`threshold_select.py`** — picks the threshold `u` automatically by two
  independent principled methods and compares them.
- **`plot_events.py`** — exploratory histograms of all five events in one figure.
- **`scrapeAll.py`** — the current scraper: many states/years/sexes/events in one
  resumable run. **See [SCRAPING.md](SCRAPING.md)** before running or changing
  any scraper. It documents the athletic.net quirks the design depends on, and
  currently opens with a live data-integrity problem in `data/2026/`.
- **`individualScrape.py`** — per-athlete career histories (one row per
  performance, not one per athlete). **`scrape.py`** is the superseded original;
  never `import` it, its body runs at module level.

### Data

One CSV per event, header:

```
name,time,team,grade,state,date
```

Three naming conventions appear in the history — `output100.csv`,
`output200.csv`, … in a flat directory (gone from the working tree; several
plotting scripts still point there and are broken); a state/sex tree like
`./data/NY/m/100r.csv`; and the current `./data/<year>/<ST>/<sex>/<event>.csv`,
e.g. `./data/2026/NY/m/100r.csv`. Check which one the working tree uses before
assuming.

An **`r` suffix means the list was restricted to in-state performances**.
`100.csv` and `100r.csv` are different data, not duplicates — the unrestricted
file admits out-of-state and foreign athletes and marks set at out-of-state
meets. For `n`-dependent statistics (§3.5) this changes the denominator, so do
not mix the two within one fit.

**"The 1600m" is not a national event.** States disagree on which metric mile
they contest, and each is a separate list: CT runs the 1600m (1,319 marks in
2026), MA runs the mile (2,144 — its 1600m list holds 30), RI runs the 1500m
(264 — its 1600m list holds 10). Files are named for what was actually run:
`1600r.csv`, `1miler.csv`, `1500r.csv`. Two consequences for the statistics:

- A near-empty `1600r.csv` is a state that runs something else, not a thin
  field. Fitting a tail to MA's 30 rows would be fitting the wrong event.
- 1500m, 1600m and 1609.34m are **different distances**. They cannot be pooled
  into one distribution without conversion; for the GPD work they are three
  events with three tails. This bears directly on §8's open question 2 about
  exceedance counts being comparable — pooling state miles to reach a usable
  `N_u` would be buying sample size with a distance error.

The `time` column is dirty on purpose (it's scraped): `10.52`, `2:05.31`,
`4:31.02h`, `10.31a`, `DNF`, blanks. Every script has its own `parse_time()`
that normalizes to float seconds and returns `NaN` for anything it can't read.

**Scraping stack:** SeleniumBase with `SB(uc=True)` (UC Mode, stealth) plus
`uc_open_with_reconnect`, then BeautifulSoup on `get_page_source()`. athletic.net
is an Angular app behind a login, which is why plain `requests` doesn't work.

---

## 3. The statistics, from the ground up

(Now `_config/evt_theory.md`, sections 3.1–3.6, text lightly edited for
cross-references.)

---

## 4. `gpd_tail.py`

(Now `stages/03_tail_fit/references/gpd_tail.md`, text lightly edited for paths.)

---

## 5. `threshold_select.py`

(Now `stages/03_tail_fit/references/threshold_select.md`. One correction made on
the move: this section claimed the 10%-of-grid agreement criterion and the
"nothing rejected" fallback detection were implemented in threshold_select.py.
The working tree's copy still hardcodes `spread < 0.15` and reports "nothing
rejected" as "ok" — see pooled2026/README.md §6, now
stages/04_pooled_fit/references/pooled_method.md.)

---

## 6. `plot_events.py`

Exploratory, not inferential. Reads `output100.csv` … `output1600.csv` and draws
all five as histograms in a 2×3 subplot grid (sixth slot switched off).

Per panel: mean and median vertical lines, `n`, and standard deviation
(`ddof=1`, Bessel's correction, since these are samples not populations). Mean
and median are both drawn because race times are right-skewed — a few slow
runners drag the mean but not the median, and the gap between the two lines is a
quick read on how skewed the event is.

Bins default to `"auto"` (numpy picks the wider of Freedman–Diaconis and
Sturges). X-axis ticks are formatted `m:ss` once times exceed a minute.

CLI: `--dir`, `--bins`, `--density`, `--out`.

---

## 7. Hard-won lessons — do not relearn these

(Now `_config/lessons.md`, text lightly edited, plus three lessons from SCRAPING.md
and pooled2026/README.md.)

---

## 8. State as of last recorded session (re-verify)

**100m** — healthy. Wide stable plateau, ξ ≈ −0.25 to −0.27 across the whole
candidate range (varying by only ~0.07 end to end). ForwardStop selected
u = 11.48s, N_u = 580, ξ = −0.270; the mixture hit its grid edge at u = 11.95s,
ξ = −0.347. The 0.47s gap looks alarming but isn't, because ξ barely moves over
that span — the plateau is the real finding. One open wrinkle: in the log-scale
tail panel, the single fastest observed time sits noticeably above the fitted
curve.

**1600m** — not healthy. No plateau; ξ slides to −0.66 at the chosen threshold,
and the model-implied wall lands only about two seconds faster than the fastest
observed runner. Both selection methods fell to the grid edge at 291.450s. The
threshold is too aggressive. Expectation from the stability plot: ForwardStop
should reject everything below roughly 275s and settle in the high 270s.

### Open questions

1. Resolve the 1600m: is there genuinely no stable GPD regime in this data, or
   does the candidate grid just need widening?
2. Once both events sit on genuine plateaus with comparable ξ, **check that
   exceedance counts are in the same ballpark.** If the 100m lands on 678 and the
   1600m on 90, the noise floors differ enough that the scores aren't equally
   trustworthy even when both fits are individually valid.
3. Unify threshold selection and tail fitting into one pipeline across all five
   events.
4. Cross-event score aggregation — the actual point of the project — once
   per-event fits are reliable.

---

## 9. Working conventions

(Now in the root CLAUDE.md, "Working with Daren", text unchanged.)
