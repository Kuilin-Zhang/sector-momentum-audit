# run_all.py
#
# One command reproduces every DESIGN-PERIOD number from the committed
# snapshot, with no network access:
#     python run_all.py
# Holdout numbers appear only after the pre-registered holdout run
# (PROTOCOL.md Section 11); until then this script covers 2000-2015.
#
# Pipeline: load -> 24-cell grid x 6 cost levels -> composite + EW9 + SPY
#           -> CAPM (hand-written OLS + Newey-West) -> results/*.csv
#           -> figures/*.png

import csv
from pathlib import Path

import numpy as np

from src.backtest import ew9_benchmark, run_backtest
from src.data import MARKET, SECTORS, load_prices
from src.metrics import ann_return, ann_vol, max_drawdown, sharpe
from src.stats import break_even_cost, newey_west_tstat, ols

COST_GRID = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0]
LOOKBACKS = [63, 126, 189, 252]
SKIPS = [0, 21]
TOPKS = [2, 3, 4]
HEADLINE_COST = 10.0


def main() -> None:
    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]
    spy = prices[:, tickers.index(MARKET)]
    spy_ret = np.zeros(len(spy))
    spy_ret[1:] = spy[1:] / spy[:-1] - 1.0

    Path("results").mkdir(exist_ok=True)
    Path("figures").mkdir(exist_ok=True)

    # ------------------------------------------------------------------ grid
    rows = []
    cell_returns_10bps = {}
    latest_start = 0
    for lb in LOOKBACKS:
        for sk in SKIPS:
            for k in TOPKS:
                for c in COST_GRID:
                    res = run_backtest(sect, dates, lb, sk, k, c)
                    s0 = res["start_index"]
                    r = res["net_returns"][s0 + 1:]
                    rows.append({
                        "lookback": lb, "skip": sk, "top_k": k, "cost_bps": c,
                        "start_date": dates[s0].date(),
                        "ann_return": round(ann_return(r), 6),
                        "ann_vol": round(ann_vol(r), 6),
                        "net_sharpe": round(sharpe(r), 4),
                        "max_drawdown": round(max_drawdown(res["nav"][s0:]), 4),
                        "ann_turnover": round(sum(res["turnovers"]) / (len(r) / 252.0), 3),
                    })
                    if c == HEADLINE_COST:
                        cell_returns_10bps[(lb, sk, k)] = res["net_returns"]
                        latest_start = max(latest_start, s0)

    with open("results/grid_design.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # --------------------------------------------------- composite + baselines
    # Grid composite (PROTOCOL.md Section 11): equal-weighted average of the
    # 24 cells' daily net return series at 10 bps. Cells sit in cash (0.0)
    # before their signals become valid; stats start once all are valid.
    composite = np.mean(np.stack(list(cell_returns_10bps.values())), axis=0)
    window = slice(latest_start + 1, None)

    ew9 = ew9_benchmark(sect, dates, HEADLINE_COST)
    ew9_r = ew9["net_returns"]

    # Design-period CAPM of the composite vs SPY (descriptive here; the
    # binding inference happens once, on the holdout - Section 11).
    reg = ols(composite[window], spy_ret[window])
    t_alpha = newey_west_tstat(reg, lag=21)

    # Break-even cost: alpha is linear in c; evaluate at 0 and 50 bps.
    comp0 = np.mean(np.stack([run_backtest(sect, dates, lb, sk, k, 0.0)["net_returns"]
                              for (lb, sk, k) in cell_returns_10bps]), axis=0)
    comp50 = np.mean(np.stack([run_backtest(sect, dates, lb, sk, k, 50.0)["net_returns"]
                               for (lb, sk, k) in cell_returns_10bps]), axis=0)
    a0 = ols(comp0[window], spy_ret[window])["alpha"]
    a50 = ols(comp50[window], spy_ret[window])["alpha"]
    c_star = break_even_cost(a0, a50, 50.0)

    # In-sample champion (Section 3): highest design net Sharpe at 10 bps,
    # ties broken by smaller lookback, then smaller top_k, then skip=21.
    ten = [r for r in rows if r["cost_bps"] == HEADLINE_COST]
    champion = sorted(ten, key=lambda r: (-r["net_sharpe"], r["lookback"],
                                          r["top_k"], 0 if r["skip"] == 21 else 1))[0]
    med_sharpe = float(np.median([r["net_sharpe"] for r in ten]))
    best_sharpe = float(max(r["net_sharpe"] for r in ten))

    summary = {
        "period": f"design {dates[latest_start + 1].date()}..{dates[-1].date()} (stats window)",
        "median_net_sharpe_10bps": round(med_sharpe, 4),
        "best_cell_net_sharpe_10bps": round(best_sharpe, 4),
        "champion_cell": f"lb{champion['lookback']}/s{champion['skip']}/k{champion['top_k']}",
        "composite_net_sharpe_10bps": round(sharpe(composite[window]), 4),
        "composite_ann_return_10bps": round(ann_return(composite[window]), 6),
        "ew9_net_sharpe_10bps": round(sharpe(ew9_r[window]), 4),
        "spy_sharpe": round(sharpe(spy_ret[window]), 4),
        "capm_alpha_ann": round(reg["alpha"] * 252, 6),
        "capm_beta": round(reg["beta"], 4),
        "newey_west_t_alpha": round(t_alpha, 3),
        "break_even_cost_bps": round(c_star, 2),
    }
    with open("results/design_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerows([summary])

    # ------------------------------------------------------------------ plots
    from src.plots import fig_cost_sensitivity, fig_grid_heatmap, fig_nav

    comp_sharpes = []
    for c in COST_GRID:
        comp_c = np.mean(np.stack([run_backtest(sect, dates, lb, sk, k, c)["net_returns"]
                                   for (lb, sk, k) in cell_returns_10bps]), axis=0)
        comp_sharpes.append(sharpe(comp_c[window]))
    fig_cost_sensitivity(COST_GRID, comp_sharpes, c_star, "figures/fig1_cost_sensitivity.png")

    combos = [(s, k) for s in SKIPS for k in TOPKS]
    grid = np.array([[next(r["net_sharpe"] for r in ten
                          if r["lookback"] == lb and r["skip"] == s and r["top_k"] == k)
                      for (s, k) in combos] for lb in LOOKBACKS])
    fig_grid_heatmap(grid, LOOKBACKS, combos, "figures/fig2_grid_heatmap.png")

    nav = lambda r: np.cumprod(1.0 + r[window])  # noqa: E731
    fig_nav(dates[latest_start + 1:], nav(composite), nav(ew9_r), nav(spy_ret),
            "figures/fig3_nav.png")

    # ------------------------------------------------------------------ report
    print("=== DESIGN PERIOD (2000-2015), stats from", dates[latest_start + 1].date(), "===")
    for k, v in summary.items():
        print(f"{k:32s} {v}")


if __name__ == "__main__":
    main()
