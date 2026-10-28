#!/usr/bin/env python3
"""
Scrape the full performance history of the top N athletes on an athletic.net
rankings list.

scrape.py (now _archive/scrape.py; scrapeAll.py is its successor) produces one row per athlete -- their season best -- which is enough
to fit the whole field against date but says nothing about any single athlete,
since each appears exactly once. This walks the same leaderboard, follows the
athlete link each row already carries, and records *every* mark on that bio:
all events, all season types, all years, track and cross country. The result is
a longitudinal panel, so seconds can be regressed against date per athlete.

Two phases, because the bio page's markup is only knowable by looking at it:

    capture   log in, download the top N athletes' bio pages, cache the raw HTML
    parse     turn the cached HTML into one tidy long CSV, no network involved

--capture does only the first, --parse-only only the second, neither flag does
both. Capture skips athletes already in the cache, so an interrupted run resumes
for free and the parser can be rewritten without re-scraping anything.

    python stages/01_scrape/individualScrape.py --top 3 --capture      # smoke test
    python stages/01_scrape/individualScrape.py --top 100 --capture    # fill the cache
    python stages/01_scrape/individualScrape.py --parse-only           # iterate on the parser

Cache and output land in this stage's output/ (html/<list>/, individual/<list>.csv)
wherever the script is launched from.
"""

import argparse
import os
import random
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from lxml import etree
from seleniumbase import SB

# Shared helpers (paths, time parsing) live in <repo>/src -- see CLAUDE.md.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from paths import HTML_CACHE, INDIVIDUAL
# Lives in src/util.py (it used to be imported from plotByDate, which dragged a
# plotting script and matplotlib into every scrape).
from util import parse_time

BASE = "https://www.athletic.net"
DEFAULT_URL = "https://www.athletic.net/TrackAndField/rankings/list/168546/m/1600m"

# Credentials come ONLY from the environment: export ATHLETIC_EMAIL and
# ATHLETIC_PASSWORD before a run. There used to be a hardcoded fallback pair
# here, which put a live password in plain text in every copy of the repo.
# Missing values are not an import error -- plenty of runs never log in
# (--dry-run, bios, which are public) -- they surface at login time instead,
# through credentials().
EMAIL = os.environ.get("ATHLETIC_EMAIL", "")
PASSWORD = os.environ.get("ATHLETIC_PASSWORD", "")


def credentials() -> tuple[str, str] | None:
    """(email, password) from the environment, or None with a clear message."""
    if EMAIL and PASSWORD:
        return EMAIL, PASSWORD
    print("  no athletic.net credentials: export ATHLETIC_EMAIL and "
          "ATHLETIC_PASSWORD to sign in.\n  Continuing signed out.")
    return None

# A bio that rendered is a few hundred KB. Anything near the Angular shell's size
# means the page 404'd, was rate-limited, or never finished loading -- worth
# flagging, though the file is still written so it can be inspected.
MIN_BIO_BYTES = 40_000

# Track and cross country are separate bios; "everything" needs both.
SPORTS = {"tf": "track-and-field", "xc": "cross-country"}

# The trailing path segment filters a bio by the level the athlete competed at.
# "high-school" drops anything raced unattached or with a club, which on a
# distance runner's bio is most of the indoor season; "all" keeps everything.
LEVEL = "all"

# The results tbody, reached by the table's id and the tbody's class rather than
# by position. scrape.py's spine, which this used to copy, was absolute:
#     /html/body/main/anet-site-app/shared-tf-rankings/div/div/div[2]/div[2]/table/tbody[2]
# A wrapper div has since moved, and the live page is now
#     ...                                              /div/div/div[2]/div[1]/table/tbody[2]
# so that path matched nothing. It failed in the worst possible way: a rankings
# page that parses to zero rows is indistinguishable from the end of a list, so
# the scrape looks like it finished instead of like it broke. Anchoring on the id
# survives any amount of wrapper reshuffling. The per-column /td[N] suffixes below
# are unchanged -- the column layout itself is the same.
TBODY = "//table[@id='rankingsTable']//tbody[contains(@class,'event-results')]"
ROWS = TBODY + "//tr"
ROW = TBODY + "/tr[{i}]"


# ---------------------------------------------------------------------------
# 1. The rankings page -> who to visit
# ---------------------------------------------------------------------------
def _text(node, default=""):
    """Stripped text of an lxml node, tolerating both None and an empty node."""
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _cell(dom, i, suffix):
    """First node at row i + suffix, or None when that cell is absent."""
    found = dom.xpath(ROW.format(i=i) + suffix)
    return found[0] if found else None


