#!/usr/bin/env python3
"""
Scrape athletic.net rankings leaderboards across every state, resumably.

scrape.py scrapes exactly one list per run: the URL and the page count are
module-level constants that have to be edited and the script rerun. Covering 51
states x 2 years x 2 sexes x 5 events that way is a thousand hand edits, and any
one of them dying to a rate-limit loses the whole list. This fixes the three
things that stand in the way:

    the job matrix   states come from references/"State ID List - Sheet1.csv", which maps
                     all 50 states plus DC to their rankings-list id per year
    page discovery   no numPages. Walk until the list runs out, and tell "the
                     list ended" apart from "we got blocked" (see fetch_page)
    resume           every page lands on disk the moment it parses, and the
                     ledger is rewritten after each one, so a killed run picks
                     up at the page it died on

Nothing is scraped without being asked for: --states/--years/--sex/--events are
all required, because the full matrix is ~1,000 jobs and days of wall clock.
Start with --dry-run, which prints the matrix and a time estimate.

    python stages/01_scrape/scrapeAll.py --states WY --years 2026 --sex m --events 1600m --dry-run
    python stages/01_scrape/scrapeAll.py --states WY --years 2026 --sex m --events 1600m
    python stages/01_scrape/scrapeAll.py --states all --years 2026 --sex m --events 100m,1600m

Output lands in this stage's output/ (<year>/<ST>/<sex>/<event>.csv, ledger in
output/_progress/) wherever the script is launched from; see src/paths.py.

Rerunning the same command after a stop resumes it; jobs already finished are
skipped. See --dump-html for the one-off investigation of the page markup.
"""

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from seleniumbase import SB

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import SCRAPE_OUT, STATE_ID_CSV

# parse_roster is scrape.py's parse_rankings, rewritten to find cells tolerantly
# and to keep the athlete href. Its six output columns were diffed against
# scrape.py's on the same list -- 600 cells, zero mismatches -- and it also
# yields athlete_id, which the repeat-page guard in run_job needs. Importing it
# beats copying: the absolute XPath spine it walks is the most fragile thing in
# this project, and two copies means the next markup change only gets fixed in
# one of them.
#
# Importing individualScrape is side-effect free. (It used to pull in matplotlib
# via plotByDate; parse_time now comes from src/util.py instead.)
# Never import scrape.py (now in _archive/): its body is module-level and would
# start a browser.
from individualScrape import credentials, page_url, parse_roster

BASE = "https://www.athletic.net"

# The six columns scrape.py wrote, in its order. Downstream readers all index by
# name (plotByDate.load_event, dateRegression.load_event, plotIndividual.load), so this
# only has to stay a superset -- but staying byte-identical lets a new scrape be
# diffed straight against the old CSVs.
COLUMNS = ["name", "time", "team", "grade", "state", "date"]
PARTIAL_COLUMNS = ["page"] + COLUMNS + ["athlete_id"]

# A full rankings page parses to exactly 100 rows. Verified against every
# legacy leaderboard CSV (output/legacy/): CA 1600m is 15,371 rows over the 154 pages scrape.py
# hardcoded (153*100 + 71), NY 100m is 8,090 over the 81 pages scrape.py:77
# records (80*100 + 90), and CA 100m, NY 1600 and NY 800 agree exactly too. The
# arithmetic coming out exact also means parse_roster's spacer-row guard never
# fired on these lists, so a short page really is the last one.
PAGE_SIZE = 100

ROW_SEL = "#rankingsTable tbody.event-results tr[id]"
TABLE_SEL = "#rankingsTable"

# Confirmed against NY 2026 100m: without it page 1 opens
#   Johan-Ramaldo Smythe 10.24 JAM   and the state column is a mix of
#   "NY, USA" / "NJ, USA" / "JAM";
# with it page 1 opens
#   Kaeden Herbert 10.44 NY          and all 100 rows read "NY".
# That reproduces the legacy output/legacy/NY/m/100.csv vs 100r.csv pair exactly, down
# to Herbert's mark changing (10.43 -> 10.44) -- restrict drops performances set
# at out-of-state meets, not just out-of-state athletes.
#
# The name is not discoverable from the page source, so if athletic.net ever
# renames it the server will simply ignore the unknown parameter and hand back
# unrestricted data under an "...r.csv" name. The tell is the state column:
# a restricted list is uniformly one state.
RESTRICT_QUERY = "restrict=true"

# The URL segment and the filename differ: the list is .../m/1600m but the files
# are 1600.csv / 1600r.csv, with the metres implied. Anything not listed falls
# through to "drop a trailing m", which leaves 110mH and 4x100 alone.
#
# States do not agree on which metric mile they contest, and athletic.net keeps
# each as its own event, so the "same" race is a different slug per state:
# CT runs 1600m (1,319 marks), MA runs 1mile (its 1600m list holds 30), RI runs
# 1500m (its 1600m list holds 10). A nationwide distance sweep therefore needs
# either a per-state event or all three slugs run everywhere -- and the three are
# *different distances* (1500 / 1600 / 1609.34m), so their times cannot be pooled
# without conversion. "1mile" keeps the URL's own spelling, which makes the
# restricted file 1miler.csv.
EVENT_FILE = {"100m": "100", "200m": "200", "400m": "400",
              "800m": "800", "1500m": "1500", "1600m": "1600",
              "1mile": "1mile", "3200m": "3200"}


