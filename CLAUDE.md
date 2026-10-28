# CLAUDE.md — Track Times Research

## What this is

This project scores high school track performances (100m–1600m) on one
cross-event scale of "how rare is this?" A 10.31 in the 100m and a 4:08 in the
1600m are both good, but the fields differ in depth, spread and physiological
ceiling. Extreme value theory handles this. We fit a **Generalized Pareto
Distribution to only the fast tail** of each event, then turn a query time into
a return period ("one athlete-season in N"). Return periods are unit-free, so
they compare across events. Data is scraped from athletic.net.

The project is an ICM workspace: numbered stages run in order, each stage
documents itself, and stable rules live apart from per-run output. Treat paths
and "current state" claims as things to re-verify.

## Folder map

| Folder | What it holds |
|---|---|
| `stages/01_scrape/` | athletic.net scrapers; its `output/` **is the project's data** |
| `stages/02_explore/` | descriptive plots and regressions, no inference |
| `stages/03_tail_fit/` | single-event GPD fit + threshold selection (core EVT code), per-state sweep |
| `stages/04_pooled_fit/` | pooled fits, 5 events: `output/northeast/<years>/` (9 states) and `output/national/<years>/` (51), plus `output/comparisons/` (seasons, regions, tail models, record tests); index in `output/README.md` |
| `stages/05_deploy/` | Streamlit website for the Gompertz query tool (local). **Daren writes this code himself**; `data/` holds copies of the stage 04 Gompertz CSVs |
| `_config/` | stable rules for every stage: data conventions, EVT theory, lessons, open questions |
| `src/` | helpers shared across stages: `paths.py` (every location), `util.py` (date/time parsing), `distances.py` (the mile rule), `northeast.py` (the nine-state pool), `regions.py` (pool scopes, Census regions/divisions), `pool_data.py` (the pooled loader: fence, dedupe, mile conversion, seasons), `plotstyle.py` (validated palette, axis helpers), `plot_groups.py` (pooled and per-group histogram figures, shared by stages 02 and 04) |
| `_archive/` | superseded code and figures, the old `scrape.py`, the 2026-10-06 project report. Don't build on it |
| `.venv/` | macOS virtualenv (`requirements.txt`) |
| `downloaded_files/` | SeleniumBase scratch, created in the cwd. Ignore |
| `reports/` | Daren's own reports. **Ignore it**: don't read, edit, cite or build on anything in it |
| `.icm/` | move log + `undo_moves.sh` from the 2026-10-07 reorganisation |

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/python stages/04_pooled_fit/run_all.py                     # e.g.
```

Every script resolves its paths through `src/paths.py`, so you can launch it from
any directory. It reads earlier stages' `output/` and writes only to its own.
Each stage's `CONTEXT.md` has the exact commands.

## Conventions

- **Internal EVT code works on `x = -seconds`.** Printed and plotted output is
  in seconds (`_config/evt_theory.md` §3.4). Mixing these is the easiest way
  to produce nonsense.
- Non-negotiables in the fit code: `floc=0`, athlete dedupe on, the strict
  `parse_time` that refuses commas, the bootstrap re-selecting `u`, and the
  ξ < −0.5 warning (`stages/03_tail_fit/references/gpd_tail.md`).
- Never reintroduce rank-based normalization. It cannot see margin of victory
  (`_config/lessons.md`).
- Event slugs always carry units (`1600m`, not `1600`). A bad slug fails silently.
- New paths go in `src/paths.py`, not inline. New outputs go in the owning stage's `output/`.
- **Ignore the `reports/` folder.** It is not part of the workspace: don't read it, treat its contents as
  project facts, or write into it, unless Daren asks for something in it by name.
- Any new cross-method or cross-event comparison must be **scale-relative**, and
  only counts as corroboration when both methods actually converged.
- **Text for Daren — reports, plans, summaries — is written in ASD-STE100 style, to
  approximately 80%.**
  - Sentences: max. 20 words for instructions, max. 25 words for descriptions.
  - Use the active voice and simple tenses. Give one instruction per sentence.
  - Use one word for one meaning, and approved STE words where possible. Technical
    names (GPD, Gompertz, return period) are permitted.
  - Paragraphs: max. 6 sentences. Use lists and tables for steps and data.
- **Agent context files** (`CLAUDE.md`, `CONTEXT.md`, `references/`, `_config/`) are not
  bound by STE. Write them in whatever form an agent reads most reliably: precise,
  explicit, structured, with exact paths, names and numbers. Code comments keep the
  house style.

## Working with Daren

Daren is the author. He has a strong coding background and is building up the
statistics as he goes, so:

- **Explain the math before the code.** Start from basic statistical intuition,
  not from the API. Assume high-school-level math and define notation when you
  use it.
- **Connect formulas to physical meaning.** What does the implied wall say about
  human physiology? What does a sliding ξ mean about the data?
- He generally prefers to write his own code, but accepts full implementations
  for complex statistical components (the GPD and threshold machinery were
  handed over whole).
- **Write generous inline comments and docstrings** that explain *why*, not what.
  The existing comments are the house style.
- He actively catches bugs and conceptual flaws. When he flags one, fix it
  directly rather than defending the original. He's usually right.
- Conversations run intuition → derivation → implementation → diagnostics.
  Expect follow-ups that go deeper into theory.

## Where to go next

Read the root `CONTEXT.md` to route a task to a stage. Then read that stage's
`CONTEXT.md`, and load only the files its Inputs table lists.
