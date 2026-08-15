# src/metrics.py
#
# Performance metrics, PROTOCOL.md Section 7. Every ratio in the study is
# computed from daily net returns with these exact conventions:
#   Sharpe = mean(r_d) / std(r_d, ddof=1) * sqrt(252)
#   annualized return = mean(r_d) * 252         (arithmetic, disclosed)
#   annualized alpha  = daily alpha * 252

import numpy as np


def sharpe(daily_returns: np.ndarray) -> float:
    """PROTOCOL.md Section 7 definition. ddof=1, sqrt(252)."""
    return float(np.mean(daily_returns) / np.std(daily_returns, ddof=1) * np.sqrt(252))


def ann_return(daily_returns: np.ndarray) -> float:
    return float(np.mean(daily_returns) * 252)


def ann_vol(daily_returns: np.ndarray) -> float:
    return float(np.std(daily_returns, ddof=1) * np.sqrt(252))


def max_drawdown(nav: np.ndarray) -> float:
    """Most negative peak-to-trough decline of the NAV path, as a negative
    fraction (e.g. -0.34)."""
    peak = np.maximum.accumulate(nav)
    return float((nav / peak - 1.0).min())