def check_slugs(events, allow_unknown=False) -> list[str]:
    """Refuse event slugs that are not confirmed (references/scraping.md §0, §8).

    athletic.net does not 404 a bad slug: it quietly serves a different event,
    or a real but tiny list, and the run "succeeds". A unit-less slug ("1600")
    is the classic case -- it is how 2026/WY/m/1600.csv came to exist. So every
    slug is checked against the confirmed list before a browser opens.
    --allow-unknown-slug skips this for a deliberate experiment; then verify
    one output file's times by eye before trusting the batch.
    """
    bad = [e for e in events if e not in EVENT_FILE]
    if bad and not allow_unknown:
        hint = [f"{e} (did you mean {e}m?)" if re.fullmatch(r"\d+", e) else e
                for e in bad]
        raise SystemExit(
            f"unconfirmed event slug(s): {', '.join(hint)}. Confirmed: "
            f"{', '.join(EVENT_FILE)}. A bad slug fails silently on "
            f"athletic.net; pass --allow-unknown-slug only to test a new one.")
    return bad

# Substrings that mean a challenge or throttle page rendered instead of the app.
# Lowercased; compared against a lowercased source.
BLOCK_MARKERS = ("just a moment", "cf-browser-verification", "attention required",
                 "access denied", "too many requests", "unusual traffic",
                 "checking your browser")

# What the rankings component renders in place of the table when it has nothing
# to show. Verified present on the page past the end of a list and absent from
# every page that has rows, which makes it the one definitive "end of list"
# signal -- see the zero-row branch of fetch_page for why that matters.
NO_RESULTS = "no results found"

# Rough cost of one page load: uc_open_with_reconnect's 2s, the 1s settle, and
# the inter-page jitter. Only used for the --dry-run estimate.
SECONDS_PER_PAGE = 4.0
PAGES_PER_JOB_GUESS = 50

# The ID CSV keys by full state name; the data tree uses abbreviations. Note the
# CSV's last row is literally "DC", not "District of Columbia".
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "DC": "DC",
}


class Blocked(RuntimeError):
    """A page could not be fetched after every retry -- stop the whole run.

    Skipping to the next job would be wrong: when athletic.net starts blocking,
    every following job fails too, so continuing burns the queue marking
    hundreds of jobs failed and deepens the block.
    """

    def __init__(self, job, page, verdict):
        super().__init__(f"{job.key} page {page}: {verdict}")
        self.job, self.page, self.verdict = job, page, verdict


class ParserBroken(Blocked):
    """Rows parsed but their marks did not -- the page markup has moved.

    A subclass of Blocked because the right move is the same (stop everything:
    every later job would be just as broken) but the advice is not. Waiting and
    rerunning fixes a rate-limit; it does nothing for a markup change. On
    2026-10-07 a full run wrote 36 files whose time column was entirely blank
    and marked every job done, because nothing checked that a parsed row
    actually carried a mark.
    """


# Most of a page's rows having no mark means the mark cell is no longer being
# read, not that those athletes have no time -- every row on a rankings list
# exists *because* of a mark. Half is far above anything real data produces and
# far below the 100% a parser break produces.
BLANK_MARK_LIMIT = 0.5

# Short-first-page guard (references/scraping.md section 2, 2026-10-08): five
# boys 800m lists came back as ONE page of 5 rows during a site hiccup, stopped
# as `duplicate`, and were marked done. A short single page looks exactly like
# a tiny list, so the guard does two things a tiny list survives and a hiccup
# does not: it re-fetches page 1 once (a hiccup rarely repeats), and it compares
# the list against the same state's other events in the ledger (the same
# schools field every event, so a 5-row 800m next to a 2,000-row 400m is a
# truncation, not a small state). Real tiny lists -- WY's 2-row boys mile --
# pass the re-fetch and only pick up an annotation.
SUSPECT_SIBLING_ROWS = 1000      # a sibling event this big ...
# ... only counts against events EVERY state contests. The mile distances are
# not among them: a state's off-distance mile list (OK's 1-row boys mile next
# to a 2,614-row 100m) is legitimately tiny, and flagging it would bury the
# real truncations in noise.
CORE_EVENTS = ("100m", "200m", "400m", "800m")
SHORT_FIRST_PAGE_WAIT = 10       # seconds before re-fetching page 1


def sibling_max_rows(ledger, job) -> int:
    """Largest finished list for the same year x state x sex, other events."""
    return max((int(v.get("rows") or 0) for k, v in ledger.data["jobs"].items()
                if k != job.key and v.get("status") == "done"
                and str(v.get("year")) == str(job.year)
                and v.get("abbr") == job.abbr and v.get("sex") == job.sex),
               default=0)


