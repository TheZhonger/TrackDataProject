# CONTEXT.md — routing

Find the task, go to that folder, and read its `CONTEXT.md`.

| If the task is… | Go to |
|---|---|
| scrape new states/years/events, fix the scraper, rescrape a bad file, athlete career histories | `stages/01_scrape/` |
| look at distributions (histograms, density plots, national pooled / by-state / by-region / by-division histograms, 2025 vs 2026), season timing, athlete progression (no model) | `stages/02_explore/` |
| fit or debug a GPD on one event's CSV, per-state fits, choose a threshold, score a time | `stages/03_tail_fit/` |
| pooled multi-state fits for all five events, mile conversion (1600m boys / 1500m girls), the cross-event summary, seasons, national boys, GPD vs Gompertz tails | `stages/04_pooled_fit/` |
| the website / Streamlit app for querying times (Daren writes the code; explain, don't write) | `stages/05_deploy/` |
| cross-event score aggregation (the project's end goal) | not built yet; it would be `stages/05_*`, reading 04's output |
| change where anything is read or written | `src/paths.py` |

## Shared resources (Layer 3)

| File | Use it for |
|---|---|
| `_config/data_conventions.md` | CSV schema, `r` suffix, which mile each state runs, the dirty `time` column |
| `_config/evt_theory.md` | the statistics: PBdH, ξ regimes, sign convention, ζ = N_u/n, bias–variance in `u` |
| `_config/lessons.md` | rejected approaches and lessons not to relearn |
| `_config/open_questions.md` | the live research questions, and which are answered |

## Open research questions

Six are listed (one answered); see `_config/open_questions.md`. Most important: every pooled tail slides once 2025 is
added (2026's lone 100m boys plateau does not replicate), so more data will not fix the shape (question 1), and extending beyond the northeast is blocked on scraping (question 6).
