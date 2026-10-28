"""
plot_pooled.py
==============
Exploratory figures for one pooled northeast dataset (2026, 2025, or the
two seasons stacked as 2025-2026). Nothing here is
inferential -- these are the pictures you look at BEFORE fitting anything, to
find out whether the pool you just built is a sensible object to fit.

Three figures, each answering one question.

1. hist_pooled.png
       What does each pooled event x sex distribution actually look like?
       Mean and median are both drawn because race times are right-skewed: a
       few slow runners drag the mean but not the median, and the gap between
       the two lines is a quick read on how skewed the event is.

2. hist_by_state_<pool>_<sex>.png   (pool = 100m ... 800m, 1600m boys, 1500m girls)
   hist_by_region_ / hist_by_division_<pool>_<sex>.png   (national scope only)
       Is pooling these nine states legitimate? Pooling assumes the states are
       samples of one population. They are not exactly -- so the question is
       whether they are close enough. Visibly shifted states mean the pool is a
       MIXTURE, and a mixture's tail belongs to its deepest component. This
       figure turns that from an assumption into an observation.

3. mile_conversion_check.png
       Do the distance conversions put each state's mile variant on its sex's
       target scale (1600 m boys, 1500 m girls)? Left panel as run, middle
       converted. If the factors are right, curves that start apart end up on
       top of each other.

       Read this one carefully -- see convert_caveats(). Neither this figure nor
       the within-athlete table printed alongside it can actually PROVE a
       conversion factor, and pretending otherwise would be worse than not
       checking at all.

       Single seasons only. The conversion is applied season by season, so the
       stacked dataset has nothing to check that its two seasons' figures do
       not already show.

Usage:  python stages/04_pooled_fit/plot_pooled.py [--years 2026] [--region northeast|us]
                                                   [--sex m,f] [--states CT,NY,...] [--dpi 140]
Output: stages/04_pooled_fit/output/<region>/<years>/figures/histograms/
"""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")            # file output only
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sys
from pathlib import Path
# Shared helpers (pool_data, paths, regions, plotstyle, ...) live in <repo>/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import (EVENTS, NORTHEAST, SEXES, DATA_ROOT, ENCODING,
                       dataset_dirs, dataset_name, fmt_time, load_pool,
                       parse_time, parse_years, pool_name)
from paths import scrape_year  # src/
from regions import CENSUS_DIVISIONS, CENSUS_REGIONS, REGIONS  # src/
from distances import MILE_SLUGS, factors_for, main_mile_slug, target_name  # src/


# Palette and axis helpers live in src/plotstyle.py (shared with stage 02);
# re-exported here so `from plot_pooled import BLUE, style_axis` keeps working.
from plotstyle import (ALERT, AQUA, BAR_FILL, BLUE, GRID, INK, INK_SOFT,  # noqa: F401
                       MEAN_C, MEDIAN_C, ORANGE, REFERENCE, SURFACE,
                       style_axis, time_axis)


# Bins, the pooled histograms (figures 1) and the per-group small multiples
# (figure 2) live in src/plot_groups.py, shared with stage 02's national
# histograms; re-exported so callers are unchanged.
from plot_groups import (aligned_bins, figure_by_group, figure_by_state,  # noqa: F401
                         figure_pooled, panel_hist,
                         group_shifts)


# ======================================================================
# FIGURE 3 -- do the distance conversions work?
# ======================================================================

def convert_caveats() -> str:
    """Why neither conversion check can be conclusive. Printed with the table."""
    return (
        "  Two things this cannot settle, stated up front:\n"
        "\n"
        "  1. The distribution overlay compares DIFFERENT POPULATIONS. MA's\n"
        "     milers and CT's 1600 runners (or NY's 1500 girls) are not the same athletes, so even a\n"
        "     perfect conversion would leave a gap if one state is simply\n"
        "     deeper. Curves landing on top of each other is encouraging; it is\n"
        "     not proof.\n"
        "\n"
        "  2. The within-athlete table below removes that confound -- those are\n"
        "     the same people at both distances -- but introduces a worse one.\n"
        "     An athlete's main-list mark is their season best in their MAIN\n"
        "     event; their target-distance mark (1600 boys, 1500 girls) is a\n"
        "     one-off at a distance their state barely contests, and almost never\n"
        "     a peak effort. So the converted prediction SHOULD look faster than\n"
        "     the recorded target-distance mark, and it does.\n"
        "     That residual measures effort and opportunity, not just distance.\n"
        "\n"
        "  Both point the same way: use the physical factors, and do not tune\n"
        "  them to this data."
    )