def short_list_flags(rows: int, pages: int, sibling_rows: int,
                     event: str) -> dict:
    """Ledger annotations for a finished list. Pure, so it is testable offline.

    short_list    -- the whole list is one page under PAGE_SIZE.
    suspect_short -- ... on a CORE_EVENTS event, while a sibling event of the
                     same state has more than SUSPECT_SIBLING_ROWS rows.
                     Rescrape it with --force.
    """
    short = pages == 1 and rows < PAGE_SIZE
    return {"short_list": short,
            "suspect_short": bool(short and event in CORE_EVENTS
                                  and sibling_rows > SUSPECT_SIBLING_ROWS)}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _tmp(path):
    return path.parent / (path.name + ".tmp")


def _replace(src, dst):
    """os.replace, retried: on Windows antivirus or an open editor can hold the
    target for a moment, and losing the ledger to that is the worst outcome in
    the design."""
    for attempt in range(3):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.2)


# ---------------------------------------------------------------------------
# 1. The state table -> the job matrix
# ---------------------------------------------------------------------------
def load_state_table(path):
    """The wide ',2026,2025' sheet as long rows of state/abbr/year/list_id."""
    raw = pd.read_csv(path, dtype=str)
    raw = raw.rename(columns={raw.columns[0]: "state"})
    raw["state"] = raw["state"].str.strip()

    table = raw.melt(id_vars="state", var_name="year", value_name="list_id")
    table["year"] = table["year"].str.strip().astype(int)
    table["list_id"] = table["list_id"].str.strip()
    table["abbr"] = table["state"].map(STATE_ABBR)

    # Fail loudly. A state silently dropped from the matrix is the worst bug
    # available here -- the run looks like it succeeded and the data is missing.
    unknown = sorted(table.loc[table["abbr"].isna(), "state"].unique())
    if unknown:
        raise SystemExit(f"no abbreviation for: {', '.join(unknown)}")
    return table


def resolve_states(table, wanted):
    """Abbreviations or full names, case-insensitively, or 'all'."""
    known = table[["state", "abbr"]].drop_duplicates()
    if any(w.lower() == "all" for w in wanted):
        return sorted(known["abbr"])

    by_name = {r.state.lower(): r.abbr for r in known.itertuples()}
    by_abbr = {r.abbr.lower(): r.abbr for r in known.itertuples()}
    picked, unknown = [], []
    for token in wanted:
        abbr = by_abbr.get(token.strip().lower()) or by_name.get(token.strip().lower())
        if abbr is None:
            unknown.append(token)
        elif abbr not in picked:
            picked.append(abbr)
    if unknown:
        raise SystemExit(f"unknown state(s): {', '.join(unknown)}")
    return picked


@dataclass(frozen=True)
class Job:
    abbr: str
    state: str
    year: int
    sex: str
    event: str
    list_id: str
    restrict: bool
    restrict_param: str

    @property
    def url(self):
        url = f"{BASE}/TrackAndField/rankings/list/{self.list_id}/{self.sex}/{self.event}"
        return f"{url}?{self.restrict_param}" if self.restrict else url

    @property
    def event_file(self):
        stem = EVENT_FILE.get(self.event, re.sub(r"m$", "", self.event))
        return stem + ("r" if self.restrict else "")

    @property
    def key(self):
        return f"{self.year}-{self.abbr}-{self.sex}-{self.event_file}"

    def out_path(self, root, template):
        return Path(root) / template.format(
            year=self.year, abbr=self.abbr, sex=self.sex, event_file=self.event_file)

    def partial_path(self, progress_dir):
        return Path(progress_dir) / "partial" / f"{self.key}.csv"

    def meta(self, out):
        return {"state": self.state, "abbr": self.abbr, "year": self.year,
                "sex": self.sex, "event": self.event, "restrict": self.restrict,
                "list_id": self.list_id, "url": self.url, "out": str(out)}


def build_jobs(table, states, years, sexes, events, restrict, restrict_param):
    """Every combination, in a stable order: year, sex, event, then state."""
    ids = {(r.abbr, r.year): (r.list_id, r.state) for r in table.itertuples()}
    jobs, missing = [], []
    for year in years:
        for sex in sexes:
            for event in events:
                for abbr in states:
                    found = ids.get((abbr, year))
                    if found is None:
                        missing.append(f"{abbr} {year}")
                        continue
                    list_id, state = found
                    jobs.append(Job(abbr, state, year, sex, event, list_id,
                                    restrict, restrict_param))
    if missing:
        raise SystemExit(f"no list id for: {', '.join(sorted(set(missing)))}")
    return jobs


