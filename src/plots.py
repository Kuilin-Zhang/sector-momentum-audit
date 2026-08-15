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
import numpy as np  # noqa: E402


def fig_cost_sensitivity(cost_grid, sharpes, break_even, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(cost_grid, sharpes, marker="o", color="tab:blue")
    ax.axhline(0.0, color="gray", lw=0.8)
    if break_even is not None:
        ax.axvline(break_even, color="tab:red", ls="--", lw=1.2,
                   label=f"break-even alpha cost = {break_even:.1f} bps")
        ax.legend()
    ax.set_xlabel("round-trip cost (bps)")
    ax.set_ylabel("net Sharpe (grid composite)")
    ax.set_title("Costs kill first: composite net Sharpe vs round-trip cost")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_grid_heatmap(grid, lookbacks, combos, path,
                     title="Design-period net Sharpe at 10 bps, all 24 cells (nothing hidden)"):
    """grid: 2-D array (len(lookbacks) x len(combos)) of net Sharpe at
    10 bps; combos are (skip, top_k) column labels."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto")
    ax.set_yticks(range(len(lookbacks)), [str(x) for x in lookbacks])
    ax.set_xticks(range(len(combos)), [f"s{s}/k{k}" for s, k in combos])
    ax.set_ylabel("lookback (days)")
    ax.set_xlabel("skip / top_k")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_nav(dates, nav_comp, nav_ew9, nav_spy, path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(dates, nav_comp, label="grid composite (net, 10 bps)", color="tab:blue")
    ax.plot(dates, nav_ew9, label="EW9 (net, 10 bps)", color="tab:orange")
    ax.plot(dates, nav_spy, label="SPY buy & hold", color="gray", lw=0.9)
    ax.set_yscale("log")
    ax.set_ylabel("NAV (log scale)")
    ax.legend()
    ax.set_title("Deliberately the last figure: NAV tells you the least")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
