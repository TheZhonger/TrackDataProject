# Scraper test files (archived 2026-10-09)

Moved out of `stages/01_scrape/output/2026/` so no stage can read them by accident.
Their ledger entries are marked `status: archived`.

- `2026/WY/m/1600.csv`: scraped with the unit-less slug `1600`, the silent
  wrong-slug trap (`stages/01_scrape/references/scraping.md` §0). `scrapeAll.py` now
  refuses such slugs.
- `2026/{DC,VT}/m/3200r.csv`: one-off 3200 m test scrapes. No stage uses the 3200 m.
