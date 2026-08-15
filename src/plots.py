# src/plots.py
#
# Three figures, in this order of importance (PROTOCOL.md Section 10 spirit):
#   Fig 1  cost sensitivity curve + break-even marker   (the cover figure)
#   Fig 2  24-cell grid heatmap of net Sharpe
#   Fig 3  NAV: composite vs EW9 vs SPY                 (deliberately last)
# Default matplotlib styling; clarity over polish.

import matplotlib
matplotlib.use("Agg")  # write files, never open windows
import matplotlib.pyplot as plt  # noqa: E402


def fig_cost_sensitivity(cost_grid, sharpes, break_even, path):
    raise NotImplementedError("Block 3")


def fig_grid_heatmap(grid_df, path):
    raise NotImplementedError("Block 3")


def fig_nav(dates, nav_strategy, nav_ew9, nav_spy, path):
    raise NotImplementedError("Block 3")
