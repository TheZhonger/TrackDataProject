"""
density_plots.py
================
Smoothed densities of the national pools, 2025 and 2026, and the two seasons
laid over each other.

WHAT A DENSITY ADDS OVER THE HISTOGRAMS
---------------------------------------
The histograms in figures/histograms/ show one season at a time with bins.
Two seasons on one set of bins are hard to compare (the bars hide each other),
and the shape question -- "is 2025's distribution the same as 2026's, only
with a different n?" -- needs both on one axis, normalised to area 1. A kernel
density estimate does that: each mark is replaced by a small Gaussian bump and
the bumps are summed, giving a smooth curve whose area is 1 whatever n is.

The bump width (bandwidth) is Scott's rule, n^(-1/5) x spread. Times sit on a
grid of hundredths; with tens of thousands of marks the bandwidth is far wider
than 0.01 s, so the grid does not show through as the comb the histograms have
to guard against (plot_pooled.aligned_bins).

WHY A SECOND ROW ON A LOG SCALE
-------------------------------
On a linear axis the densities of the two seasons look identical: the body
holds almost all of the area, and the fast tail -- the only part the tail fits
and the record test use -- is a sliver against zero. The comparison figure's
second row therefore plots the empirical survival S(t) = share of the season
at t or faster, for the fastest 10%, on a log y-axis. There a factor-of-two
difference in how many athletes reach a time is a visible gap, and the record
sits at S = 1/n.

Data: the same cleaned pools the fits use (pool_data.load_pool: fence, athlete
dedupe, mile conversion), all 51 states.

    python stages/02_explore/density_plots.py [--sex m,f] [--dpi 140]

Writes stages/02_explore/output/density/density_{2025,2026,2025_vs_2026}_{m,f}.png
(paths.EXPLORE_DENSITY). Stage 02 work: descriptive, no tail model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

# The pooled loader and the palette are shared helpers in <repo>/src, so this
# descriptive stage uses exactly the cleaned pools the stage 04 fits use
# (fence, athlete dedupe, mile conversion) without importing a later stage.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from plotstyle import (BLUE, INK, INK_SOFT, MEDIAN_C, ORANGE, REFERENCE,  # noqa: E402
                       SURFACE, style_axis, time_axis)
from pool_data import EVENTS, load_pool, pool_name  # noqa: E402
from paths import EXPLORE_DENSITY  # noqa: E402

YEARS = (2025, 2026)
# Fixed slot per season, never cycled (the palette's first two categorical
# slots, validated in src/plotstyle): 2025 is always blue, 2026 always orange.
SEASON_C = {2025: BLUE, 2026: ORANGE}
KDE_MAX = 50_000          # sample size for the KDE; the curve is unchanged by more
TAIL_SHARE = 0.10         # the comparison's log-scale row: fastest 10%


def season_marks(event: str, sex: str) -> dict[int, np.ndarray]:
    out = {}
    for y in YEARS:
        df, _ = load_pool(event, sex, years=(y,), region="us")
        out[y] = np.sort(df["seconds"].to_numpy(dtype=float))
    return out


def kde_curve(t: np.ndarray, grid: np.ndarray, rng) -> np.ndarray:
    """Gaussian KDE on a seeded subsample (KDE cost grows with n x grid)."""
    s = t if t.size <= KDE_MAX else rng.choice(t, KDE_MAX, replace=False)
    return gaussian_kde(s)(grid)


def plot_grid(pools: dict) -> np.ndarray:
    """One x-grid per event covering both seasons from 0.1% to 99.5%: the
    extreme slow end is junk the fence only partly removes, and drawing it
    would squash the body into the left of the panel."""
    both = np.concatenate([pools[y] for y in YEARS])
    lo, hi = np.quantile(both, [0.0005, 0.995])
    pad = 0.03 * (hi - lo)
    return np.linspace(lo - pad, hi + pad, 600)


def figure_season(data: dict, sex: str, year: int, path, dpi: int, rng) -> None:
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(3.3 * len(EVENTS), 3.4))
    for ax, ev in zip(axes, EVENTS):
        t = data[ev][year]
        grid = plot_grid(data[ev])
        d = kde_curve(t, grid, rng)
        style_axis(ax)
        ax.fill_between(grid, d, color=SEASON_C[year], alpha=0.18, lw=0)
        ax.plot(grid, d, color=SEASON_C[year], lw=2)
        med = float(np.median(t))
        ax.axvline(med, color=MEDIAN_C, lw=1.5)
        # The fast tail is the LOW-seconds side: the top 10% / 1% of marks
        # are the 10% / 1% quantiles of time. These are the fit thresholds.
        for q, ls in ((0.10, "--"), (0.01, ":")):
            ax.axvline(np.quantile(t, q), color=REFERENCE, lw=1.1, ls=ls)
        ax.set_title(f"{pool_name(ev, sex)}  (n = {t.size:,})", fontsize=10, color=INK)
        ax.set_yticks([])
        time_axis(ax, grid.max())
        ax.set_xlabel("time", fontsize=8, color=INK_SOFT)
    handles = [plt.Line2D([], [], color=SEASON_C[year], lw=2, label=f"{year} density"),
               plt.Line2D([], [], color=MEDIAN_C, lw=1.5, label="median"),
               plt.Line2D([], [], color=REFERENCE, lw=1.1, ls="--", label="top 10% starts"),
               plt.Line2D([], [], color=REFERENCE, lw=1.1, ls=":", label="top 1% starts")]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.suptitle(f"National {'boys' if sex == 'm' else 'girls'} {year}: smoothed "
                 "distribution of season-best marks (area = 1; faster is left)",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


def figure_compare(data: dict, sex: str, path, dpi: int, rng) -> None:
    fig, axes = plt.subplots(2, len(EVENTS), figsize=(3.3 * len(EVENTS), 6.4))
    for j, ev in enumerate(EVENTS):
        grid = plot_grid(data[ev])
        top, bot = axes[0, j], axes[1, j]
        style_axis(top)
        style_axis(bot)
        for y in YEARS:
            t = data[ev][y]
            top.plot(grid, kde_curve(t, grid, rng), color=SEASON_C[y], lw=2,
                     label=f"{y} (n = {t.size:,})")
            # Empirical survival of the fast tail: the k-th fastest of n has
            # S = k/n. Plotted as a step down to the record at 1/n.
            k = max(int(TAIL_SHARE * t.size), 1)
            bot.step(t[:k], np.arange(1, k + 1) / t.size, where="post",
                     color=SEASON_C[y], lw=1.6)
        top.set_title(pool_name(ev, sex), fontsize=10, color=INK)
        top.set_yticks([])
        top.legend(frameon=False, fontsize=7, loc="upper right")
        time_axis(top, grid.max())
        bot.set_yscale("log")
        time_axis(bot, grid.max())
        bot.set_xlabel("time", fontsize=8, color=INK_SOFT)
    axes[0, 0].set_ylabel("density", fontsize=9, color=INK_SOFT)
    axes[1, 0].set_ylabel("share at this time or faster\n(fastest 10%, log scale)",
                          fontsize=9, color=INK_SOFT)
    fig.suptitle(f"National {'boys' if sex == 'm' else 'girls'}: 2025 vs 2026. "
                 "Top: whole distribution. Bottom: the fast tail, where the "
                 "record sits at 1/n", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="National density plots, 2025 vs 2026.")
    ap.add_argument("--sex", default="m,f")
    ap.add_argument("--dpi", type=int, default=140)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out = EXPLORE_DENSITY
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    for sex in args.sex.split(","):
        data = {ev: season_marks(ev, sex) for ev in EVENTS}
        for y in YEARS:
            figure_season(data, sex, y, out / f"density_{y}_{sex}.png", args.dpi, rng)
        figure_compare(data, sex, out / f"density_2025_vs_2026_{sex}.png", args.dpi, rng)


if __name__ == "__main__":
    main()