# ---------------------------------------------------------------------------
# 2. The ledger
# ---------------------------------------------------------------------------
class Ledger:
    """Job statuses in one JSON file, rewritten atomically after every page.

    A hard kill therefore loses at most one page of bookkeeping, and the partial
    CSV is the real recovery record regardless.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.data = {"version": 1, "updated": None, "argv": sys.argv[1:], "jobs": {}}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as err:
                # Keep the corrupt file rather than silently starting over -- it
                # is the only record of what a long run already did.
                backup = self.path.with_name(self.path.name + ".corrupt")
                print(f"unreadable ledger ({type(err).__name__}) -> {backup}")
                self.path.replace(backup)
        self.data.setdefault("jobs", {})
        self.data["argv"] = sys.argv[1:]

    def entry(self, key):
        return self.data["jobs"].setdefault(key, {})

    def status(self, key):
        return self.data["jobs"].get(key, {}).get("status", "pending")

    def mark(self, key, **fields):
        entry = self.entry(key)
        entry.update(fields)
        entry["updated"] = now()
        self.save()

    def save(self):
        self.data["updated"] = now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = _tmp(self.path)
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        _replace(tmp, self.path)


# ---------------------------------------------------------------------------
# 3. Fetching one page
# ---------------------------------------------------------------------------
def page_rows(html):
    """parse_roster's rows projected onto the output columns."""
    return [{"name": r["name"], "time": r["rank_mark"], "team": r["team"],
             "grade": r["grade"], "state": r["state"], "date": r["rank_date"],
             "athlete_id": r["athlete_id"]}
            for r in parse_roster(html)]


def looks_blocked(html):
    low = html.lower()
    return any(marker in low for marker in BLOCK_MARKERS)


def fetch_page(sb, url, page, opts, timeout=None):
    """One page -> (rows, verdict) with verdict in {ok, empty, blocked, error}.

    Telling "the list ended" apart from "we got blocked" is the crux of the whole
    script. Both look like zero rows, and confusing them is the worst failure
    available: a rate-limit read as an ending writes a truncated CSV and marks
    the job done, which is invisible.
    """
    try:
        sb.uc_open_with_reconnect(page_url(url, page), 2)
    except Exception:
        return [], "error"

    try:
        sb.wait_for_element(ROW_SEL, timeout=timeout or opts.page_timeout)
    except Exception:
        # Not an error yet. Past the end of a list this *always* times out,
        # because an empty page never grows a tr[id].
        pass
    sb.sleep(1)

    try:
        html = sb.get_page_source()
    except Exception:
        return [], "error"

    if looks_blocked(html):
        return [], "blocked"

    rows = page_rows(html)
    if rows:
        return rows, "ok"

    # Zero rows, so this is either the end of the list or a failure, and the two
    # have to be told apart. Two independent signals say "end", cheapest first.
    #
    # 1. The component says so. Past the end of a list athletic.net does not
    #    render an empty table -- it drops the table element entirely and puts
    #    "No Results Found" in its place, on a ~115KB page (a page with rows is
    #    ~470KB). So a missing #rankingsTable does NOT mean nothing rendered, and
    #    treating it that way made every single-page list unscrapeable: the probe
    #    past the only page was called an error, retried three times, and aborted
    #    the entire run. Verified on DC 3200m (95 rows) and VT 3200m (21 rows).
    if NO_RESULTS in html.lower():
        return [], "empty"

    # 2. Failing that, a table that rendered with no rows in it also means the
    #    list is out of rows. Multi-page lists reach the end this way, because
    #    they clamp an out-of-range page back onto the last one instead (which
    #    the duplicate guard in run_job catches). is_element_present does not
    #    wait, so this is free.
    try:
        shell = sb.is_element_present(TABLE_SEL)
    except Exception:
        shell = False
    if not shell:
        # Nothing recognisable rendered: a slow paint, a soft block, or markup
        # that has moved again. Let the caller retry rather than quietly calling
        # it the end of the list, which would truncate the CSV and mark it done.
        return [], "error"
    if opts.min_bytes and len(html) < opts.min_bytes:
        return [], "error"
    return [], "empty"


def fetch_with_retries(sb, url, page, opts, timeout=None):
    """fetch_page, retried with backoff. Only ok/empty come back settled."""
    verdict = "error"
    for attempt in range(opts.page_retries):
        rows, verdict = fetch_page(sb, url, page, opts, timeout)
        if verdict in ("ok", "empty"):
            return rows, verdict
        if attempt == opts.page_retries - 1:
            break
        # A block is not a blip -- retrying a challenge five seconds later just
        # confirms it, so skip the short rungs of the ladder.
        step = attempt + 2 if verdict == "blocked" else attempt
        delay = opts.retry_delay * (2 ** step) * random.uniform(0.8, 1.3)
        print(f"    page {page}: {verdict}, retrying in {delay:.0f}s")
        sb.sleep(delay)
    return [], verdict


# ---------------------------------------------------------------------------
# 4. The partial file: accumulator and checkpoint in one
# ---------------------------------------------------------------------------
# Rows land on disk as they parse and nothing accumulates in memory, which also
# sidesteps scrape.py:71's growing pd.concat -- quadratic, and per
# individualScrape.py:464 no longer well defined on this venv's pandas 3.
def append_page(partial, rows, page):
    partial.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=PARTIAL_COLUMNS[1:])
    frame.insert(0, "page", page)
    # Size, not just existence: a kill can leave a zero-byte file behind, and
    # appending to that without a header would write a CSV whose first data row
    # gets read back as the column names.
    fresh = not partial.exists() or partial.stat().st_size == 0
    frame.to_csv(partial, mode="a", header=fresh, index=False)


