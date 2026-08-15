# fetch_holdout.py
#
# PROTOCOL.md Section 3: the holdout snapshot (2016-01-01 onward) is fetched
# ONLY on the day of the pre-registered holdout run and committed in the
# same commit as the holdout results. Running this script IS the opening of
# the box. Do not run it before the design-freeze tag exists.
#
# Anchor alignment (NOTES.md amendment, 2026-08-15, pre-freeze): yfinance
# auto_adjust anchors adjusted prices to the fetch date. If any dividend
# occurs between the design fetch and the holdout fetch, the two snapshots
# sit on different adjustment bases and every cross-boundary return and
# signal is contaminated. Therefore this script fetches an overlap month
# (from 2015-12-01), verifies the design/holdout ratio is a per-ticker
# CONSTANT over the overlap (pure basis rescale), rescales the holdout
# frame back onto the design basis, and only then writes rows dated
# 2016-01-01 onward. If no dividend occurred between fetches the factors
# are exactly 1 and this is a no-op.

from pathlib import Path

import pandas as pd
import yfinance as yf

from fetch_data import TICKERS


def main() -> None:
    # end is exclusive, so use 2026-01-01 to include 2025-12-31
    prices = yf.download(
        tickers=TICKERS,
        start="2015-12-01",           # overlap month for anchor alignment
        end="2026-01-01",
        auto_adjust=True,
    )
    raw = prices["Close"]

    design = pd.read_csv("data/prices_design.csv", index_col=0, parse_dates=True)
    overlap = design.index.intersection(raw.index)
    assert len(overlap) >= 15, f"overlap too short: {len(overlap)} days"

    ratio = design.loc[overlap] / raw.loc[overlap]
    rel_var = (ratio.max() - ratio.min()) / ratio.mean()
    # Tolerance calibration (NOTES.md, 2026-08-15): Yahoo quote rounding
    # makes this ratio wobble at ~1e-6 even for same-day fetches (observed
    # 0.7-1.4e-6); a dividend-sized basis mismatch is ~3e-3. 5e-5 sits 35x
    # above the noise floor and 60x below the dividend scale.
    assert (rel_var.abs() < 5e-5).all(), (
        "design/holdout ratio is not constant over the overlap - this is "
        f"not a pure basis rescale; investigate before proceeding:\n{rel_var}"
    )
    factors = ratio.mean()
    rescaled = raw * factors

    out = rescaled.loc[rescaled.index > design.index[-1]]
    output_path = Path("data/prices_holdout.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path)

    print("Anchor-alignment factors (1.0 = same basis):")
    print(factors.round(8))
    print("\nShape written (2016-01-01 onward):")
    print(out.shape)
    print("\nFirst and last dates:")
    print(out.index[0], out.index[-1])
    print("\nMissing values by ticker:")
    print(out.isna().sum())


if __name__ == "__main__":
    main()
