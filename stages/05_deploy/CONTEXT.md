# Stage 05 — deploy

A Streamlit website for the national Gompertz query tool (2025 + 2026 stacked).
Local only for now (`streamlit run` on Daren's Mac).

**Daren writes the app code here, to learn scripting and deployment. Agents explain,
review and answer questions; they do not write or edit app code in this folder unless
he asks for it.** The layout of app files (`.py`, `pages/`, `.streamlit/`) is his to design.

## Inputs
| Layer | Path | What to use from it |
|---|---|---|
| 4 (working) | `data/gompertz_fit.csv` | one row per pool (event, sex): `u_sec`, `top_pct` (ζ = top_pct/100), `c`, `b`, `n`, `n_2025`, `n_2026` |
| 4 (working) | `data/gompertz_boot.csv` | 200 bootstrap draws per pool: `u_sec`, `zeta`, `c`, `b` (for intervals) |
| 4 (working) | `data/gompertz_counts.csv` | every distinct time per pool with `k_2025`, `k_2026` athlete-seasons at it (for counts slower than u) |
| 3 (reference) | `references/query_guide.md` | **start here**: the files, the math, code to copy, Streamlit widgets, check values, pitfalls |
| 3 (reference) | `../04_pooled_fit/gompertz_query.py` | the reference implementation: `return_period`, `equal_rarity_time`, `Counts`, `poisson_ci`, output layout |
| 3 (reference) | `../04_pooled_fit/references/pooled_method.md` §14 | formulas, validity range (t ≤ u for the model), interval meaning |

`data/` holds copies of `../04_pooled_fit/output/national/2025-2026/gompertz/gompertz_{fit,boot,counts}.csv`
(copied 2026-10-23), so this folder is self-contained. Re-copy after `../04_pooled_fit/gompertz_pooled.py`
or `../04_pooled_fit/gompertz_query.py --build-counts`. Event values in the CSVs: `100m 200m 400m 800m`,
`1600m` (boys), `1500m` (girls); sex `m`/`f`.

## Process
- Run: `.venv/bin/streamlit run stages/05_deploy/<app>.py` (from the project root).
- Streamlit 1.66.1 is installed in the project `.venv` (`requirements.txt`, "web app" block).
- Check results against the CLI: `.venv/bin/python stages/04_pooled_fit/gompertz_query.py <event> <sex> <time>`.

## Outputs
- `output/`: anything the app exports (screenshots, CSV downloads). Empty at setup.

## Verify
- The app's return period for a time equals `gompertz_query.py`'s for the same time.
- `cmp data/gompertz_fit.csv ../04_pooled_fit/output/national/2025-2026/gompertz/gompertz_fit.csv`
  is silent (data not stale); same for boot and counts.
