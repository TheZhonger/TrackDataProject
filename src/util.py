"""
util.py
=======
Small helpers shared by more than one stage, so no stage has to import another
stage's script to get them.

parse_time and seconds_formatter used to live in plotByDate.py. The scraper
(stage 01) imported parse_time from there, which made scraping depend on a
plotting script and pulled matplotlib in on every scrape. They are moved here
verbatim; plotByDate re-imports them, so `from plotByDate import ...` still works.

Note this parse_time is the lenient one (strips any non-digit/colon/dot). The
GPD scripts in stages 03 and 04 keep their own stricter copies that refuse
"2:05,4" rather than misreading it -- see _config/data_conventions.md.
"""

import re
from datetime import date

import numpy as np

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def parseDate(day):
    """Convert a 'May 16' style string into a date in the current year.

    Returns None for anything unrecognizable so callers can drop the row
    instead of crashing.
    """
    if not isinstance(day, str):
        return None

    day = day.strip()
    month = MONTHS.get(day[:3])
    if month is None:
        return None

    space = day.find(" ")
    if space == -1:
        return None

    try:
        return date(int(str(date.today())[:4]), month, int(day[space + 1:]))
    except ValueError:      # non-numeric day, or a day out of range for the month
        return None


# ---------------------------------------------------------------------------
# Turn the "time" column into a single number (seconds)
# ---------------------------------------------------------------------------
def parse_time(raw) -> float:
    """Convert '10.52', '2:05.31', or '1:02:03.4' into seconds as a float.

    Everything downstream (mean, median, binning) needs times on a single
    numeric scale. '2:05.31' and '10.52' are not comparable as strings, so we
    normalize to seconds. Unparseable entries become NaN and get dropped.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return np.nan

    s = str(raw).strip()
    # Drop annotation junk that meet results love: '10.52a', '4:31.02h', '*', '#'
    s = re.sub(r"[^0-9:.]", "", s)
    if not s:
        return np.nan

    parts = s.split(":")
    try:
        if len(parts) == 1:                       # SS.ss
            return float(parts[0])
        if len(parts) == 2:                       # MM:SS.ss
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:                       # HH:MM:SS.ss
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return np.nan
    return np.nan


# ---------------------------------------------------------------------------
# Cosmetic helper: label an axis in m:ss once times exceed a minute
# ---------------------------------------------------------------------------
def seconds_formatter(x, _pos):
    if x < 60:
        return f"{x:.1f}"
    minutes, seconds = divmod(x, 60)
    return f"{int(minutes)}:{seconds:04.1f}"
