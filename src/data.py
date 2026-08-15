# src/data.py
#
# Data layer: the only file in this repository where pandas touches prices.
# It loads the committed snapshot, applies the data policy of PROTOCOL.md
# Section 3, and hands everything downstream as plain numpy + lists.
# All time shifts below this layer use explicit integer indexing.

import pandas as pd

DESIGN_CSV = "data/prices_design.csv"


def load_prices(csv_path: str = DESIGN_CSV):
    """Load the committed price snapshot and apply the Section 3 data policy.

    Policy (PROTOCOL.md Section 3):
      1. Align all series on SPY's trading days.
      2. Count remaining missing cells BEFORE filling (reported in NOTES.md).
      3. Forward-fill missing sector closes. Backward filling is forbidden:
         it would import future information.

    Returns
    -------
    dates   : list of pandas.Timestamp, length T
    prices  : numpy.ndarray, shape (T, N)
    tickers : list of str, length N
    n_filled: int, number of cells that were forward-filled
    """
    # 1. Read the snapshot. The first column is the date index and must be
    #    parsed as real dates, not strings.
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    # 2. Align on SPY's trading days: keep only rows where SPY has a price.
    df = df.loc[df["SPY"].notna()].copy()

    # 3. Count missing cells BEFORE filling.
    n_filled = df.isna().sum().sum()

    # 4. Forward-fill the gaps.
    df = df.ffill()

    # 5. Hand over to numpy: from here on, no more pandas downstream.
    dates = list(df.index)
    tickers = df.columns.tolist()
    prices = df.to_numpy(dtype=float)

    return dates, prices, tickers, int(n_filled)


if __name__ == "__main__":
    dates, prices, tickers, n_filled = load_prices()
    print("T x N:", prices.shape)
    print("first/last:", dates[0].date(), dates[-1].date())
    print("tickers:", tickers)
    print("cells forward-filled:", n_filled)
    # Contract asserts: fail loudly if the data policy is violated.
    assert prices.shape[0] == len(dates)
    assert prices.shape[1] == len(tickers) == 10
    import numpy as np
    assert not np.isnan(prices).any(), "NaNs survived the fill policy"
