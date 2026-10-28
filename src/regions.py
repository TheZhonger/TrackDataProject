"""
regions.py
==========
Which states make up a pool, and how states group into Census regions.

Two kinds of fact live here, both about geography rather than about any stage:

REGIONS
    The pool scopes stage 04 may fit. "northeast" is the original nine
    (src/northeast.py, unchanged, because stage 02 imports it from there);
    "us" is all 50 states plus DC. A pool's states must come from ONE scope, so
    all five events' pools rest on the same population -- otherwise their
    return periods would be counting different things and could not be compared.

CENSUS_REGIONS / CENSUS_DIVISIONS
    The US Census Bureau's 4 regions and 9 divisions, as state -> group maps,
    for the group-vs-national figures. DC is in the South Atlantic division, as
    the Bureau has it. The Census Northeast region is exactly the project's
    northeast nine, which is a useful cross-check rather than a coincidence:
    those were the nine states scraped first.
"""

from northeast import NORTHEAST

# 9 divisions -> states. Regions are unions of divisions, so they are derived
# below rather than typed twice.
_DIVISIONS = {
    "New England":        ("CT", "ME", "MA", "NH", "RI", "VT"),
    "Middle Atlantic":    ("NJ", "NY", "PA"),
    "East North Central": ("IL", "IN", "MI", "OH", "WI"),
    "West North Central": ("IA", "KS", "MN", "MO", "NE", "ND", "SD"),
    "South Atlantic":     ("DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV"),
    "East South Central": ("AL", "KY", "MS", "TN"),
    "West South Central": ("AR", "LA", "OK", "TX"),
    "Mountain":           ("AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"),
    "Pacific":            ("AK", "CA", "HI", "OR", "WA"),
}
_REGION_OF_DIVISION = {
    "New England": "Northeast", "Middle Atlantic": "Northeast",
    "East North Central": "Midwest", "West North Central": "Midwest",
    "South Atlantic": "South", "East South Central": "South",
    "West South Central": "South",
    "Mountain": "West", "Pacific": "West",
}

CENSUS_DIVISIONS = {st: div for div, sts in _DIVISIONS.items() for st in sts}
CENSUS_REGIONS = {st: _REGION_OF_DIVISION[div]
                  for st, div in CENSUS_DIVISIONS.items()}

US = tuple(sorted(CENSUS_DIVISIONS))            # 50 states + DC

REGIONS = {"northeast": NORTHEAST, "us": US}


def _self_check() -> None:
    """Each grouping must partition exactly the 51 jurisdictions."""
    assert len(US) == 51, len(US)
    counts = {}
    for st, div in CENSUS_DIVISIONS.items():
        counts[div] = counts.get(div, 0) + 1
    assert sum(counts.values()) == 51 and len(counts) == 9, counts
    assert len(set(CENSUS_REGIONS.values())) == 4
    assert {st for st, r in CENSUS_REGIONS.items() if r == "Northeast"} == set(NORTHEAST)


_self_check()
