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


def composite_and_window(cells):
    """Grid composite (PROTOCOL.md Section 11) and its statistics window.

    cells: list of dicts with 'start_index' and 'net_returns'. The window
    starts one day after the LAST cell becomes valid, so every cell is in
    the market for every day the statistics cover.
    """
    latest = max(c["start_index"] for c in cells)
    comp = np.mean(np.stack([c["net_returns"] for c in cells]), axis=0)
    return comp, slice(latest + 1, None)


def main() -> None:
    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]
    spy = prices[:, tickers.index(MARKET)]
    spy_ret = np.zeros(len(spy))
    spy_ret[1:] = spy[1:] / spy[:-1] - 1.0

    Path("results").mkdir(exist_ok=True)
    Path("figures").mkdir(exist_ok=True)

    # ------------------------------------------------------------------ grid
    rows = []                       # full precision throughout; CSV is the artifact
    cells_10bps = []
    for lb in LOOKBACKS:
        for sk in SKIPS:
            for k in TOPKS:
                for c in COST_GRID:
                    res = run_backtest(sect, dates, lb, sk, k, c)
                    s0 = res["start_index"]
                    r = res["net_returns"][s0 + 1:]
                    reg = ols(r, spy_ret[s0 + 1:])          # per-cell CAPM,
                    t_a = newey_west_tstat(reg, lag=21)     # descriptive only (S11)
                    rows.append({
                        "lookback": lb, "skip": sk, "top_k": k, "cost_bps": c,
                        "start_date": dates[s0].date(),
                        "ann_return": ann_return(r),
                        "ann_vol": ann_vol(r),
                        "net_sharpe": sharpe(r),
                        "max_drawdown": max_drawdown(res["nav"][s0:]),
                        "ann_turnover": sum(res["turnovers"]) / (len(r) / 252.0),
                        "capm_alpha_ann": reg["alpha"] * 252,
                        "capm_beta": reg["beta"],
                        "nw_t_alpha": t_a,
                    })
                    if c == HEADLINE_COST:
                        cells_10bps.append({"key": (lb, sk, k),
                                            "start_index": s0,
                                            "net_returns": res["net_returns"]})

    with open("results/grid_design.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # --------------------------------------------------- composite + baselines
    composite, window = composite_and_window(cells_10bps)
    latest_start = window.start - 1

    ew9 = ew9_benchmark(sect, dates, HEADLINE_COST)
    ew9_r = ew9["net_returns"]

    # Design-period CAPM of the composite vs SPY (descriptive here; the
    # binding inference happens once, on the holdout - Section 11).
    reg = ols(composite[window], spy_ret[window])
    t_alpha = newey_west_tstat(reg, lag=21)

    # Break-even cost: alpha is linear in c; evaluate at 0 and 50 bps.
    def composite_at(cost):
        return np.mean(np.stack(
            [run_backtest(sect, dates, lb, sk, k, cost)["net_returns"]
             for (lb, sk, k) in [c["key"] for c in cells_10bps]]), axis=0)

    a0 = ols(composite_at(0.0)[window], spy_ret[window])["alpha"]
    a50 = ols(composite_at(50.0)[window], spy_ret[window])["alpha"]
    c_star = break_even_cost(a0, a50, 50.0)

    # In-sample champion (Section 3): highest design net Sharpe at 10 bps
    # on FULL-PRECISION values (rounding first could fake a tie), ties
    # broken by smaller lookback, then smaller top_k, then skip=21.
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

    comp_sharpes = [sharpe(composite_at(c)[window]) for c in COST_GRID]
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