def truncate_torn(partial):
    """Drop a half-written trailing line left by a kill mid-write."""
    data = partial.read_bytes()
    if not data or data.endswith(b"\n"):
        return
    cut = data.rfind(b"\n")
    tmp = _tmp(partial)
    tmp.write_bytes(data[:cut + 1] if cut != -1 else b"")
    _replace(tmp, partial)


def resume_point(partial):
    """-> (page to fetch next, athlete ids already banked).

    The highest page present is dropped and re-fetched unconditionally. A kill
    can land mid-append, so that page may be short; dropping it makes resume
    correct whether the kill tore a page or landed cleanly between two, without
    having to work out which happened. The cost is one repeated page.
    """
    if not partial.exists():
        return 1, set()
    if partial.stat().st_size == 0:
        partial.unlink()        # leave no empty file for append_page to find
        return 1, set()

    truncate_torn(partial)
    try:
        # read_csv, never a manual split: the state column legitimately contains
        # commas ("NY, USA" appears in output/legacy/NY/m/100.csv).
        frame = pd.read_csv(partial, dtype=str)
    except Exception as err:
        print(f"  unreadable partial ({type(err).__name__}) -- restarting the job")
        partial.unlink()
        return 1, set()

    if frame.empty or "page" not in frame.columns:
        partial.unlink()
        return 1, set()

    pages = frame["page"].astype(int)
    last = int(pages.max())
    kept = frame[pages < last]
    if kept.empty:
        partial.unlink()
        return 1, set()

    tmp = _tmp(partial)
    kept.to_csv(tmp, index=False)
    _replace(tmp, partial)
    return last, set(kept["athlete_id"].dropna().astype(str))


def finalize(job, opts, out):
    """Partial -> the real CSV. Row order is the leaderboard's; do not sort."""
    partial = job.partial_path(opts.progress_dir)
    frame = pd.read_csv(partial, dtype=str)
    frame = frame.drop_duplicates(subset=COLUMNS + ["athlete_id"], keep="first")
    frame = frame[COLUMNS + (["athlete_id"] if opts.keep_athlete_id else [])]

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp(out)
    frame.to_csv(tmp, index=False)
    _replace(tmp, out)          # the CSV appears complete or not at all
    partial.unlink()
    return len(frame)


