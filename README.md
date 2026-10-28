# Track Times Research

This project scores high school track & field performances (100m–1600m) on one
cross-event scale of rarity. It fits a Generalized Pareto Distribution to the
fast tail of each event and reports return periods ("a mark this fast happens
about once in N athlete-seasons"). Data is scraped from athletic.net.

Start with [CLAUDE.md](CLAUDE.md) (what's where, how to run, conventions), then
[CONTEXT.md](CONTEXT.md) (which stage handles which task). The work runs in
order through `stages/01_scrape` → `02_explore` → `03_tail_fit` → `04_pooled_fit`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python stages/04_pooled_fit/run_all.py
```

## Scratch notes

- Only 1 athlete in CA gets filtered by restrict
- No Tate Taylor in TX
