# Data conventions

Layer 3, shared by every stage. These rules hold for every run. Before you read,
write or pool any leaderboard CSV, check it against them.

(Moved from the old CLAUDE.md §2 "Data" on 2026-10-07, with paths updated.)

## Where the data lives

Everything scraped is the **output of stage 01**:

```
stages/01_scrape/output/
  <year>/<ST>/<sex>/<event>.csv     current layout, e.g. 2026/NY/m/100r.csv  (2025, 2026)
  legacy/<ST>/<sex>/<event>.csv     August 2026 scrape.py files (CA, NY, TX)
  individual/<list>.csv             per-athlete career histories (one row per performance)
  html/                             cached athlete bios + rosters (individualScrape)
  _progress/                        scrapeAll resume ledger + per-page partials
```

Scripts never hardcode these. They import them from `src/paths.py`
(`DATA_2026`, `LEGACY`, `INDIVIDUAL`, …).

Two older naming conventions show up in history and in old comments:

- flat `output100.csv`, `output200.csv`, … These became `legacy/NY/m/100.csv` etc.
- `data/<ST>/<sex>/…`. This became `legacy/<ST>/<sex>/…`.

## Schema

One CSV per event, header:

```
name,time,team,grade,state,date
```

The rows are in rank order (do not sort). `--keep-athlete-id` appends `athlete_id`,
which is the join key into `individual/`. The `state` column can contain commas
(`"NY, USA"`), so **always read with `pd.read_csv`, never a manual split**. Read
as UTF-8 explicitly: the 2026 files contain bytes that Windows' cp1252 default
cannot decode.

## The `r` suffix

**`r` means the list was restricted to in-state performances.** `100.csv` and
`100r.csv` are different data, not duplicates. The unrestricted file admits
out-of-state and foreign athletes, and marks set at out-of-state meets. For
`n`-dependent statistics (`evt_theory.md` §3.5) this changes the denominator, so
do not mix the two within one fit.

## "The 1600m" is not a national event

States disagree on which metric mile they contest, and each is a separate list.
Files are named for what was actually run: `1600r.csv`, `1miler.csv`,
`1500r.csv`. Nationally in 2026 (the variant with the most rows wins; the
northeast map is the same in 2025):

| | 1500 m | 1 mile | 1600 m |
|---|---|---|---|
| boys | HI OR RI VT | MA | the other 46 |
| girls | HI IA NY OR RI VT | MA | the other 44 |

Every state also has small off-distance lists (HI boys' 1-row `1600r`), which
the most-rows rule ignores. The map can differ by sex within one state: NY boys
run the 1600, NY girls the 1500. Consequences for the statistics:

- A near-empty file (MA `1600r` 30 rows, NY girls `1600r` 96) is a state that
  runs something else, not a thin field. Fitting a tail to it would be fitting
  the wrong event. The rule everywhere is **the variant with the most rows**.
- 1500m, 1600m and 1609.34m are **different distances**. They cannot be pooled
  without conversion; pooling unconverted miles to reach a usable `N_u` would be
  buying sample size with a distance error.
- **Conversion targets differ by sex: boys onto 1600 m, girls onto 1500 m**,
  the distance most of each field runs. Factors (`src/distances.py`, the single
  source of truth for stages 03 and 04):

  | | → 1600 m (boys) | → 1500 m (girls) |
  |---|---|---|
  | from 1600 m | 1 | × 0.933877 (Riegel) |
  | from 1 mile | × 0.99419 (distance ratio) | × 0.928130 (Riegel) |
  | from 1500 m | × 1.070805 (Riegel) | 1 |

  Riegel is `t2 = t1 * (d2/d1)^1.06`. Return periods are unit-free, so boys' and
  girls' results remain comparable despite the different scales. See
  `stages/04_pooled_fit/references/pooled_method.md` §2–3.

## The `time` column is dirty on purpose

It's scraped: `10.52`, `2:05.31`, `4:31.02h`, `10.31a`, `DNF`, blanks. Each
parser normalizes to float seconds and returns `NaN` for anything it can't read.
There are two families:

- **Lenient**, in `src/util.py`. It strips everything but digits, `:` and `.`.
  The scraper and the stage 02 plots use it.
- **Strict**, with copies in `stages/03_tail_fit/gpd_tail.py` and
  `src/pool_data.py`. It deliberately does **not** strip commas,
  so `"2:05,4"` becomes NaN instead of silently becoming 174.0. A NaN you can see
  beats a wrong number you can't. Keep the inference code on the strict one.