# ---------------------------------------------------------------------------
# 5. One job
# ---------------------------------------------------------------------------
def run_job(sb, job, opts, ledger, _recheck=True):
    """Walk one list to its end. -> (stop_reason, pages fetched)."""
    key = job.key
    out = job.out_path(opts.out_root, opts.out_template)
    partial = job.partial_path(opts.progress_dir)

    page, seen = resume_point(partial)
    entry = ledger.entry(key)
    ledger.mark(key, **job.meta(out), status="running", last_error=None,
                attempts=int(entry.get("attempts", 0)) + 1,
                started=entry.get("started") or now())
    if page > 1:
        print(f"  resuming at page {page} ({len(seen):,} athletes banked)")

    fetched = 0
    short_page = False          # the previous page came back under PAGE_SIZE
    stop_reason = None
    last_page_rows = None

    while True:
        if page > opts.max_pages:
            stop_reason = "max-pages"
            break

        # A short page is almost certainly the last, so probe the next one with
        # a shorter timeout rather than waiting the full one on a page we expect
        # to be empty. Only the timeout changes -- the page is fetched either way.
        rows, verdict = fetch_with_retries(
            sb, job.url, page, opts, opts.probe_timeout if short_page else None)
        fetched += 1

        if verdict not in ("ok", "empty"):
            ledger.mark(key, status="failed", pages_done=page - 1,
                        stop_reason=verdict, last_error=f"page {page}: {verdict}")
            raise Blocked(job, page, verdict)

        if verdict == "empty":
            # Believe a zero only when it repeats. One extra load per job.
            sb.sleep(5)
            rows, verdict = fetch_with_retries(
                sb, job.url, page, opts, opts.probe_timeout)
            fetched += 1
            if verdict not in ("ok", "empty"):
                ledger.mark(key, status="failed", pages_done=page - 1,
                            stop_reason=verdict, last_error=f"page {page}: {verdict}")
                raise Blocked(job, page, verdict)
            if verdict == "empty":
                stop_reason = "short-page-confirmed" if short_page else "empty-page"
                break

        # If a page brings no athlete we have not already banked, the server
        # clamped an out-of-range page back onto an earlier one. Subset-of-seen
        # rather than equals-previous, so a clamp to *any* earlier page is caught.
        ids = {r["athlete_id"] for r in rows if r["athlete_id"]}
        if ids and ids <= seen:
            stop_reason = "duplicate"
            break

        # Checked after the clamp guard: on a clamping server every short page is
        # followed by rows, and blaming PAGE_SIZE for that would be noise. Getting
        # here means the rows were genuinely new, so the constant really is suspect.
        # Positive check on the one field everything downstream needs. A page
        # whose names parse but whose marks do not looks exactly like success
        # otherwise (see ParserBroken).
        blank = sum(not r["time"] for r in rows)
        if rows and blank > BLANK_MARK_LIMIT * len(rows):
            ledger.mark(key, status="failed", pages_done=page - 1,
                        stop_reason="blank-marks",
                        last_error=f"page {page}: {blank}/{len(rows)} rows without a mark")
            raise ParserBroken(job, page, f"blank-marks ({blank}/{len(rows)})")

        if short_page:
            print(f"    note: page {page - 1} was short but page {page} has new"
                  f" rows -- PAGE_SIZE={PAGE_SIZE} may be wrong")
            ledger.mark(key, short_page_contradicted=page - 1)

        append_page(partial, rows, page)
        seen |= ids
        last_page_rows = len(rows)
        ledger.mark(key, status="running", pages_done=page,
                    last_page_rows=last_page_rows)
        print(f"  page {page}: +{len(rows)} (total {len(seen):,})")

        short_page = last_page_rows < PAGE_SIZE
        page += 1
        sb.sleep(random.uniform(opts.min_delay, opts.max_delay))

    pages_done = page - 1
    if stop_reason == "max-pages":
        # A capped job is an incomplete job and has to stay visible.
        ledger.mark(key, status="failed", pages_done=pages_done,
                    stop_reason=stop_reason,
                    last_error=f"hit --max-pages {opts.max_pages}")
        return stop_reason, fetched

    if not partial.exists():
        ledger.mark(key, status="empty", pages_done=0, rows=0,
                    stop_reason=stop_reason, finished=now())
        return stop_reason, fetched

    # ---- short-first-page guard -------------------------------------
    # One page under PAGE_SIZE ended the list. Re-fetch page 1 once: if it now
    # has more rows, page 1 was a partial render, so throw the partial away and
    # walk the list again from the top.
    if (_recheck and pages_done == 1 and last_page_rows is not None
            and last_page_rows < PAGE_SIZE):
        sb.sleep(SHORT_FIRST_PAGE_WAIT)
        again, verdict = fetch_with_retries(sb, job.url, 1, opts)
        fetched += 1
        if verdict == "ok" and len(again) > last_page_rows:
            print(f"  page 1 was short ({last_page_rows} rows) but a re-fetch "
                  f"has {len(again)} -- partial render; restarting the list")
            partial.unlink(missing_ok=True)
            ledger.mark(key, short_first_page_refetched=last_page_rows)
            reason, more = run_job(sb, job, opts, ledger, _recheck=False)
            return reason, fetched + more

    rows_written = finalize(job, opts, out)
    flags = short_list_flags(rows_written, pages_done,
                             sibling_max_rows(ledger, job), job.event)
    if flags["suspect_short"]:
        print(f"  !! {rows_written} rows on one page while this state's other "
              f"events reach {sibling_max_rows(ledger, job):,}: probably "
              f"truncated. Rescrape with --force.")
    # The CSV lands before the ledger claims it: a crash in between leaves a
    # complete file and a running job, which the next pass re-finalizes cheaply.
    # The other order would claim done with no file.
    ledger.mark(key, status="done", pages_done=pages_done, rows=rows_written,
                last_page_rows=last_page_rows, stop_reason=stop_reason,
                finished=now(), **flags)
    print(f"  {rows_written:,} rows -> {out}")
    return stop_reason, fetched


# ---------------------------------------------------------------------------
# 6. The driver
# ---------------------------------------------------------------------------
def login(sb, url):
    """The tolerant block from individualScrape.capture, as a function.

    Unlike bios, deep rankings pages may well be gated -- scrape.py signs in for
    a reason -- so a failure is reported loudly rather than shrugged off.
    """
    creds = credentials()
    if creds is None:
        sb.uc_open_with_reconnect(url, 2)
        return False
    try:
        sb.uc_open_with_reconnect(url, 2)
        sb.uc_click("button.btn-primary.btn-lg")
        sb.type("//input[@id='email']", creds[0])
        sb.type("//input[@id='password']", creds[1])
        sb.click("//button[@class='athletic-auth-modal--button"
                 " athletic-auth-modal--continue']")
        sb.sleep(3)
        return True
    except Exception as err:
        print(f"login step failed ({type(err).__name__})")
        return False


def should_run(job, ledger, opts):
    entry = ledger.data["jobs"].get(job.key, {})
    status = entry.get("status", "pending")
    if status in ("done", "skipped"):
        return False
    if status in ("failed", "empty") and not opts.retry_failed:
        return False
    if status != "pending" and int(entry.get("attempts", 0)) >= opts.max_attempts:
        return False
    return True


def prepare(jobs, opts, ledger):
    """Adopt pre-existing CSVs, and honour --force, before anything opens.

    Under --dry-run nothing is deleted or saved: --force only reports what it
    WOULD delete. (Before 2026-10-09 the deletion ran before the dry-run check,
    so `--dry-run --force` really destroyed files.)
    """
    would_delete = []
    for job in jobs:
        out = job.out_path(opts.out_root, opts.out_template)
        partial = job.partial_path(opts.progress_dir)

        if opts.force:
            # Scoped to the jobs the filters selected, so --force --states WY
            # cannot touch anything else.
            for path in (out, partial):
                if path.exists():
                    if opts.dry_run:
                        would_delete.append(path)
                    else:
                        path.unlink()
            if not opts.dry_run:
                ledger.data["jobs"].pop(job.key, None)
            continue

        if out.exists() and job.key not in ledger.data["jobs"]:
            ledger.entry(job.key).update(
                **job.meta(out), status="skipped", stop_reason="pre-existing",
                attempts=0, updated=now())
    if would_delete:
        print(f"--dry-run: --force WOULD delete {len(would_delete)} file(s), "
              f"e.g. {would_delete[0]}")
    if not opts.dry_run:
        ledger.save()


