# Stage 02 script notes

Layer 3 reference for stage 02: how to point the scripts at the 2026 scrape,
and what `plot_events.py` draws.

**Running on the 2026 scrape.** `plot_events.py`, `plotByDate.py` and
`dateRegression.py` take `--dir <ST>/<sex> folder --suffix r [--title …]`.
With `--suffix r`, the mile slot is the variant that state actually runs (the one
with the most rows, via `src/distances.event_stems`). It is plotted **as run,
unconverted**, and labelled by its real distance (e.g. "1500m" for NY girls).
Conversion belongs to the fitting stages; this one shows the raw data. For example:

```bash
.venv/bin/python stages/02_explore/plot_events.py --suffix r \
    --dir stages/01_scrape/output/2026/NY/f \
    --out stages/02_explore/output/2026/NY_f/event_histograms.png
```

Without flags, the scripts read the legacy NY boys files as before.

`plot_events.py` (moved from the old CLAUDE.md §6) draws mean and median lines,
`n`, and the SD (`ddof=1`, Bessel's correction, since these are samples). Both
centre lines are drawn because race times are right-skewed. A few slow runners
drag the mean but not the median, so the gap between them is a quick read on
skew. Bins default to `"auto"` (numpy picks the wider of Freedman–Diaconis and
Sturges). Ticks switch to `m:ss` past a minute.

Time parsing and the `m:ss` formatter come from `src/util.py`. `plotByDate.py`
re-exports them for older imports.

**Pooling the northeast.** `--pool northeast --sex {m,f} [--year 2026]` replaces
`--dir`/`--suffix` on all three scripts. `src/northeast.pooled_rows` stacks the
nine states' files for each event. The mile is the most-rows variant per state,
converted onto 1600 m (boys) / 1500 m (girls) as in stage 04. A one-sided
log-IQR fence (k = 2, stage 04's) drops slow-side junk: 0.3–1.2% of each pool.
Without it, a single "36:24.00" filed as a 200 m stretches the axis to half an
hour. `plot_events.py` prints the fenced count on each panel. Pooled n equals
stage 04's final n for the mile (e.g. 10,467 girls' 1500 m eq.).

```bash
.venv/bin/python stages/02_explore/plot_events.py --pool northeast --sex f \
    --out stages/02_explore/output/2026/NE_f/event_histograms.png
.venv/bin/python stages/02_explore/dateRegression.py --pool northeast --sex m --save \
    --out stages/02_explore/output/2026/NE_m/date_regression.png
```

In pool mode `dateRegression.py --top 1000` ranks across all nine states, so it
fits the elite 3–10% of a 10k–29k pool, not a whole state's field. Every pooled
slope was negative on 2026-10-08, for both sexes and all five events.
