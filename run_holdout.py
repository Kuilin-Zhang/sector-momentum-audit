# run_holdout.py
#
# THE pre-registered holdout run. PROTOCOL.md Section 11: executed exactly
# once, after the design-freeze tag exists and data/prices_holdout.csv has
# been fetched (fetch_holdout.py). The strategy runs continuously from
# 2000; holdout statistics cover every daily accrual dated 2016-01-01
# through 2025-12-31, including the PnL of positions formed at the final
# design-period rebalance. Verdict criteria are pre-committed in Section 11
# and printed verbatim below.

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest import ew9_benchmark, run_backtest
from src.data import MARKET, SECTORS, load_full
from src.metrics import ann_return, ann_vol, max_drawdown, sharpe
from src.stats import break_even_cost, newey_west_tstat, ols

COST_GRID = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0]
LOOKBACKS = [63, 126, 189, 252]
SKIPS = [0, 21]
TOPKS = [2, 3, 4]
HEADLINE_COST = 10.0
HOLDOUT_START = pd.Timestamp("2016-01-01")


def main() -> None:
    dates, prices, tickers, n_filled = load_full()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]
    spy = prices[:, tickers.index(MARKET)]
    spy_ret = np.zeros(len(spy))
    spy_ret[1:] = spy[1:] / spy[:-1] - 1.0

    dates_arr = pd.DatetimeIndex(dates)
    window = dates_arr >= HOLDOUT_START          # holdout accruals mask
    Path("results").mkdir(exist_ok=True)

    # ------------------------------------------------- 24 cells, full history
    rows = []
    cell_returns = {}                            # (lb, sk, k) -> {cost: ret}
    for lb in LOOKBACKS:
        for sk in SKIPS:
            for k in TOPKS:
                cell_returns[(lb, sk, k)] = {}
                for c in COST_GRID:
                    res = run_backtest(sect, dates, lb, sk, k, c)
                    r = res["net_returns"][window]
                    cell_returns[(lb, sk, k)][c] = res["net_returns"]
                    reg_c = ols(r, spy_ret[window])          # per-cell CAPM,
                    t_c = newey_west_tstat(reg_c, lag=21)    # descriptive only (S11)
                    rows.append({
                        "lookback": lb, "skip": sk, "top_k": k, "cost_bps": c,
                        "ann_return": ann_return(r),
                        "ann_vol": ann_vol(r),
                        "net_sharpe": sharpe(r),
                        "max_drawdown": max_drawdown(np.cumprod(1.0 + r)),
                        "capm_alpha_ann": reg_c["alpha"] * 252,
                        "capm_beta": reg_c["beta"],
                        "nw_t_alpha": t_c,
                    })

    with open("results/grid_holdout.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    ten = [r for r in rows if r["cost_bps"] == HEADLINE_COST]
    med_sharpe = float(np.median([r["net_sharpe"] for r in ten]))
    best_sharpe = float(max(r["net_sharpe"] for r in ten))

    # ------------------------------------------- composite: primary series
    def composite_at(cost):
        return np.mean(np.stack([cell_returns[key][cost] for key in cell_returns]), axis=0)

    comp10 = composite_at(HEADLINE_COST)
    reg = ols(comp10[window], spy_ret[window])
    t_alpha = newey_west_tstat(reg, lag=21)
    alpha_ann = reg["alpha"] * 252

    a0 = ols(composite_at(0.0)[window], spy_ret[window])["alpha"]
    a50 = ols(composite_at(50.0)[window], spy_ret[window])["alpha"]
    c_star = break_even_cost(a0, a50, 50.0)

    ew9 = ew9_benchmark(sect, dates, HEADLINE_COST)["net_returns"][window]
    comp_sharpe = sharpe(comp10[window])
    ew9_sharpe = sharpe(ew9)

    # Champion (selected on DESIGN data, per Section 3) - shrinkage check.
    gd = pd.read_csv("results/grid_design.csv")
    gd10 = gd[gd["cost_bps"] == HEADLINE_COST].copy()
    gd10["skip_rank"] = (gd10["skip"] != 21).astype(int)
    champ = gd10.sort_values(
        ["net_sharpe", "lookback", "top_k", "skip_rank"],
        ascending=[False, True, True, True]).iloc[0]
    champ_key = (int(champ["lookback"]), int(champ["skip"]), int(champ["top_k"]))
    champ_holdout_sharpe = sharpe(cell_returns[champ_key][HEADLINE_COST][window])

    # --------------------------------------------------- pre-committed verdict
    if reg["alpha"] > 0 and abs(t_alpha) >= 2.0:
        primary = "Alpha survives costs and beta."
    elif abs(t_alpha) < 2.0:
        primary = "Cannot reject zero alpha."
    else:
        primary = "Alpha significantly NEGATIVE."
    secondary = comp_sharpe > ew9_sharpe
    implementable = c_star >= HEADLINE_COST

    summary = {
        "holdout_window": f"{dates_arr[window][0].date()}..{dates_arr[window][-1].date()}",
        "median_net_sharpe_10bps": round(med_sharpe, 4),
        "best_cell_net_sharpe_10bps": round(best_sharpe, 4),
        "composite_net_sharpe_10bps": round(comp_sharpe, 4),
        "ew9_net_sharpe_10bps": round(ew9_sharpe, 4),
        "capm_alpha_ann": round(alpha_ann, 6),
        "capm_beta": round(reg["beta"], 4),
        "newey_west_t_alpha": round(t_alpha, 3),
        "break_even_cost_bps": round(c_star, 2),
        "design_champion": f"lb{champ_key[0]}/s{champ_key[1]}/k{champ_key[2]}",
        "champion_design_sharpe": round(float(champ["net_sharpe"]), 4),
        "champion_holdout_sharpe": round(champ_holdout_sharpe, 4),
        "primary_verdict": primary,
        "clears_ew9": bool(secondary),
        "implementable_at_10bps": bool(implementable),
        "cells_forward_filled": n_filled,     # NOTES.md obligation, Section 3
    }
    with open("results/holdout_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerows([summary])

    # ------------------------------------------------------- holdout figures
    from src.plots import fig_cost_sensitivity, fig_grid_heatmap, fig_nav
    Path("figures").mkdir(exist_ok=True)

    comp_sharpes = [sharpe(composite_at(c)[window]) for c in COST_GRID]
    fig_cost_sensitivity(COST_GRID, comp_sharpes, c_star,
                         "figures/fig1_cost_sensitivity_holdout.png")

    combos = [(s, k) for s in SKIPS for k in TOPKS]
    grid = np.array([[next(r["net_sharpe"] for r in ten
                          if r["lookback"] == lb and r["skip"] == s and r["top_k"] == k)
                      for (s, k) in combos] for lb in LOOKBACKS])
    fig_grid_heatmap(grid, LOOKBACKS, combos, "figures/fig2_grid_heatmap_holdout.png",
                     title="HOLDOUT net Sharpe at 10 bps, all 24 cells (nothing hidden)")

    nav = lambda r: np.cumprod(1.0 + r)  # noqa: E731
    fig_nav(dates_arr[window], nav(comp10[window]), nav(ew9), nav(spy_ret[window]),
            "figures/fig3_nav_holdout.png")

    # ---------------------------------------------------------------- report
    print("=== HOLDOUT (run once, PROTOCOL.md Section 11) ===")
    for k, v in summary.items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main()