def run_batch(jobs, opts, ledger):
    """One browser, run until a recycle trigger. -> reason."""
    pages = 0
    with SB(uc=True) as sb:
        if not login(sb, jobs[0].url):
            print("continuing signed out -- deep pages may be gated")
        try:
            for n, job in enumerate(jobs, 1):
                print(f"\n[{job.key}] {job.url}")
                reason, got = run_job(sb, job, opts, ledger)
                pages += got
                print(f"  -> {reason}")
                if pages >= opts.pages_per_session and n < len(jobs):
                    return "page-budget"
            return "batch-done"
        finally:
            ledger.save()


def run_all(jobs, opts, ledger):
    """Recycle the browser between batches until the queue empties.

    The queue is recomputed from the ledger each pass rather than mutated, which
    keeps --retry-failed and mid-run status changes coherent.
    """
    last_attempts = None
    while True:
        queue = [j for j in jobs if should_run(j, ledger, opts)]
        if not queue:
            return
        # A browser held open across hundreds of jobs accumulates state, and job
        # sizes vary tenfold (Wyoming 1600m is a few pages, CA 100m is ~251), so
        # a job count alone is a poor recycle trigger. Whichever trips first.
        batch = queue[:opts.jobs_per_session]
        print(f"\n=== {len(queue)} job(s) left; running {len(batch)} this session")
        run_batch(batch, opts, ledger)

        # Every started job increments attempts, so a pass that advances nothing
        # means the queue can never drain. Bail rather than spin.
        attempts = sum(int(e.get("attempts", 0)) for e in ledger.data["jobs"].values())
        if attempts == last_attempts:
            print("no progress this pass -- stopping")
            return
        last_attempts = attempts


