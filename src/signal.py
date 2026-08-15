# src/signal.py
#
# Momentum signal, PROTOCOL.md Section 4:
#   signal_i(t) = AdjClose_i(t - skip) / AdjClose_i(t - lookback) - 1
# Pure numpy with explicit integer offsets. No pandas below the data layer.

import numpy as np


def momentum_score(prices: np.ndarray, lookback: int, skip: int) -> np.ndarray:
    """Cross-sectional momentum with a short-term-reversal skip.

    Parameters
    ----------
    prices   : (T, N) adjusted closes from data.load_prices
    lookback : offset in trading days (63 / 126 / 189 / 252)
    skip     : offset in trading days (0 / 21); lookback > skip always

    Returns
    -------
    scores : (T, N) array. Row t holds signal_i(t); rows t < lookback are
             np.nan (signal not yet valid, PROTOCOL.md Section 4).
    """
    T, N = prices.shape
    scores = np.full((T, N), np.nan)
    # Derivation (worked out by hand on a T=6, lookback=3, skip=1 example):
    # as t runs over [lookback, T), the numerator row t-skip sweeps
    # [lookback-skip, T-skip) and the denominator row t-lookback sweeps
    # [0, T-lookback). Both slices have length T-lookback.
    scores[lookback:] = prices[lookback - skip : T - skip] / prices[0 : T - lookback] - 1
    return scores
