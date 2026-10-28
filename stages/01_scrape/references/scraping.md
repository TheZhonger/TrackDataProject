# Scraping — data acquisition from athletic.net

Layer 3 reference for stage 01 (this was the root `SCRAPING.md` before the
2026-10-07 reorganisation). The statistics are in `_config/evt_theory.md`. This
covers where the CSVs come from. Read it before running or changing any scraper.
Paths below are relative to `stages/01_scrape/` unless they start at the repo root.

Everything here was verified against the live site on 2026-09-08. athletic.net
changes its markup without notice, so treat "verified" as "was true then" and
re-check with `--dump-html` if results look wrong.

---

## 0. Resolved: 18 files in `2026/` once held the wrong event

**Status: resolved. Verified 2026-10-07: every `2026/<ST>/<sex>/1600r.csv` opens
on a mile-range time (e.g. NY boys `4:08.19`, 4,430 rows).** The incident is
kept here because the trap is still live for any new event.

A run on 2026-09-11 used `--events 100,1600` instead of `100m,1600m`.
**athletic.net silently falls back to a default event when the slug is not
recognized**, and it does not error. It returns a full, healthy-looking list.
Every `1600r.csv` written by that run held **100 m data**: NY boys' `1600r.csv`
and `100r.csv` were identical frames, 7,972 rows each, with times like `10.44`.
The files were deleted and rescraped with the right slug (`--force` was needed,
because the job key is built from the *filename* stem `1600`, which is the same
either way).

**The rule: always pass the event slug exactly as it appears in the URL, with
its unit: `100m`, `1600m`, `110mH`, `4x100`.** Since 2026-10-09 `scrapeAll.py`
refuses any slug outside the confirmed list (§8 item 9), with a hint for a
unit-less one (`1600` → `1600m?`). `--allow-unknown-slug` overrides it for a new
event, and then nothing in the pipeline can detect a silent server-side
fallback. The filename strips the trailing `m`, so
wrong URLs produce right-looking filenames. Sanity-check a new event by opening
one output file and confirming the times look like that event.

---

## 1. The three scrapers

| Script | Role | Status |
|---|---|---|
| [scrapeAll.py](../scrapeAll.py) | **Current.** Many states/years/sexes/events, auto page discovery, resumable | Use this |
| [individualScrape.py](../individualScrape.py) | Per-athlete career histories (every mark, all seasons, track + XC) | Current, different purpose |
| [scrape.py](../../../_archive/scrape.py) | The original one-list-per-run scraper | Legacy; archived in `_archive/` as a record |

`scrapeAll.py` produces **one row per athlete** (their season best) for a whole
ranking list. `individualScrape.py` produces **one row per performance** for the
top N athletes on a list. They answer different questions; neither replaces the
other.

