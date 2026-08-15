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
    raise NotImplementedError("Block 1 - you write this")
