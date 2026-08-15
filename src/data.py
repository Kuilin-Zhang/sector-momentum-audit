# src/data.py
#
# Data layer: the only file in this repository where pandas touches prices.
# It loads the committed snapshot, applies the data policy of PROTOCOL.md
# Section 3, and hands everything downstream as plain numpy + lists.
# All time shifts below this layer use explicit integer indexing.

import pandas as pd

DESIGN_CSV = "data/prices_design.csv"

# The nine-sector universe (PROTOCOL.md Section 2) in fixed ticker order —
# this order is also the cross-sectional tie-break. SPY is the benchmark
# factor, never a member of the momentum universe.
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
MARKET = "SPY"


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


HOLDOUT_CSV = "data/prices_holdout.csv"


def load_full(design_csv: str = DESIGN_CSV, holdout_csv: str = HOLDOUT_CSV):
    """Design + holdout snapshots concatenated, same Section 3 policy.

    Used only by run_holdout.py after the box is opened. The strategy runs
    continuously from 2000 (Section 3, holdout boundary); the holdout
    STATISTICS window is selected downstream by date.
    """
    a = pd.read_csv(design_csv, index_col=0, parse_dates=True)
    b = pd.read_csv(holdout_csv, index_col=0, parse_dates=True)
    df = pd.concat([a, b])
    assert df.index.is_monotonic_increasing, "snapshots overlap or are out of order"
    assert df.index.is_unique, "duplicate dates across snapshots"

    df = df.loc[df["SPY"].notna()].copy()
    n_filled = int(df.isna().sum().sum())
    df = df.ffill()

    # Splice sanity: both snapshots were fetched with the same adjustment
    # anchor; the first cross-boundary daily move must therefore be a normal
    # market move, not an adjustment jump.
    boundary = df.index.searchsorted(b.index[0])
    splice_move = df.iloc[boundary].to_numpy() / df.iloc[boundary - 1].to_numpy() - 1.0
    assert (abs(splice_move) < 0.15).all(), f"splice jump detected: {splice_move}"
    # Last line of defence only: the real basis check is the overlap-ratio
    # assertion in fetch_holdout.py, which CAN tell a dividend-sized basis
    # mismatch from a genuine market move. This one cannot.

    assert int(df.isna().sum().sum()) == 0, "NaNs survived the fill policy"
    return list(df.index), df.to_numpy(dtype=float), df.columns.tolist(), n_filled


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
