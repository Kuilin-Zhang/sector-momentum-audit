# src/backtest.py
#
# The heart of the repository. Implements PROTOCOL.md Sections 5-7:
# month-end rebalance, top-k equal weight, T+1 execution, drift between
# rebalances, half-sum turnover, cost deduction on the first accrual day.
# Explicit daily loop, chosen for auditability over speed (~0.4s per run).

import numpy as np


def month_end_indices(dates) -> list:
    """Indices of the last actual trading day of each month.

    PROTOCOL.md Section 5. Implementation constraint: derive month labels
    from the dates themselves (year, month); resample/date_range are
    forbidden - they can produce days that never traded.
    """
    raise NotImplementedError("Block 2 - you write this")


def select_top_k(score_row: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k largest scores in one cross-sectional row.

    Ties broken by fixed ticker order (PROTOCOL.md Section 4) - numpy's
    stable argsort over the fixed column order gives exactly that.
    """
    raise NotImplementedError("Block 2 - you write this")


def run_backtest(prices: np.ndarray, dates, lookback: int, skip: int,
                 top_k: int, cost_bps: float) -> dict:
    """Run one grid cell. Returns a dict with:

    net_returns : (T,) daily net returns of the strategy (0.0 before start)
    nav         : (T,) cumulative NAV starting at 1.0
    turnover    : total two-way turnover / 2 summed over rebalances
    start_index : first index at which signals were valid

    Timing contract (PROTOCOL.md Section 6):
      signal at t close -> weights effective at t+1 close -> first PnL
      accrues t+1 close to t+2 close. Cost = turnover_t x cost_bps, deducted
      from the first accrual day of the new weights.
    """
    raise NotImplementedError("Block 2 - you write this")


def ew9_benchmark(prices: np.ndarray, dates, cost_bps: float) -> dict:
    """EW9: all nine sectors equal weight, same monthly schedule, same cost
    model on its own turnover (PROTOCOL.md Section 8). Same return keys as
    run_backtest."""
    raise NotImplementedError("Block 2 - you write this")