# A mark as it appears in the cell: '10.44', '3:49.83', '1:02:03.4', optionally
# with a one-letter annotation ('10.5h' hand-timed, '10.31a' altitude).
_MARK_RE = re.compile(r"(?:\d+:)*\d+(?:\.\d+)?[A-Za-z]?")


def _rank_mark(dom, i):
    """The mark in td[7], found by what it is rather than where it sits.

    This used to walk the cell by position -- cell[0][0].text, or cell[1].text
    when a badge added children (scrape.py:26-29) -- and swallow any IndexError
    into "". Between the 2026-09-13 and 2026-10-07 scrapes athletic.net wrapped
    the mark one level deeper, as
        td > div > span.me-1 > a[href='/result/...'] > span '3:49.83'
    so cell[0][0] landed on the <a>, whose own .text is whitespace. Every mark
    came back "" while names, teams and dates were fine, and the run reported
    success: the cell-level twin of the zero-rows XPath bug in scraping.md §2.

    Now: the mark is the text of the cell's link to its /result/ page. That
    link holds the mark and nothing else; the wind reading ' (0.2)' is a
    sibling span outside it. If the link ever disappears, fall back to the
    first mark-shaped token in the whole cell with parenthesised text (wind)
    removed. A genuinely blank result is still "", and scrapeAll's blank-marks
    guard stops the run if that happens to most of a page.
    """
    links = dom.xpath(ROW.format(i=i) + "/td[7]//a[contains(@href,'/result/')]")
    if links:
        text = "".join(links[0].itertext()).strip()
        found = _MARK_RE.search(text)
        if found:
            return found.group(0)

    cell = _cell(dom, i, "/td[7]")
    if cell is None:
        return ""
    text = re.sub(r"\([^)]*\)", " ", "".join(cell.itertext()))
    found = _MARK_RE.search(text)
    return found.group(0) if found else ""


def parse_roster(html):
    """Read one rankings page into athlete metadata rows, athlete link included.

    parse_rankings() in scrape.py reads td[5]'s anchor for its text and throws
    the href away. The href is the whole point here, so this keeps both.
    """
    dom = etree.HTML(str(BeautifulSoup(html, "lxml")))
    rows = []
    for i in range(1, len(dom.xpath(ROWS)) + 1):
        tr = dom.xpath(ROW.format(i=i))
        # scrape.py:22's guard: the table interleaves short spacer/ad rows
        # between results.
        if not tr or len(tr[0]) <= 3:
            continue

        link = _cell(dom, i, "/td[5]/div[1]/a[1]")
        if link is None:
            continue
        href = link.get("href") or ""
        found = re.search(r"/athlete/(\d+)", href)
        if not found:
            continue

        rows.append({
            "athlete_id": found.group(1),
            "name": _text(link),
            "team": _text(_cell(dom, i, "/td[15]/a[1]"), "Unattached"),
            "grade": _text(_cell(dom, i, "/td[12]")),
            "state": _text(_cell(dom, i, "/td[10]")),
            "rank_mark": _rank_mark(dom, i),
            "rank_date": _text(_cell(dom, i, "/td[16]")),
            "href": href,
        })
    return rows


def page_url(url, page):
    """Append ?page=N, or &page=N when the list URL already has a query."""
    return f"{url}{'&' if '?' in url else '?'}page={page}"


def collect_athletes(sb, url, top_n):
    """Walk the leaderboard until top_n athletes are in hand.

    A rankings page holds ~100 rows, so --top 100 costs exactly one page load.
    """
    rows, page = [], 1
    while len(rows) < top_n:
        sb.uc_open_with_reconnect(page_url(url, page), 2)
        sb.wait_for_element("#rankingsTable tbody.event-results tr[id]")
        sb.sleep(1)

        found = parse_roster(sb.get_page_source())
        if not found:
            print(f"  page {page}: no rows -- stopping short at {len(rows)}")
            break
        rows.extend(found)
        print(f"  page {page}: +{len(found)} (total {len(rows)})")

        page += 1
        sb.sleep(random.uniform(.75, 2))

    roster = pd.DataFrame(rows).head(top_n).reset_index(drop=True)
    roster.insert(0, "rank", range(1, len(roster) + 1))
    return roster


