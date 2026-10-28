"""
plot_groups.py
==============
Per-group small multiples ("each state against the pool"), the pooled
event x sex histograms (panel_hist, figure_pooled), and the
resolution-aligned histogram bins they use. Moved unchanged out of
stages/04_pooled_fit/plot_pooled.py on 2026-10-22 so stage 02 can draw the same
figure for the national pools without importing a later stage. plot_pooled
re-exports every name here. Callers select the matplotlib backend
(matplotlib.use("Agg")) before importing this module.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plotstyle import (ALERT, BAR_FILL, INK, INK_SOFT, MEAN_C, MEDIAN_C,
                       REFERENCE, SURFACE, style_axis, time_axis)
from pool_data import EVENTS, SEXES, fmt_time


def aligned_bins(seconds: np.ndarray, target: int = 60,
                 resolution: float = 0.01,
                 lo: float | None = None, hi: float | None = None):
    """
    Bin edges that are a whole multiple of the timing resolution.

    Race times are not continuous -- they are recorded on a grid of hundredths
    of a second. If a bin comes out 0.094 s wide, some bins span nine of those
    hundredths and their neighbours span ten, so the histogram grows a regular
    comb of alternating tall and short bars. That comb is an artefact of where
    the edges landed and says nothing whatever about the athletes.

    numpy's "auto" rule walks straight into it: Freedman-Diaconis optimises bin
    WIDTH and knows nothing about the grid the data sits on. On the pooled 100 m
    it picks 0.094 s and the comb is plainly visible.

    Snapping the width to a multiple of the resolution makes every bin cover
    exactly the same number of achievable times, and the comb disappears.
    """
    v = np.asarray(seconds, dtype=float)
    lo = float(v.min()) if lo is None else lo
    hi = float(v.max()) if hi is None else hi
    width = max(resolution, round((hi - lo) / target / resolution) * resolution)
    start = np.floor(lo / width) * width
    return np.arange(start, hi + width, width)


# ======================================================================
# FIGURE 2 -- per-group small multiples (states; Census regions/divisions)
# ======================================================================

def group_shifts(df: pd.DataFrame, groups: dict[str, str]) -> pd.DataFrame:
    """
    Per group: n, median, mean, and each one's shift from the WHOLE pool's.

    `groups` maps state -> group label ({"NY": "NY"} for states themselves,
    or the Census maps in src/regions.py). Negative shifts are faster.

    Two cautions travel with these numbers. The mean is pulled by the slow
    tail, so mean shift minus median shift is a skew signal, not a second
    estimate of speed. And a list stops where athletic.net's list stops, so
    a state whose list is short relative to its real field looks FASTER at
    the median than it is: these compare lists, not populations.
    """
    sec = df["seconds"].to_numpy(dtype=float)
    nat_med, nat_mean = float(np.median(sec)), float(sec.mean())
    g = df["state_dir"].map(groups)
    rows = []
    for name, s in df.groupby(g)["seconds"]:
        v = s.to_numpy(dtype=float)
        med, mean = float(np.median(v)), float(v.mean())
        rows.append({"group": name, "n": int(v.size),
                     "median_s": med, "mean_s": mean,
                     "median_shift_s": med - nat_med,
                     "mean_shift_s": mean - nat_mean})
    out = pd.DataFrame(rows).sort_values("median_shift_s").reset_index(drop=True)
    out.attrs.update(national_median_s=nat_med, national_mean_s=nat_mean)
    return out


def figure_by_group(df: pd.DataFrame, meta: dict, groups: dict[str, str],
                    level: str, path, dpi: int) -> pd.DataFrame:
    """
    One histogram per group on a shared x-axis, each against the whole pool.

    Small multiples rather than overlaid series: past a handful of groups,
    overlaid colours cannot be told apart, and the comparison that matters is
    each group against the POOL, not against each other. Panels are ordered by
    median shift, fastest first, so the order itself is readable.

    In every panel: this group's median (solid) and mean (dashed), and the
    pool's median and mean as grey references. Returns the group_shifts table
    the figure was drawn from, so the numbers can be quoted without reading
    them off a plot.
    """
    tab = group_shifts(df, groups)
    nat_med = tab.attrs["national_median_s"]
    nat_mean = tab.attrs["national_mean_s"]
    all_sec = df["seconds"].to_numpy(dtype=float)
    g = df["state_dir"].map(groups)

    # Shared limits so the panels are actually comparable. Clipped at the 99.5th
    # percentile: a handful of slow marks would otherwise squeeze every body
    # into the left third of its panel.
    lo, hi = float(all_sec.min()), float(np.percentile(all_sec, 99.5))
    pad = 0.02 * (hi - lo)
    bins = aligned_bins(all_sec, target=42, lo=lo - pad, hi=hi + pad)

    k = len(tab)
    ncols = 2 if k <= 4 else 3 if k <= 9 else 6
    nrows = int(np.ceil(k / ncols))
    pw, ph = (4.5, 3.1) if k <= 9 else (2.35, 1.75)     # inches per panel
    fig, axes = plt.subplots(nrows, ncols, figsize=(pw * ncols, ph * nrows + 1.3),
                             sharex=True, squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    small = k > 9
    warned = {w["state"] for w in meta["coverage_warnings"]}

    for ax, r in zip(axes.flatten(), tab.itertuples()):
        style_axis(ax)
        s = df.loc[g == r.group, "seconds"].to_numpy(dtype=float)
        ax.hist(s, bins=bins, color=BAR_FILL, edgecolor=SURFACE, linewidth=0.3)
        ax.axvline(nat_med, color=REFERENCE, ls="-", lw=1.2)
        ax.axvline(nat_mean, color=REFERENCE, ls="--", lw=1.2)
        ax.axvline(r.median_s, color=MEDIAN_C, ls="-", lw=1.8)
        ax.axvline(r.mean_s, color=MEAN_C, ls="--", lw=1.6)
        flag = " !" if r.group in warned else ""
        ax.set_title(f"{r.group}{flag}   n = {r.n:,}", fontsize=8 if small else 10,
                     color=ALERT if flag else INK)
        ax.text(0.985, 0.93,
                f"median {r.median_shift_s:+.2f} s\nmean {r.mean_shift_s:+.2f} s",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=6.5 if small else 8, color=INK_SOFT, linespacing=1.4)
        if small:
            ax.tick_params(labelsize=6)
            ax.set_yticks([])
        time_axis(ax, hi)

    for ax in axes.flatten()[k:]:
        ax.axis("off")
    if not small:
        for ax in axes[:, 0]:
            ax.set_ylabel("athletes", fontsize=9, color=INK_SOFT)

    # One legend for the whole figure: the four lines mean the same thing in
    # every panel, so repeating a legend per panel is pure noise.
    handles = [plt.Line2D([], [], color=MEDIAN_C, ls="-", lw=1.8, label="group median"),
               plt.Line2D([], [], color=MEAN_C, ls="--", lw=1.6, label="group mean"),
               plt.Line2D([], [], color=REFERENCE, ls="-", lw=1.2,
                          label=f"pool median  {fmt_time(nat_med)}"),
               plt.Line2D([], [], color=REFERENCE, ls="--", lw=1.2,
                          label=f"pool mean  {fmt_time(nat_mean)}")]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               fontsize=9, labelcolor=INK_SOFT, bbox_to_anchor=(0.5, 0.004))

    sex_word = "boys" if meta["sex"] == "m" else "girls"
    fig.suptitle(f"{meta['label']} {sex_word}, {meta['dataset']}: each {level} "
                 f"against the pool", fontsize=15, color=INK)
    fig.text(0.5, 1 - 0.55 / fig.get_figheight(),
             "shift = group minus pool, negative is faster; panels fastest "
             "median first. Lists, not populations: a short list looks fast.",
             ha="center", va="top", fontsize=9, color=INK_SOFT)
    fig.tight_layout(rect=(0, 0.45 / fig.get_figheight(), 1,
                           1 - 0.8 / fig.get_figheight()))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")
    return tab


def figure_by_state(df: pd.DataFrame, meta: dict, path, dpi: int) -> pd.DataFrame:
    """Each state against the pool: figure_by_group with every state its own group."""
    return figure_by_group(df, meta, {st: st for st in meta["per_state"]},
                           "state", path, dpi)


def panel_hist(ax, seconds: np.ndarray, title: str, bins=None,
               subtitle: str = "") -> None:
    """One histogram with mean, median, n and spread."""
    style_axis(ax)
    if seconds.size == 0:
        ax.set_title(f"{title} -- no data", fontsize=10, color=INK)
        ax.axis("off")
        return

    if bins is None:
        bins = aligned_bins(seconds)
    ax.hist(seconds, bins=bins, color=BAR_FILL, edgecolor=SURFACE, linewidth=0.4)

    mean = float(seconds.mean())
    median = float(np.median(seconds))
    # ddof=1: these are samples of a season's athletes, not the population.
    sd = float(seconds.std(ddof=1)) if seconds.size > 1 else 0.0

    ax.axvline(mean, color=MEAN_C, ls="--", lw=2.0,
               label=f"mean  {fmt_time(mean)}")
    ax.axvline(median, color=MEDIAN_C, ls="-", lw=2.0,
               label=f"median  {fmt_time(median)}")

    ax.set_title(title, fontsize=11, color=INK, pad=12 if subtitle else 5)
    if subtitle:
        ax.text(0.5, 1.012, subtitle, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=7.5, color=INK_SOFT)
    ax.set_xlabel("time", fontsize=9, color=INK_SOFT)
    ax.set_ylabel("athletes", fontsize=9, color=INK_SOFT)
    time_axis(ax, float(seconds.max()))

    leg = ax.legend(fontsize=8, frameon=False, loc="upper right")
    for text in leg.get_texts():
        text.set_color(INK_SOFT)

    ax.text(0.985, 0.63,
            f"n = {seconds.size:,}\nsd = {sd:.2f} s\n"
            f"fastest {fmt_time(float(seconds.min()))}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color=INK_SOFT, linespacing=1.5)


def figure_pooled(pools: dict, path, dpi: int, dataset: str = "2026") -> None:
    """Rows are events, columns are the sexes present in `pools`."""
    sexes = [s for s in SEXES if any(k[1] == s for k in pools)]
    fig, axes = plt.subplots(len(EVENTS), len(sexes),
                             figsize=(6.75 * len(sexes), 3.6 * len(EVENTS)),
                             squeeze=False)
    fig.patch.set_facecolor(SURFACE)

    for r, event in enumerate(EVENTS):
        for c, sex in enumerate(sexes):
            df, meta = pools[(event, sex)]
            sub = ""
            if event == "mile":
                mixed = [f"{st} {info['slug']}"
                         for st, info in meta["resolution"].items()
                         if info["factor"] != 1.0]
                sub = "converted: " + ", ".join(mixed) if mixed else ""
                # National stacked pools convert dozens of state-seasons, and
                # the full list runs off the panel; count them per variant.
                if len(mixed) > 6:
                    slugs = [m.rsplit(" ", 1)[1] for m in mixed]
                    sub = "converted: " + ", ".join(
                        f"{s} x{slugs.count(s)}" for s in sorted(set(slugs))) \
                        + " state-seasons"
            if meta["coverage_warnings"]:
                bad = ", ".join(w["tag"] for w in meta["coverage_warnings"])
                sub += ("   |   " if sub else "") + f"under-collected: {bad}"
            who = "boys" if sex == "m" else "girls"
            panel_hist(axes[r, c], df["seconds"].to_numpy(dtype=float),
                       f"{meta['label']}  --  {who}", subtitle=sub)

    scope = "US" if dataset.startswith("us-") else "northeast"
    fig.suptitle(f"Pooled {dataset.removeprefix('us-')} {scope} race times",
                 fontsize=15, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")