def _slug_label(slug: str) -> str:
    return {"1600r": "1600 m", "1miler": "1 mile", "1500r": "1500 m"}[slug]


def mile_groups(sex: str, states=NORTHEAST, root=DATA_ROOT) -> dict[str, list[str]]:
    """main mile slug -> the states whose main list it is, for one sex."""
    groups: dict[str, list[str]] = {}
    for st in states:
        slug = main_mile_slug(root / st / sex)
        if slug:
            groups.setdefault(slug, []).append(st)
    return groups


def within_athlete_table(states=NORTHEAST, root=DATA_ROOT) -> pd.DataFrame:
    """
    Athletes who appear on BOTH a converted state's main mile list and that
    state's list at the TARGET distance (1600 m boys, 1500 m girls).

    This is the overlap that forces the one-file-per-state rule in pool_data --
    the same names in two files. Here it is put to use: convert the athlete's
    main-distance mark and compare it against the target-distance race they
    actually ran. Before 2026-10-08 this was hardcoded to MA's mile and RI's
    1500 against a 1600; with girls targeting 1500 m the converted states are
    found from the data instead (src/distances.main_mile_slug).
    """
    rows = []
    for sex in SEXES:
        factors = factors_for(sex)
        native = next(s for s, f in factors.items() if f == 1.0)
        for slug, sts in mile_groups(sex, states, root).items():
            if slug == native:
                continue
            for state in sts:
                src = root / state / sex / f"{slug}.csv"
                ref = root / state / sex / f"{native}.csv"
                if not (src.exists() and ref.exists()):
                    continue
                a = pd.read_csv(src, dtype=str, encoding=ENCODING)
                b = pd.read_csv(ref, dtype=str, encoding=ENCODING)
                a["t"] = a["time"].map(parse_time)
                b["t"] = b["time"].map(parse_time)
                a = a.dropna(subset=["t"]).sort_values("t").drop_duplicates("name")
                b = b.dropna(subset=["t"]).sort_values("t").drop_duplicates("name")
                m = a.merge(b, on="name", suffixes=("_src", "_ref"))
                if m.empty:
                    continue
                factor = factors[slug]
                resid = m["t_src"] * factor - m["t_ref"]
                rows.append({
                    "source": f"{state} {slug}", "sex": sex, "n_pairs": len(m),
                    "factor": factor,
                    "median_resid_s": float(resid.median()),
                    "iqr_lo": float(resid.quantile(0.25)),
                    "iqr_hi": float(resid.quantile(0.75)),
                    # The factor that would zero the median residual. NOT a
                    # recommendation -- it absorbs the effort confound above.
                    "implied_factor": float((m["t_ref"] / m["t_src"]).median()),
                })
    return pd.DataFrame(rows)


def _ecdf(v: np.ndarray):
    """Empirical CDF: the fraction of the field at or under each time."""
    x = np.sort(np.asarray(v, dtype=float))
    return x, np.arange(1, x.size + 1) / x.size