# ---------------------------------------------------------------------------
# 2. The bio pages -> cached HTML
# ---------------------------------------------------------------------------
def bio_url(athlete_id, sport, level=LEVEL):
    """The whole-career view for one sport.

    The href in the rankings table can be school- or season-scoped; this
    canonical form lists every season the athlete has results for.
    """
    return f"{BASE}/athlete/{athlete_id}/{SPORTS[sport]}/{level}"


def cache_path(cache_dir, athlete_id, sport):
    """Track bios are '<id>.html', cross country '<id>-xc.html'."""
    suffix = "" if sport == "tf" else "-" + sport
    return cache_dir / f"{athlete_id}{suffix}.html"


def capture_bio(sb, athlete_id, sport, cache_dir):
    """Download one bio page into the cache. Returns the byte count written."""
    sb.uc_open_with_reconnect(bio_url(athlete_id, sport), 2)
    try:
        sb.wait_for_element("main", timeout=20)
    except Exception:
        pass                       # save whatever rendered; the size check flags it
    sb.sleep(2)

    # Seasons far down a long bio only render once scrolled into view.
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    sb.sleep(1.5)

    html = sb.get_page_source()
    path = cache_path(cache_dir, athlete_id, sport)
    path.write_text(html, encoding="utf-8")
    return len(html)


def capture(url, top_n, cache_dir, roster_path, force, sports):
    """Log in, build the roster, and cache every athlete's bio page(s)."""
    with SB(uc=True) as sb:
        sb.uc_open_with_reconnect(url, 2)

        # Verbatim from scrape.py:61-64. Tolerated if it fails: bios are public,
        # and the top 100 live on page 1, which renders signed out.
        creds = credentials()
        try:
            if creds is None:
                raise RuntimeError("no credentials")
            sb.uc_click("button.btn-primary.btn-lg")
            sb.type("//input[@id='email']", creds[0])
            sb.type("//input[@id='password']", creds[1])
            sb.click("//button[@class='athletic-auth-modal--button"
                     " athletic-auth-modal--continue']")
            sb.sleep(3)
        except Exception as err:
            print(f"login step failed ({type(err).__name__}) -- continuing signed out")

        print(f"collecting the top {top_n} from {url}")
        roster = collect_athletes(sb, url, top_n)
        roster.to_csv(roster_path, index=False)
        print(f"roster -> {roster_path}  ({len(roster)} athletes)\n")

        missing = []
        try:
            for row in roster.itertuples():
                for sport in sports:
                    tag = f"[{row.rank:>3}] {row.name} ({sport})"
                    if cache_path(cache_dir, row.athlete_id, sport).exists() and not force:
                        print(f"  {tag}: cached")
                        continue
                    try:
                        size = capture_bio(sb, row.athlete_id, sport, cache_dir)
                    except Exception as err:
                        print(f"  {tag}: FAILED {type(err).__name__}")
                        missing.append(
                            f"{row.athlete_id}\t{sport}\t{row.name}\t{type(err).__name__}")
                        continue
                    flag = "   <-- suspiciously small" if size < MIN_BIO_BYTES else ""
                    print(f"  {tag}: {size:,} bytes{flag}")
                    sb.sleep(random.uniform(.75, 2))
        finally:
            if missing:
                (cache_dir / "missing.txt").write_text("\n".join(missing), encoding="utf-8")
                print(f"\n{len(missing)} bios failed -> {cache_dir / 'missing.txt'}")


# ---------------------------------------------------------------------------
# 3. Cached HTML -> performance rows
# ---------------------------------------------------------------------------
# A track header reads '2026 Outdoor ...'; a cross country one is just
# '2025 Bellarmine College Prep HS ...', with the sport implied by the page.
#
# Not anchored to the start: when a team has no logo its initials render as text
# in front of the year, giving 'AV 2026 Outdoor Ausable Valley Central HS 10th
# Grade'. Anchoring silently dropped every card for those athletes -- 6.7% of the
# New York rows. Searching for the first 20xx instead is safe, because the season
# year always precedes the team name in this header.
SEASON_RE = re.compile(r"\b(20\d{2})(?:\s+(Outdoor|Indoor))?\b", re.I)
SEASON_GRADE_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+Grade", re.I)
DATE_RE = re.compile(r"^[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}$")
DAY_RE = re.compile(r"^[A-Za-z]{3,9}\s+\d{1,2}$")
ROUND_CODES = {"F", "P", "S", "Q"}

