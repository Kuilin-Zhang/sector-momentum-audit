# src/stats.py
#
# Hand-written OLS + Newey-West, PROTOCOL.md Section 11. statsmodels
# appears ONLY in tests, as an independent oracle to cross-check against
# (tests/test_contract.py asserts agreement).
#
# The normal-equation solution below was stated from memory before
# implementation (2026-08-15): beta_hat = (X'X)^{-1} X'y, with the
# all-ones first column carrying the intercept, so coef[0] = alpha and
# coef[1] = beta.

import numpy as np


def ols(y: np.ndarray, x: np.ndarray) -> dict:
    """Regress y on [1, x] by solving the normal equations directly."""
    X = np.column_stack([np.ones(len(x)), x])
    inv_xtx = np.linalg.inv(X.T @ X)
    coef = inv_xtx @ X.T @ y            # (X'X)^{-1} X'y
    residuals = y - X @ coef
    return {
        "alpha": float(coef[0]),
        "beta": float(coef[1]),
        "residuals": residuals,
        "X": X,
        "inv_xtx": inv_xtx,
    }


def newey_west_tstat(ols_result: dict, lag: int = 21) -> float:
    """HAC t-statistic of alpha, Bartlett weights, lag daily lags.

    Sandwich estimator: cov = (X'X)^{-1} S (X'X)^{-1} with
    S = Gamma_0 + sum_{l=1..lag} w_l (Gamma_l + Gamma_l'),
    w_l = 1 - l/(lag+1), Gamma_l = sum_t (u_t x_t)(u_{t-l} x_{t-l})'.
    Daily returns are autocorrelated; a plain OLS t would overstate
    significance. No small-sample correction (disclosed; the test oracle
    is run with use_correction=False to match).
    """
    X = ols_result["X"]
    u = ols_result["residuals"][:, None] * X       # score contributions
    S = u.T @ u                                     # Gamma_0
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    cov = ols_result["inv_xtx"] @ S @ ols_result["inv_xtx"]
    se_alpha = float(np.sqrt(cov[0, 0]))
    return ols_result["alpha"] / se_alpha


def break_even_cost(alpha_at_zero: float, alpha_at_c: float, c: float) -> float:
    """Exact break-even round-trip cost c* where CAPM alpha = 0.

    Net returns are linear in the cost rate, hence alpha is linear in c:
    alpha(c) = alpha(0) + slope * c. Evaluate at 0 and at c, solve the
    line for zero (PROTOCOL.md Section 11) - no interpolation from the
    sweep.
    """
    slope = (alpha_at_c - alpha_at_zero) / c
    return float(-alpha_at_zero / slope)