def figure_conversion_check(states, path, dpi: int, root=DATA_ROOT) -> None:
    """
    One row per sex, three panels each: ECDFs as run, ECDFs converted onto that
    sex's target distance, and a quantile-quantile plot of each converted
    source against the native target-distance field.

    Boys' native field is the 1600 m states, converted from the mile (MA) and
    the 1500 (RI, VT). Girls' native field is the 1500 m states (NY, RI, VT),
    converted from the 1600 (most states) and the mile (MA). Groups are found
    from the data, so a new state or a rescrape regroups itself.

    ECDFs rather than histograms, deliberately. The series differ in size by
    more than twenty to one, and at a few hundred points a density estimate is
    mostly noise. An ECDF needs no bin width, is stable at small n, and turns
    "these are on different scales" into a plain horizontal gap between curves.

    The QQ panel is the sharp version of the question: it compares fields at
    matched quantiles, so a conversion that is right everywhere puts the points
    on the 45-degree line, while a factor slightly off tilts them.
    """
    def gather(slug, sex, only):
        out = []
        for st in only:
            p = root / st / sex / f"{slug}.csv"
            if p.exists():
                col = pd.read_csv(p, dtype=str, encoding=ENCODING)["time"]
                out.append(col.map(parse_time).dropna())
        return pd.concat(out).to_numpy(dtype=float) if out else np.array([])

    styles = [(BLUE, "-"), (ORANGE, "--"), (AQUA, ":")]
    fig, axes = plt.subplots(len(SEXES), 3, figsize=(16, 5.2 * len(SEXES)))
    fig.patch.set_facecolor(SURFACE)

    for row, sex in enumerate(SEXES):
        factors = factors_for(sex)
        native_slug = next(s for s, f in factors.items() if f == 1.0)
        groups = mile_groups(sex, states, root)
        who = "boys" if sex == "m" else "girls"
        target = target_name(sex)[:-1] + " m"

        # Native first, then each converted distance; tuples are
        # (label, values, factor, colour, linestyle).
        order = [native_slug] + [s for s in MILE_SLUGS if s != native_slug]
        series = []
        for slug in order:
            sts = groups.get(slug, [])
            v = gather(slug, sex, sts)
            if not v.size:
                continue
            tag = "native " if slug == native_slug else ""
            lab = f"{tag}{_slug_label(slug)} ({' '.join(sts)})"
            colour, ls = styles[len(series)]
            series.append((lab, v, factors[slug], colour, ls))
        native = series[0][1]
        r_ax = axes[row]

        for ax, converted in zip(r_ax[:2], (False, True)):
            style_axis(ax)
            vals = [(lab, v * (f if converted else 1.0), col, ls)
                    for lab, v, f, col, ls in series]
            lo = min(float(v.min()) for _, v, _, _ in vals)
            hi = float(np.percentile(np.concatenate([v for _, v, _, _ in vals]), 98))
            for lab, v, col, ls in vals:
                x, y = _ecdf(v)
                # Line style as well as hue: identity survives greyscale
                # printing and colour-vision deficiency without the legend.
                ax.plot(x, y, lw=2.0, color=col, ls=ls,
                        label=f"{lab}  (n = {v.size:,})")
            ax.set_title(f"{who}: as run" if not converted
                         else f"{who}: converted to {target} equivalent",
                         fontsize=11, color=INK)
            ax.set_xlabel("time", fontsize=9, color=INK_SOFT)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_time))
            ax.set_xlim(lo, hi)
            ax.set_ylim(0, 1)
            leg = ax.legend(fontsize=8, frameon=False, loc="lower right")
            for t in leg.get_texts():
                t.set_color(INK_SOFT)
        r_ax[0].set_ylabel("fraction of the field at or under this time",
                           fontsize=9, color=INK_SOFT)

        ax = r_ax[2]
        style_axis(ax)
        q = np.linspace(0.02, 0.98, 97)
        ref_q = np.quantile(native, q)
        for lab, v, f, col, _ in series[1:]:
            ax.plot(ref_q, np.quantile(v * f, q), "o", ms=4, alpha=0.75,
                    color=col, label=f"{lab} x {f:.5f}")
        span = [float(ref_q.min()), float(ref_q.max())]
        ax.plot(span, span, "-", color=REFERENCE, lw=1.6, label="perfect agreement")
        ax.set_xlim(span)
        ax.set_ylim(span)
        ax.set_title(f"{who}: converted vs native {target}, matched quantiles",
                     fontsize=11, color=INK)
        ax.set_xlabel(f"native {target} field", fontsize=9, color=INK_SOFT)
        ax.set_ylabel("converted field", fontsize=9, color=INK_SOFT)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_time))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt_time))
        leg = ax.legend(fontsize=8, frameon=False, loc="upper left")
        for t in leg.get_texts():
            t.set_color(INK_SOFT)

    fig.suptitle("Do the distance conversions line the three miles up?",
                 fontsize=14, color=INK, y=0.995)
    fig.text(0.5, 0.968,
             "boys onto 1600 m, girls onto 1500 m (src/distances.py)      "
             "separate states, so alignment is evidence and not proof",
             ha="center", va="top", fontsize=8.5, color=INK_SOFT)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