**Never `import scrape`.** Its body is module level ([scrape.py:56-74](../../../_archive/scrape.py#L56-L74)),
so importing it launches a browser and starts scraping CA 1600 m.

`scrapeAll.py` imports `parse_roster`, `page_url`, `EMAIL` and `PASSWORD` from
`individualScrape.py` — deliberately, so the fragile XPath lives in exactly one
place. (It used to pull in matplotlib transitively through `plotByDate`; since
the reorganisation `individualScrape` takes `parse_time` from `src/util.py`.)

---

## 2. The single most fragile thing: the XPath spine

`parse_roster` walks a hand-written XPath into the results table. On 2026-09-08
it was returning **zero rows on every page** — the absolute path in `scrape.py`
had drifted by one step (`div[2]/div[2]` → `div[2]/div[1]`) when a wrapper div
moved upstream.

It failed in the worst possible way: **a rankings page that parses to zero rows
is indistinguishable from the end of a list.** Scrapes look like they finished
successfully and write truncated or empty files.

The fix ([individualScrape.py:71-81](../individualScrape.py#L71-L81)) anchors on the
table's id instead of on position:

```python
TBODY = "//table[@id='rankingsTable']//tbody[contains(@class,'event-results')]"
```

This survives wrapper reshuffling. The per-column `/td[N]` offsets were *not*
affected and are still correct:

| Cell | Contents |
|---|---|
| `td[5]` | athlete name + `/athlete/<id>/...` href |
| `td[7]` | the mark, as the text of the cell's `a[href*='/result/']` link (see below) |
| `td[10]` | state (blank on ~3% of rows) |
| `td[12]` | grade |
| `td[15]` | team — **plain text when the team has no profile link** |
| `td[16]` | date, `"Jun 07"` style, no year |

***If a run suddenly marks many jobs `empty`, suspect this before believing the
data.** Diagnose with `--dump-html` and check whether the saved page has
`tr[id]` rows that the parser did not find.

### The same failure one level down: blank marks (2026-10-07)

Between the 2026-09-13 and 2026-10-07 runs athletic.net wrapped the mark one
level deeper:

```
td[7] > div > span.me-1 > a[href="/result/…"] > span "3:49.83"
                        > span.wind " (0.2)"        (sprints, sometimes)
```

`_rank_mark` read the cell **by position** (`cell[0][0].text`) and turned any
mismatch into `""`. So every row parsed with its name, team and date, but no
time. A full run (`1mile,1500m`, 9 states, both years and sexes) wrote 68 files
with an entirely blank `time` column and marked every job `done`. It hit every
event, `100m` included. It is fixed by reading the result link's text, falling
back to the first mark-shaped token in the cell with the parenthesised wind
removed. The 68 files were rescraped with `--force`.

**Guard:** `run_job` now stops the whole run with `stop_reason: blank-marks`
(exit code 3, `ParserBroken`) when more than half a page's rows have no mark.
Rerunning won't help with this one. Save a page with `--dump-html` (it now
prints the blank-mark count and the first mark), inspect `td[7]`, and fix
`_rank_mark`.

### The same failure, a third time: a short first page (2026-10-08)

During the national sweep five boys 800m lists (IN, KS, KY, LA, MD) were scraped
back-to-back (06:56:25–06:57:07, about 8 s each). Each fetched **one page of 5
rows**, then stopped as `duplicate` and was marked `done`. The 5 marks are real
(IN's leader is 1:47.86), so this was a partial render during a brief site
hiccup, not wrong-event data. But a state's 800m list has thousands of rows (IN
has 2,873 boys in its 100m), and nothing in the scraper compares a list to its
state's other events. A short first page looks exactly like a tiny list.

**Guarded since 2026-10-09.** When a list ends after one page of fewer than 100
rows, `run_job` re-fetches page 1 once. If the re-fetch has more rows, it
restarts the list. Otherwise the ledger gets `short_list: true`, plus
`suspect_short: true` (and a printed warning) when the event is 100–800 m and
the same state's largest other list has more than 1,000 rows. Before the guard,
the blank-marks check covered marks but not list length. A flagged
job still needs a human decision: redo it with `--force`, scoped to exactly that
job.

### Known fidelity loss

`parse_roster` reads the team from `td[15]/a[1]` and falls back to
`"Unattached"` when there is no anchor. Real team names are lost that way —
`Sheridan-WY` and `Otto-WY` were 2 of 100 rows in a WY sample, consistent with
the 0.6% `Unattached` rate in the older NY files. Left as-is deliberately, so
new files stay consistent with the old ones. Changing it is ~2 lines in
`parse_roster` (take the cell text when there is no anchor).

---

## 3. Four facts about athletic.net that the design depends on

**A full page is exactly 100 rows.** Verified arithmetically against every
legacy CSV: CA 1600 m is 15,371 rows over the 154 pages `scrape.py` hardcoded
(153·100 + 71); NY 100 m is 8,090 over 81 pages (80·100 + 90). CA 100 m, NY 1600
and NY 800 agree exactly. So a short page is reliably the last page, which is
why `scrapeAll.py` probes the following page with a shorter timeout.

**A list ends in one of two different ways, and both have to be handled.**

*Multi-page lists clamp.* `?page=9999` on WY 1600 m (3 pages) returns the *last
page's* 99 rows. A naive "stop when a page is empty" sentinel would loop forever
on the final page. The duplicate guard in `run_job` — stop when a page
contributes no athlete id that is not already banked — is what ends these jobs
(`stop_reason: duplicate`).

*Single-page lists do not clamp.* Past the end of a one-page list athletic.net
does **not** render an empty table — it drops the `#rankingsTable` element
entirely and renders **`No Results Found`** in its place, on a ~115 KB page
(a page with rows is ~470 KB). Verified on DC 3200 m (95 rows) and VT 3200 m
(21 rows), at both `?page=2` and `?page=9999`, and it is not a timeout artifact:
a 20 s wait gives the same result as 6 s.

This bit once, and badly. `fetch_page` originally used "no `#rankingsTable`" as
its proxy for "nothing rendered", so the probe past the only page was judged an
`error`, retried three times, and raised `Blocked` — aborting the whole run.
**Every list that fits on one page was unscrapeable.** The fix keys on the
positive marker instead (`NO_RESULTS`, checked before the table check), which is
present on every past-the-end page and absent from every page that has rows.
These jobs now end with `stop_reason: short-page-confirmed`.

The general lesson: *absence* of an expected element is a bad render check,
because it cannot distinguish "the app chose not to draw this" from "the app
never ran". Prefer a positive marker. `--dump-html` now warns if the page past
the end reads as `error` rather than `empty`, which is the signature of this
class of bug recurring.

**`?restrict=true` is the in-state filter.** Confirmed on NY 2026 100 m:

- without it — page 1 opens `Johan-Ramaldo Smythe 10.24 JAM`, state column is a
  mix of `NY, USA` / `NJ, USA` / `PA` / `JAM`
- with it — page 1 opens `Kaeden Herbert 10.44 NY`, all 100 rows read `NY`

That reproduces the legacy `output/legacy/NY/m/100.csv` vs `100r.csv` pair exactly, down
to Herbert's mark changing 10.43 → 10.44. So restrict drops **performances set
at out-of-state meets**, not merely out-of-state athletes — the restricted list
is a strict subset (0 names unique to it, 117 dropped, 7,972 vs 8,090 rows).

The parameter name appears nowhere in the page source, so if athletic.net
renames it the server will just ignore the unknown parameter and hand back
unrestricted data under an `r` filename. **The tell is the state column: a
restricted list is essentially uniform in one state.**

"Essentially" rather than "exactly", for two reasons. A school can sit in one
state and compete in another's league: `output/2026/DC/m/3200r.csv` is 92 `DC` rows
and 3 `VA` rows, all three from Flint Hill. And the state cell is often simply
blank — 3% of rows on a WY sample, but 65% on `output/2026/RI/f/1500r.csv`. So read
the check as "the non-blank values are one state plus a handful of neighbours" —
a *mix* of far-flung states and country codes (`JAM`) is what unrestricted data
looks like.

**Which mile a state runs is a per-state fact, and each is a separate event.**
There is no single "the 1600 m" nationally. Confirmed for 2026 boys:

| State | Event it actually contests | Rows | Its `1600m` list |
|---|---|---|---|
| CT | `1600m` | 1,319 | — |
| MA | `1mile` | 2,144 | 30 |
| RI | `1500m` | 264 | 10 |

A near-empty `1600m` list is therefore **not** an error and not an empty state —
it means that state files its mile under a different slug. Scraping `1600m`
nationwide silently under-collects exactly the states that don't use it.

Two consequences:

- A distance sweep needs either a per-state event map or all three slugs run
  everywhere, keeping whichever is populated. No such map exists yet; only
  CT/MA/RI are known.
- **The three are different distances** — 1500 m, 1600 m, and 1609.34 m. Their
  times cannot be pooled into one distribution without conversion, and for the
  GPD work they are three separate events with three separate tails.

---

## 4. Output layout and naming

```
output/<year>/<ST>/<sex>/<event><r>.csv        e.g. output/2026/CA/m/1600r.csv
```

Columns are `scrape.py`'s six, unchanged, in rank order (do not sort):

```
name,time,team,grade,state,date
```

- The `r` suffix means **restricted** (in-state). It is on by default;
  `--no-restrict` drops both the parameter and the suffix.
- The filename drops a trailing `m` from the URL slug: `1600m` → `1600`.
  Slugs not ending in `m` (`110mH`, `4x100`) are left alone.
- `--keep-athlete-id` appends an `athlete_id` column; that is the join key into
  `individualScrape.py`'s output.

***Legacy files live at `output/legacy/<ST>/<sex>/<event>.csv`** (CA, NY, TX;
they were `data/<ST>/<sex>/` before the reorganisation) and are untouched.
Where the old and new conventions would collide, `scrapeAll` adopts the existing file as `skipped` rather than overwriting it.

`time` is dirty by design — `10.52`, `4:31.02h`, `10.31a`, blanks. Parsing lives
in `src/util.py` (`parse_time`), with stricter copies in the stage 03/04 fitting code
(`_config/data_conventions.md`). The `state` column can contain commas (`"NY, USA"`),
so **always read these with `pd.read_csv`, never a manual split**.

---

## 5. How resume works

Two levels, both under `output/_progress/`:

```
_progress/progress.json              the ledger: one entry per job
_progress/partial/<key>.csv          rows saved page by page, with a page column
```

- Each page's rows are appended to the partial **the moment they parse**, then
  the ledger is rewritten atomically. A hard kill loses at most one page.
- On resume, the highest page in the partial is **dropped and re-fetched
  unconditionally**. That is correct whether the kill tore a half-written page or
  landed cleanly between two, without having to work out which.
- On completion the partial is collapsed into the real CSV, deduplicated, the
  `page` column dropped, written via a temp file and `os.replace`, and only then
  is the job marked `done`. A crash between those two steps leaves a complete
  file and a `running` job, which the next pass re-finalizes cheaply.

Job statuses: `pending` · `running` (killed mid-job — resumable, **not** a
failure) · `done` · `failed` (blocked, or hit `--max-pages`) · `empty` (list has
no rows) · `skipped` (output already existed and was adopted).

Verified live: WY 1600 m scraped clean (298 rows), then interrupted at page 2
and resumed — the resulting frame was `.equals()`-identical to the uninterrupted
baseline, zero duplicates.

**On a block the whole run stops** (exit code 2) rather than continuing. When
athletic.net starts blocking, every subsequent job would fail too, so continuing
just burns the queue and deepens the block. Rerun the same command later.

---

## 6. Running it

Run with the project venv. Default paths are anchored on the repo (`src/paths.py`),
so any working directory works. The full flag list is in
`.venv/bin/python stages/01_scrape/scrapeAll.py --help`; the ones that matter:

| Flag | Notes |
|---|---|
| `--states` | abbreviations or full names, or `all` (51, DC included) |
| `--years` | must be a column in `references/State ID List - Sheet1.csv` (2026, 2025) |
| `--sex` | `m` / `f`. Both confirmed working |
| `--events` | **URL slugs with units** — see §0 |
| `--dry-run` | job matrix + time estimate, no browser |
| `--retry-failed` | requeue `failed` and `empty` jobs |
| `--force` | delete the selected jobs' CSV, partial and ledger entry, rescrape |
| `--dump-html PATH` | save the first job's page 1 and probe `?page=9999` |
| `--max-pages` | default 400; hitting it marks the job `failed`, keeps the partial |
| `--jobs-per-session` / `--pages-per-session` | browser recycle, defaults 5 / 500 |

All four filters are required — the full matrix is ~1,020 jobs and ~57 hours, so
there is no default.

Credentials come **only** from `ATHLETIC_EMAIL` / `ATHLETIC_PASSWORD`. The
hardcoded fallback pair was removed on 2026-10-09. Without them, a run continues
signed out and says so. The old password still sits in plain text in
`_archive/scrape.py`, so change it on athletic.net.

### Gotchas

- ~~`--dry-run --force` really deletes files.~~ Fixed 2026-10-09: under
  `--dry-run`, `--force` only reports what it would delete, and nothing is saved.
- **`--max-attempts` (default 3) counts your own Ctrl-Cs.** Interrupt the same
  job three times and it stops being queued, even with `--retry-failed`. Raise
  the flag rather than using `--force`, which throws away the saved pages.
- **`--progress-dir` must match between runs** or nothing resumes.

---

## 7. Current data state (verified 2026-10-22)

Ledger: 1,431 jobs, all `done` (1,401), `empty` (27) or `archived` (3); no
partials. The last run was the 2025 boys' resume, finished 2026-10-15.

| scope | state |
|---|---|
| 2026, all 51 states, both sexes, all seven lists | complete |
| 2025 boys, all 51 states | complete and verified (below) |
| 2025 girls, all 51 states | complete and verified 2026-10-22 (rescraped 2026-10-21/22) |

**Why the 2025 girls were rescraped:** the 2026-10-09 run had no credentials (§6), and
signed-out lists stop at 5 rows. The ledger calls those jobs `done`, so
`--retry-failed` skipped them. The 2026-10-21 `--force` run cleared all of them
up front, so this no longer applies.

**2025 boys checks (2026-10-20):**
- 349 files; row counts match the ledger exactly.
- 696,904 rows, with 0 unparsable times, 0 duplicate rows and 0 unsorted files.
- Mile-map lists are full (e.g. OR 1500 m: 2,152 rows vs 2,242 in 2026).
- The 20 files with 5 rows or fewer are genuine off-distance lists.
- Median 2025/2026 row ratio on the core events is 0.95. Outliers:
  - OH 0.42–0.49 and MO 0.60–0.74 (low);
  - AR 1.6–2.0 (high).
  
  These look like athletic.net coverage differences, not scrape errors:
  multi-page lists with no truncation flag.
- Top marks to audit:
  - 100 m 9.82 (TX);
  - 1600 m 3:57.28 (IA).

The short-first-page guard (§2) fired once (2026 NH girls 400 m) and recovered
the full list (424 rows).

**The 11 `empty` jobs are real**, not failures: a state with no list at that
distance (boys 1500 m in AK LA MS NE WV; girls 1500 m in KS NM OK WV; girls mile
in NM OK).

**Fixed since 2026-10-08:** the five truncated boys 800 m lists (IN KS KY LA MD)
were rescraped; their 800/400 row ratios are now 0.84–1.12. No core-event list
(100–800 m) anywhere is a single short page.

**Archived 2026-10-09** (`_archive/scrape_test_files/`, ledger `status: archived`):
`2026/WY/m/1600.csv` (unit-less slug, §0) and the `3200r` test files for DC and VT.

**Sanity scans.** Every boys and girls 2026 file with 100+ rows has a median in
its event's plausible range, so no file is the §0 wrong-event trap. Junk rows
still exist on the slow side (e.g. WV's 800 m has `2:37:40.00`); stage 04's fence
removes them. The fastest boys 100 m in the country (9.88, TX, Mar 07) is the same
athlete as the second-fastest 200 m (20.22, the same day). That is
national-record territory, possibly wind-aided, but nothing in the list marks
it. It stays in, flagged.

**Which mile each state runs** (most rows wins, `src/distances.main_mile_slug`; 2026):

| | 1500 m | 1 mile | 1600 m |
|---|---|---|---|
| boys | HI OR RI VT | MA | the other 46 |
| girls | HI IA NY OR RI VT | MA | the other 44 |

The northeast map is the same in 2025. Every state also has small lists for the
other distances (the same athletes' off-distance races, e.g. HI boys' 1-row
`1600r`). Near-empty files are correct *by nature*.

`output/legacy/` (CA, NY, TX) is from `scrape.py` in August and is unaffected.

**2025 girls checks (2026-10-22):**
- 357 jobs: 349 `done`, 8 `empty` (genuinely absent off-distance lists).
- Row counts match the ledger.
- 535,265 rows, with 0 unparsable times, 0 unsorted files and 1 duplicate row.
  The duplicate is an OR 1600 m athlete listed once with grade 10 and once with
  "-"; the athlete dedupe removes it.
- The 22 files with 5 rows or fewer are off-distance lists.
- Mile-map lists are full (e.g. NY 1500 m: 2,875 rows vs 3,004).
- Median core 2025/2026 ratio is 0.98. Same outliers as the boys:
  OH 0.43–0.53, AR 1.8–1.9.
- Fastest 1600 m is 4:21.81, Jane Hedengren (UT, Jun 05). This is real, almost
  certainly her 1600 m split inside the 4:23.50 national-record mile that day.
  A split is not a standalone race, so audit it with the boys' 9.82 (TX).

**Re-running a slice later** (credentials required; never `--force` unless the
files are known bad):

```bash
scrape() { .venv/bin/python stages/01_scrape/scrapeAll.py "$@"; }
export ATHLETIC_EMAIL=... ATHLETIC_PASSWORD=...
scrape --states OH --years 2025 --sex m,f --events 100m --dry-run
```

---

## 8. Open items

1. ~~Finish the 13 outstanding `1600r` jobs~~. Done.
2. ~~Redo the five truncated boys 800 m lists, then finish the national 2026 sweep~~.
   Done (§7). 2025 boys done 2026-10-15. 2025 girls done 2026-10-22. Both years complete.
3. ~~Add a short-first-page guard~~. Done 2026-10-09 (§2): page 1 is re-fetched once
   and a short core-event list is flagged `suspect_short` in the ledger.
4. ~~The per-state distance-event map~~. Built by the national sweep (§7).
5. ~~Guard against silent event fallback~~. Done 2026-10-09 (§0): unconfirmed or
   unit-less slugs are refused unless `--allow-unknown-slug` is passed.
6. ~~Fix `--dry-run --force`~~. Done 2026-10-09 (§6).
7. Decide on the `Unattached` team fallback (§2).
8. `--min-bytes` ships disabled (`0`). Real rankings pages measured ~470 KB, so
   `--min-bytes 100000` would be a cheap extra "did this page render" check.
9. Confirmed slugs: `100m`, `200m`, `400m`, `800m`, `1500m`, `1600m`, `1mile`,
   `3200m`; both `m` and `f`. This list is now enforced in code
   (`scrapeAll.EVENT_FILE`). Still verify one output file per *new* event before
   trusting a batch (§0).
