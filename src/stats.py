# src/stats.py
#
# Hand-written OLS + Newey-West, PROTOCOL.md Section 11. statsmodels/scipy
# appear ONLY in tests, as an independent oracle to cross-check against
# (tests/test_stats.py asserts agreement to 1e-8).

import numpy as np


def ols(y: np.ndarray, x: np.ndarray) -> dict:
    """Regress y on [1, x] by solving the normal equations directly.

    Returns dict with: alpha, beta, residuals, and the (2,2) matrix
    inv(X'X) needed by newey_west below.
    """
    raise NotImplementedError("Block 3 - you write this")


def newey_west_tstat(residuals: np.ndarray, x: np.ndarray,
                     inv_xtx: np.ndarray, lag: int = 21) -> float:
    """HAC t-statistic of alpha with Bartlett weights, lag = 21 daily lags.

    Corrects the alpha standard error for autocorrelation in daily returns;
    a plain OLS t would overstate significance.
    """
    raise NotImplementedError("Block 3 - you write this")


def break_even_cost(gross_alpha_fn) -> float:
    """Exact break-even round-trip cost c* where holdout CAPM alpha = 0.

    Net returns are linear in the cost rate, hence alpha is linear in c:
    evaluate alpha at two cost levels and solve the line for zero
    (PROTOCOL.md Section 11) - no interpolation from the sweep.
    """
    raise NotImplementedError("Block 3 - you write this")