def dump_html(job, dest, opts):
    """Save one rankings page, and probe an out-of-range one.

    This is the investigation the restrict parameter and the clamp guard both
    hang on: it reports whether the table shell id is right, how big a rendered
    page is (to calibrate --min-bytes), and whether ?page=9999 comes back empty
    or clamped back onto real rows.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with SB(uc=True) as sb:
        login(sb, job.url)
        rows, verdict = fetch_page(sb, job.url, 1, opts)
        html = sb.get_page_source()
        dest.write_text(html, encoding="utf-8")

        print(f"\n{job.url}")
        print(f"  page 1: {len(html):,} bytes, {len(rows)} rows, verdict={verdict}")
        print(f"  rows without a mark: {sum(not r['time'] for r in rows)}"
              f"  (first mark: {rows[0]['time'] if rows else '-'!r})")
        print(f"  {TABLE_SEL} present: {sb.is_element_present(TABLE_SEL)}")
        print(f"  saved -> {dest}")

        far, far_verdict = fetch_page(sb, job.url, 9999, opts, opts.probe_timeout)
        print(f"  page 9999: {len(far)} rows, verdict={far_verdict}")
        if far:
            print("  -> this list CLAMPS out-of-range pages back onto real rows;"
                  " the duplicate guard is what ends the job")
        else:
            print(f"  -> out-of-range pages come back {far_verdict!r};"
                  " the empty-page sentinel is what ends the job")
            if far_verdict == "error":
                print("     WARNING: that should be 'empty'. A list whose end"
                      " reads as an error cannot be scraped -- check whether the"
                      " NO_RESULTS marker still matches the page.")
    print("\nNow read the saved HTML for a result count or pagination control,"
          "\nand toggle 'restrict' in a browser to read RESTRICT_QUERY off the URL.")


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------
def csv_list(value):
    return [token.strip() for token in value.split(",") if token.strip()]


def summarize(jobs, ledger):
    counts = {}
    for job in jobs:
        status = ledger.status(job.key)
        counts[status] = counts.get(status, 0) + 1
    print("\n" + "  ".join(f"{status}={n}" for status, n in sorted(counts.items())))

    stuck = [j.key for j in jobs if ledger.status(j.key) == "failed"]
    if stuck:
        tail = "  ..." if len(stuck) > 10 else ""
        print(f"failed: {', '.join(stuck[:10])}{tail}")
        print("rerun with --retry-failed once the block has cleared")


def main():
    p = argparse.ArgumentParser(
        description="Scrape athletic.net rankings across states, resumably.")
    p.add_argument("--states", type=csv_list, required=True,
                   help="abbreviations or full names, or 'all'")
    p.add_argument("--years", type=csv_list, required=True,
                   help="comma list; must be columns in the state CSV")
    p.add_argument("--sex", type=csv_list, required=True, help="m, f, or m,f")
    p.add_argument("--events", type=csv_list, required=True,
                   help="athletic.net URL slugs, e.g. 100m,800m,1600m")

    p.add_argument("--no-restrict", action="store_true",
                   help="drop the restrict parameter and the r suffix")
    p.add_argument("--restrict-param", default=RESTRICT_QUERY,
                   help=f"restrict query string (default: {RESTRICT_QUERY})")
    # Defaults are anchored on the repo (src/paths.py), not the cwd, so the
    # scraper can be launched from anywhere and still resume the same ledger.
    p.add_argument("--state-csv", type=Path, default=STATE_ID_CSV)
    p.add_argument("--out-root", type=Path, default=SCRAPE_OUT)
    p.add_argument("--out-template", default="{year}/{abbr}/{sex}/{event_file}.csv")
    p.add_argument("--progress-dir", type=Path, default=None,
                   help="default: <out-root>/_progress")

    p.add_argument("--max-pages", type=int, default=400,
                   help="hard cap per job (default: 400; CA 100m is ~251)")
    p.add_argument("--page-retries", type=int, default=3)
    p.add_argument("--retry-delay", type=float, default=5.0)
    p.add_argument("--min-delay", type=float, default=0.75)
    p.add_argument("--max-delay", type=float, default=2.0)
    p.add_argument("--page-timeout", type=float, default=20)
    p.add_argument("--probe-timeout", type=float, default=6,
                   help="shorter wait for a page expected to be empty")
    p.add_argument("--min-bytes", type=int, default=0,
                   help="treat a smaller page source as unrendered; 0 disables."
                        " Calibrate from --dump-html before turning this on")
    p.add_argument("--jobs-per-session", type=int, default=5)
    p.add_argument("--pages-per-session", type=int, default=500)
    p.add_argument("--max-attempts", type=int, default=3)

    p.add_argument("--retry-failed", action="store_true",
                   help="re-queue failed and empty jobs")
    p.add_argument("--force", action="store_true",
                   help="redo selected jobs already done, deleting their CSVs")
    p.add_argument("--keep-athlete-id", action="store_true",
                   help="keep athlete_id in the output (joins to individualScrape)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the job matrix and a time estimate, then exit")
    p.add_argument("--allow-unknown-slug", action="store_true",
                   help="skip the confirmed-slug check (verify the output by eye)")
    p.add_argument("--dump-html", type=Path, default=None,
                   help="save the first job's page source and probe pagination")
    opts = p.parse_args()
    check_slugs(opts.events, opts.allow_unknown_slug)

    opts.progress_dir = opts.progress_dir or opts.out_root / "_progress"

    table = load_state_table(opts.state_csv)
    known_years = sorted(table["year"].unique())
    try:
        years = [int(y) for y in opts.years]
    except ValueError:
        raise SystemExit(f"--years must be integers; known: {known_years}")
    unknown = [y for y in years if y not in known_years]
    if unknown:
        raise SystemExit(f"no column for year(s) {unknown}; known: {known_years}")

    states = resolve_states(table, opts.states)
    jobs = build_jobs(table, states, years, opts.sex, opts.events,
                      not opts.no_restrict, opts.restrict_param)

    if opts.dump_html:
        dump_html(jobs[0], opts.dump_html, opts)
        return

    ledger = Ledger(opts.progress_dir / "progress.json")
    prepare(jobs, opts, ledger)

    if opts.dry_run:
        for job in jobs[:20]:
            print(f"{job.key:<22} {ledger.status(job.key):<9}"
                  f" {job.out_path(opts.out_root, opts.out_template)}")
        if len(jobs) > 20:
            print(f"... and {len(jobs) - 20} more")

        # --force would reset every selected job, so all of them would run.
        pending = (list(jobs) if opts.force
                   else [j for j in jobs if should_run(j, ledger, opts)])
        loads = len(pending) * PAGES_PER_JOB_GUESS
        print(f"\n{len(jobs)} job(s), {len(pending)} to run")
        print(f"~{loads:,} page loads, roughly"
              f" {loads * SECONDS_PER_PAGE / 3600:.1f} hours"
              f" at {SECONDS_PER_PAGE:.0f}s/page")
        print(f"first URL: {jobs[0].url}")
        return

    try:
        run_all(jobs, opts, ledger)
    except ParserBroken as err:
        ledger.save()
        print(f"\nstopped at {err.job.key} page {err.page}: {err.verdict}.")
        print("rows parsed but their marks did not -- athletic.net has probably"
              " changed the mark cell (td[7]).")
        print("rerunning will not help. Save a page with --dump-html, inspect"
              " td[7], and fix _rank_mark in individualScrape.py.")
        summarize(jobs, ledger)
        raise SystemExit(3)
    except Blocked as err:
        ledger.save()
        print(f"\nblocked at {err.job.key} page {err.page} ({err.verdict}).")
        print("progress is saved -- rerun the same command later to resume.")
        summarize(jobs, ledger)
        raise SystemExit(2)
    except KeyboardInterrupt:
        ledger.save()
        print("\ninterrupted -- progress is saved; rerun to resume.")
        raise SystemExit(130)

    summarize(jobs, ledger)


if __name__ == "__main__":
    main()
