"""
plotstyle.py
============
The validated palette and axis helpers shared by every figure script
(stage 02 density plots, stage 04 fits). Moved out of
stages/04_pooled_fit/plot_pooled.py on 2026-10-22 so an earlier stage can use it
without importing a later one. Callers must select the matplotlib backend
(matplotlib.use("Agg")) BEFORE importing this module, because it imports pyplot.
"""

import matplotlib.pyplot as plt

from pool_data import fmt_time  # noqa: F401  (re-exported for callers)


# ======================================================================
# PALETTE
# ======================================================================
# Validated with the dataviz checker against the light surface these PNGs
# actually render on (categorical, all pairs): worst CVD deltaE 9.2, worst
# normal-vision deltaE 24.0. Only light steps are used -- a PNG has one fixed
# surface, so the dark steps of the same ramps never apply here.
#
# Aqua sits just under 3:1 contrast on this surface, so it never carries meaning
# alone: every aqua mark is also distinguished by line style and named in a
# legend with its value.

SURFACE  = "#fcfcfb"
INK      = "#0b0b0b"
INK_SOFT = "#52514e"
GRID     = "#d8d7d2"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

BAR_FILL  = BLUE
MEAN_C    = ORANGE      # always dashed
MEDIAN_C  = AQUA        # always solid
REFERENCE = "#8a8984"   # pooled reference line in the small multiples
ALERT     = "#a03a12"

# Fixed slot per data source, never cycled: the same source keeps the same
# colour in every figure it appears in.


def style_axis(ax) -> None:
    """Recessive grid and axes: the data should be the darkest thing on screen."""
    ax.set_facecolor(SURFACE)
    ax.grid(alpha=0.35, color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=8)


def _mss(v, _pos=None) -> str:
    """Axis label m:ss. Ticks are whole seconds, so fmt_time's hundredths
    ("2:20.00") only widen the label -- enough to collide on narrow panels."""
    return f"{int(v // 60)}:{int(round(v % 60)):02d}"


def time_axis(ax, seconds_max: float) -> None:
    """At most 5 ticks; labelled m:ss once the event is longer than a minute.
    (Before 2026-10-22 the labels were m:ss.00 at matplotlib's default tick
    count, and they ran into each other on the 51-panel mile figures.)"""
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))
    if seconds_max >= 60:
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_mss))
