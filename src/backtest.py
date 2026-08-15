# src/backtest.py
#
# The heart of the repository. Implements PROTOCOL.md Sections 5-7:
# month-end rebalance, top-k equal weight, T+1 execution, drift between
# rebalances, half-sum turnover, cost deduction on the first accrual day.
# Explicit daily loop, chosen for auditability over speed (~0.4s per run).
#
# The three research-critical decisions below were answered from
# PROTOCOL.md before implementation (2026-08-15):
#   Q1  Weights formed at month-end index m take effect at the m+1 close;
#       their first PnL accrues from the m+1 close to the m+2 close.
#   Q2  turnover = 0.5 * sum_i |w_i,target - w_i,drift|
#   Q3  cost = turnover x rate is deducted from that first accrual
#       (m+1 close -> m+2 close) return.

import numpy as np

from src.signal import momentum_score


def month_end_indices(dates) -> list:
    """Indices of the last actual trading day of each month.

    Derived from the dates themselves: index i is a month end iff the next
    trading day belongs to a different (year, month). resample/date_range
    are forbidden - they can produce days that never traded.
    """
    idx = []
    for i in range(len(dates) - 1):
        if (dates[i].year, dates[i].month) != (dates[i + 1].year, dates[i + 1].month):
            idx.append(i)
    idx.append(len(dates) - 1)
    return idx


def select_top_k(score_row: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k largest scores in one cross-sectional row.

    Stable sort on the negated scores: ties keep the fixed column order,
    which IS the protocol's tie-break rule (Section 4).
    """
    order = np.argsort(-score_row, kind="stable")
    return order[:k]


def run_with_scores(prices: np.ndarray, dates, scores: np.ndarray,
                    top_k: int, cost_bps: float) -> dict:
    """Generic engine: any score matrix in, PnL ledger out.

    Used by run_backtest (momentum scores) and ew9_benchmark (constant
    scores). ret[t] is the return accrued from close t-1 to close t.
    A rebalance scheduled at month-end m executes at the close of t = m+1
    (Q1); its cost lands in ret[m+2] via pending_cost (Q3).
    """
    T, N = prices.shape
    rate = cost_bps / 1e4

    # Map execution day -> selected column indices. A month-end signal row
    # with any NaN is not yet valid (all-or-nothing, Section 4): no trade.
    exec_days = {}
    for m in month_end_indices(dates):
        if m + 1 >= T:
            continue
        row = scores[m]
        if np.isnan(row).any():
            continue
        exec_days[m + 1] = select_top_k(row, top_k)

    w = np.zeros(N)                # weights as of the latest close; cash = 1 - sum(w)
    weights = np.zeros((T, N))     # weights effective at each close
    ret = np.zeros(T)              # ret[t]: close t-1 -> close t, net of costs
    turnovers = []
    pending_cost = 0.0
    start_index = None

    for t in range(1, T):
        rel = prices[t] / prices[t - 1]
        gross = w @ rel + (1.0 - w.sum())          # cash earns rf = 0 (Section 7)
        ret[t] = gross - 1.0 - pending_cost        # Q3: cost hits the first accrual day
        pending_cost = 0.0

        # Drift: shares held fixed, weights move with returns (Section 5).
        if gross > 0:
            w = w * rel / gross

        # Execution at the close of t (t = m+1 for a valid month-end m). Q1.
        if t in exec_days:
            target = np.zeros(N)
            target[exec_days[t]] = 1.0 / top_k
            turnover = 0.5 * np.abs(target - w).sum()   # Q2: half-sum vs drifted
            turnovers.append(turnover)
            pending_cost = turnover * rate              # lands in ret[t+1]
            w = target
            if start_index is None:
                start_index = t
        weights[t] = w

    nav = np.cumprod(1.0 + ret)
    return {"net_returns": ret, "nav": nav, "weights": weights,
            "turnovers": turnovers, "start_index": start_index}


def run_backtest(prices: np.ndarray, dates, lookback: int, skip: int,
                 top_k: int, cost_bps: float) -> dict:
    """Run one grid cell on the given (sector-only) price panel."""
    scores = momentum_score(prices, lookback, skip)
    return run_with_scores(prices, dates, scores, top_k, cost_bps)


def ew9_benchmark(prices: np.ndarray, dates, cost_bps: float) -> dict:
    """EW9: every column equal weight, same monthly schedule, same cost
    model on its own turnover (PROTOCOL.md Section 8). Implemented as the
    same engine fed constant scores valid from day one."""
    ones = np.ones_like(prices)
    return run_with_scores(prices, dates, ones, prices.shape[1], cost_bps)