# Marks in these events are distances, not times, and share the same tables.
FIELD_WORDS = ("jump", "vault", "put", "throw", "discus", "javelin",
               "hammer", "weight", "shot")
# SS.ss / M:SS.ss / H:MM:SS.ss, plus the odd FAT/hand-timing letter.
TIME_RE = re.compile(r"^\d{1,3}(?::\d{2}){0,2}(?:\.\d+)?[a-zA-Z]?$")


def mark_seconds(event, mark):
    """Seconds for a running mark; NaN for a field mark, which shares the table.

    Both checks earn their place: the event name catches a metric field mark
    like '12.45m', which is shaped exactly like a sprint time, and the shape
    check catches a feet-inches mark like '20-11.25' in an event whose name is
    not in FIELD_WORDS. Without them parse_time strips the punctuation and
    returns a confident, meaningless number.
    """
    if any(word in event.lower() for word in FIELD_WORDS):
        return np.nan
    if not TIME_RE.match(mark.strip()):
        return np.nan
    return parse_time(mark)


def split_division(raw):
    """'Var F' -> ('Var', 'F'). The round code is optional, the division is not."""
    parts = raw.split()
    if parts and parts[-1].upper() in ROUND_CODES:
        return " ".join(parts[:-1]), parts[-1].upper()
    return raw, ""


def parse_season_header(card, sport):
    """Pull year, season type, team and grade out of a season card's <h5>.

    A track header reads '2026 Outdoor Bellarmine College Prep HS 18 12th Grade'.
    A cross country one names no season type at all, so the sport whose page
    this is supplies it. Grade is worth keeping separately from the roster's:
    the roster has the athlete's grade now, this has their grade in the season
    the mark was actually run.
    """
    header = card.find("h5")
    if header is None:
        return None
    text = " ".join(header.get_text(" ", strip=True).split())

    season = SEASON_RE.search(text)
    if season is None:
        return None
    grade = SEASON_GRADE_RE.search(text)
    team = header.select_one('a[href*="/team/"]')

    return {
        "season_year": int(season.group(1)),
        "season_type": season.group(2).title() if season.group(2) else
                       ("Cross Country" if sport == "xc" else "Outdoor"),
        "season_team": team.get_text(" ", strip=True) if team else "Unattached",
        "season_grade": grade.group(1) if grade else "",
    }


def parse_result_row(tr, event, season):
    """One <tr result-id> -> one performance dict.

    Cells are found by what they contain rather than by position, so a column
    added or reordered upstream costs one field instead of the whole row.
    """
    tds = tr.find_all("td", recursive=False)

    # Track rows use shared-result-and-comment-tf, cross country -xc.
    mark_cell = tr.find(lambda t: t.name.startswith("shared-result-and-comment"))
    if mark_cell is None:
        return None
    # The mark sits in the anchor; a PB/SB badge sits outside it, in the cell.
    link = mark_cell.find("a")
    mark = (link or mark_cell).get_text(" ", strip=True)
    if not mark:
        return None

    date_raw = ""
    for td in tds:
        text = " ".join(td.get_text(" ", strip=True).split())
        if DATE_RE.match(text) or DAY_RE.match(text):
            date_raw = text
            break

    # Track rows date themselves ('Mar 18, 2026'); cross country rows give only
    # 'Oct 24' and take their year from the season. The branch has to be explicit
    # -- pd.to_datetime('Oct 24') returns year 1 rather than NaT, so leaning on a
    # NaT check here would write 0001-10-24 into every cross country row.
    if DATE_RE.match(date_raw):
        date = pd.to_datetime(date_raw, errors="coerce")
    elif DAY_RE.match(date_raw):
        date = pd.to_datetime(f"{date_raw} {season['season_year']}", errors="coerce")
    else:
        date = pd.NaT

    meet = tr.select_one('a[href*="/meet/"]')
    meet_id = re.search(r"/meet/(\d+)", meet["href"]) if meet else None

    end_cell = tr.select_one("td.text-end")
    division, round_ = split_division(
        " ".join(end_cell.get_text(" ", strip=True).split()) if end_cell else "")

    return {
        **season,
        "event": event,
        "mark": mark,
        "seconds": mark_seconds(event, mark),
        "place": tds[0].get_text(" ", strip=True) if tds else "",
        "division": division,
        "round": round_,
        "date": date.date().isoformat() if pd.notna(date) else "",
        "date_raw": date_raw,
        "meet": meet.get_text(" ", strip=True) if meet else "",
        "meet_id": meet_id.group(1) if meet_id else "",
        "result_id": tr.get("result-id", ""),
    }