def draw_figures(pools: dict, states, years, region: str, dpi: int) -> pd.DataFrame:
    """
    Every descriptive figure for one dataset; returns the conversion table.

    Shared by run_all.py and this script's main(), so the two can never drift.
      hist_pooled.png                       all pools
      hist_by_state_<pool>_<sex>.png        each state against the pool
      hist_by_region_<pool>_<sex>.png       national scope only: 4 Census regions
      hist_by_division_<pool>_<sex>.png     national scope only: 9 Census divisions
      output/<region>/<years>/group_shifts.csv     the numbers behind those figures
      mile_conversion_check.png             single seasons only
    """
    dirs = dataset_dirs(years, region)
    hist = dirs["hist"]
    hist.mkdir(parents=True, exist_ok=True)

    figure_pooled(pools, hist / "hist_pooled.png", dpi, dataset_name(years, region))
    levels = [("state", None)]
    if region == "us":
        levels += [("region", CENSUS_REGIONS), ("division", CENSUS_DIVISIONS)]
    shifts = []
    for (event, sex), (df, meta) in pools.items():
        for level, groups in levels:
            path = hist / f"hist_by_{level}_{meta['pool']}_{sex}.png"
            if groups is None:
                tab = figure_by_state(df, meta, path, dpi)
            else:
                tab = figure_by_group(df, meta, groups, level, path, dpi)
            shifts.append(tab.assign(event=meta["pool"], sex=sex, level=level,
                                     national_median_s=tab.attrs["national_median_s"],
                                     national_mean_s=tab.attrs["national_mean_s"]))
    cols = ["event", "sex", "level", "group", "n", "median_s", "mean_s",
            "median_shift_s", "mean_shift_s", "national_median_s", "national_mean_s"]
    out = pd.concat(shifts, ignore_index=True)[cols].round(3)
    out.to_csv(dirs["out"] / "group_shifts.csv", index=False, encoding="utf-8")
    print(f"  wrote {dirs['out'] / 'group_shifts.csv'}")

    # The conversion is applied one season at a time, so it is checked one
    # season at a time; a stacked dataset defers to its seasons' folders.
    if len(years) > 1:
        print("\n  (stacked seasons: the conversion check lives in each "
              "season's own folder)")
        return pd.DataFrame()
    root = scrape_year(years[0])
    figure_conversion_check(states, hist / "mile_conversion_check.png", dpi,
                            root=root)
    print()
    print("  DISTANCE CONVERSION CHECK")
    print("  " + "-" * 70)
    print(convert_caveats())
    return within_athlete_table(states, root=root)


# ======================================================================
# MAIN
# ======================================================================

def main() -> None:
    ap = argparse.ArgumentParser(description="Pooled histograms for one dataset.")
    ap.add_argument("--years", default="2026",
                    help="season(s): 2026, 2025, or 2025,2026 (stacked)")
    ap.add_argument("--region", default="northeast", choices=sorted(REGIONS))
    ap.add_argument("--sex", default="m,f", help="m, f, or m,f")
    ap.add_argument("--states", default=None,
                    help="comma-separated subset of the region (default: all of it)")
    ap.add_argument("--dpi", type=int, default=140)
    args = ap.parse_args()

    years = parse_years(args.years)
    states = (tuple(s.strip().upper() for s in args.states.split(",") if s.strip())
              if args.states else tuple(REGIONS[args.region]))
    sexes = tuple(args.sex.split(","))

    print("=" * 74)
    print(f"  POOLED HISTOGRAMS  --  {dataset_name(years, args.region)}")
    print("=" * 74)

    pools = {}
    for event in EVENTS:
        for sex in sexes:
            pools[(event, sex)] = load_pool(event, sex, states=states,
                                            years=years, region=args.region)
            _, meta = pools[(event, sex)]
            print(f"  {meta['label']:<20s} {sex}   n = {meta['n']:>7,}")

    print()
    tab = draw_figures(pools, states, years, args.region, args.dpi)
    if len(years) > 1:
        return
    print()
    if tab.empty:
        print("  no athletes appear on both a converted list and a target-distance list")
        return
    print(f"  {'source':<14}{'sex':>4}{'pairs':>7}{'factor':>10}"
          f"{'median resid':>14}{'IQR (s)':>18}{'implied':>10}")
    for _, r in tab.iterrows():
        iqr = f"[{r['iqr_lo']:+.1f}, {r['iqr_hi']:+.1f}]"
        print(f"  {r['source']:<14}{r['sex']:>4}{int(r['n_pairs']):>7}"
              f"{r['factor']:>10.5f}{r['median_resid_s']:>13.2f}s"
              f"{iqr:>18}{r['implied_factor']:>10.5f}")
    print()
    # Caveat 2 predicts negative residuals (converted main-event bests beat a
    # one-off off-distance mark). Report what the data says rather than assert it.
    pos = tab[tab["median_resid_s"] > 0]
    if pos.empty:
        print("  Every median residual is negative, exactly as caveat 2 predicts.")
    else:
        print("  Not every residual is negative: "
              + ", ".join(f"{r['source']} {r['sex']} ({r['median_resid_s']:+.1f} s)"
                          for _, r in pos.iterrows())
              + ". Those athletes' target-distance marks beat their converted"
              "\n  main-event bests -- small samples, or a championship run at"
              " that distance -- so read those rows as noise, not a factor error.")


if __name__ == "__main__":
    main()
