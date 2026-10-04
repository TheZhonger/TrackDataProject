from datetime import date

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
