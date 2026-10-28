# Stage 01 — scrape

Pull high school leaderboards (and, separately, athlete career histories) from
athletic.net into CSVs. This stage's `output/` **is the project's data**, and
every later stage reads it. The scrapers are SeleniumBase UC mode plus
BeautifulSoup, because athletic.net is an Angular app behind a login.

## Inputs
| Layer | Path | What to use from it |
|---|---|---|
| 3 (reference) | `references/scraping.md` | **read first**: site quirks, the silent-slug trap, resume design, current data state |
| 3 (reference) | `references/State ID List - Sheet1.csv` | state → rankings-list id, one column per year (2025, 2026) |
| 3 (reference) | `../../_config/data_conventions.md` | CSV schema, `r` suffix, which mile each state runs |
| 4 (working) | `output/_progress/progress.json` | resume ledger; tells you which jobs are already `done` |

## Process
1. `scrapeAll.py`: one row per athlete (their season best) per ranking list,
   for many states/years/sexes/events. It is resumable. Start with `--dry-run`.
   Pass event slugs **with units** (`100m`, `1600m`).
   `.venv/bin/python stages/01_scrape/scrapeAll.py --states CT --years 2026 --sex m --events 100m --dry-run`
2. `individualScrape.py`: every mark on the bios of the top N athletes on one
   list, in two phases (`--capture`, then `--parse-only`). `scrapeAll` imports
   `parse_roster` from here, so the fragile XPath lives in one place.
3. Credentials come only from `ATHLETIC_EMAIL` / `ATHLETIC_PASSWORD` (no fallback; without them it runs signed out).
   Unconfirmed or unit-less event slugs are refused (`--allow-unknown-slug` to override).
4. Never `import scrape`. The original scraper lives in `_archive/scrape.py`
   and starts a browser on import.

## Outputs
- `output/<year>/<ST>/<sex>/<event>[r].csv`: leaderboards, `name,time,team,grade,state,date`
- `output/legacy/<ST>/<sex>/<event>.csv`: August 2026 `scrape.py` files (CA, NY, TX); frozen
- `output/individual/<list>.csv`: one row per performance, for stage 02's `plotIndividual.py`
- `output/html/<list>/`: cached bios + `roster.csv` (re-parse without re-scraping)
- `output/_progress/`: the ledger and per-page partials. Don't hand-edit while a run is live.
- SeleniumBase also drops `downloaded_files/` into the working directory. It is harmless.

## Verify
- Open one new file per new event and check that the `time` column is filled and the times look like that event.
  A wrong slug returns a full, plausible list of the *default* event.
- A restricted (`r`) file's non-blank `state` values are one state plus a few neighbours.
- Many jobs suddenly `empty` means you should suspect the XPath spine (`scraping.md` §2) before the data.
- Exit code 3 / `blank-marks` means the mark cell moved. Use `--dump-html` and fix `_rank_mark` (`scraping.md` §2).
- 2026 is complete for all 51 states, both sexes, all seven lists. 2025 is complete for the northeast nine;
  the national 2025 sweep stopped at WY boys 400m (`scraping.md` §7 has the resume command).
- A ledger entry with `suspect_short: true` is a one-page core-event list next to a big sibling list: probably a
  partial render. Redo it with `--force` scoped to that job (`scraping.md` §2).