def parse_bio(html, meta, sport):
    """One athlete's cached bio -> a list of performance rows.

    The page nests as: a card per season, each holding one table whose rows are
    either an event header (an <h5> in a full-width cell) or a result carrying a
    result-id. Walking the rows in order lets the most recent header label the
    results that follow it.
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("shared-athlete-bio-results div.card")
    if not cards:
        # Fall back to any card holding results, in case the wrapper is renamed
        # or cross country uses a component of its own.
        cards = [c for c in soup.select("div.card") if c.select_one("tr[result-id]")]

    rows = []
    for card in cards:
        season = parse_season_header(card, sport)
        if season is None:
            continue

        event = ""
        for tr in card.select("tr"):
            if not tr.has_attr("result-id"):
                heading = tr.find("h5")
                if heading is not None:
                    event = " ".join(heading.get_text(" ", strip=True).split())
                continue
            row = parse_result_row(tr, event, season)
            if row:
                rows.append({
                    "athlete_id": meta.athlete_id,
                    "name": meta.name,
                    "rank": meta.rank,
                    "team": meta.team,
                    "state": meta.state,
                    "grade": meta.grade,
                    **row,
                })
    return rows


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
COLUMNS = ["athlete_id", "name", "rank", "team", "state", "grade",
           "season_year", "season_type", "season_team", "season_grade",
           "event", "mark", "seconds", "place", "division", "round",
           "date", "date_raw", "meet", "meet_id", "result_id"]


def slug(url):
    """Stable directory name for one rankings list: '168546-m-1600m'."""
    return "-".join(re.findall(r"[^/?#]+", url.split("?")[0])[-3:])


def parse_cache(cache_dir, roster_path, out, sports):
    """Turn every cached bio into one tidy long CSV. Touches no network."""
    if not roster_path.exists():
        raise SystemExit(f"no roster at {roster_path} -- run --capture first")
    roster = pd.read_csv(roster_path, dtype={"athlete_id": str, "grade": str})

    frames, empty = [], []
    for meta in roster.itertuples():
        rows = []
        for sport in sports:
            path = cache_path(cache_dir, meta.athlete_id, sport)
            if path.exists():
                rows.extend(parse_bio(path.read_text(encoding="utf-8"), meta, sport))
        if rows:
            frames.append(pd.DataFrame(rows))
        else:
            empty.append(f"{meta.name} ({meta.athlete_id})")

    if not frames:
        raise SystemExit("no performances parsed")

    # One concat at the end. Growing a frame per athlete, the way scrape.py:71
    # does, is quadratic and no longer well defined on this venv's pandas 3.
    df = pd.concat(frames, ignore_index=True)[COLUMNS]
    df = df.sort_values(["rank", "date"]).reset_index(drop=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"{len(df):,} performances from {df['athlete_id'].nunique()} athletes -> {out}")
    if empty:
        print(f"{len(empty)} athletes yielded nothing: {', '.join(empty[:10])}")
    return df


def main():
    p = argparse.ArgumentParser(
        description="Scrape full performance histories for the top N ranked athletes.")
    p.add_argument("--url", default=DEFAULT_URL, help="rankings list URL")
    p.add_argument("--top", type=int, default=100, help="how many athletes (default: 100)")
    p.add_argument("--cache", type=Path, help="HTML cache dir (default: <stage output>/html/<list>)")
    p.add_argument("--out", type=Path, help="output CSV (default: <stage output>/individual/<list>.csv)")
    p.add_argument("--capture", action="store_true", help="fetch and cache only, never parse")
    p.add_argument("--parse-only", action="store_true",
                   help="reparse the cache, never open a browser")
    p.add_argument("--force", action="store_true", help="re-download bios already cached")
    p.add_argument("--no-xc", action="store_true", help="skip cross country, track only")
    args = p.parse_args()

    name = slug(args.url)
    cache_dir = args.cache or HTML_CACHE / name
    out = args.out or INDIVIDUAL / f"{name}.csv"
    roster_path = cache_dir / "roster.csv"
    sports = ["tf"] if args.no_xc else ["tf", "xc"]

    if not args.parse_only:
        cache_dir.mkdir(parents=True, exist_ok=True)
        capture(args.url, args.top, cache_dir, roster_path, args.force, sports)

    if not args.capture:
        parse_cache(cache_dir, roster_path, out, sports)


if __name__ == "__main__":
    main()
