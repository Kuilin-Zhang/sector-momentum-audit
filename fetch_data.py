# fetch_data.py

from pathlib import Path

import yfinance as yf


# 9 sector ETFs plus SPY, 10 tickers in total
TICKERS = [
    "XLB",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
    "SPY",
]


def main() -> None:
    # The end date is exclusive, so use 2016-01-01 to include 2015-12-31
    prices = yf.download(
        tickers=TICKERS,
        start="2000-01-01",
        end="2016-01-01",
        auto_adjust=True,
    )

    # Extract adjusted closing prices
    close = prices["Close"]

    # Create the data directory if it does not exist
    output_path = Path("data/prices_design.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the data and print basic validation checks
    close.to_csv(output_path)

    print("Shape:")
    print(close.shape)

    print("\nFirst and last dates:")
    print(close.index[0], close.index[-1])

    print("\nMissing values by ticker:")
    print(close.isna().sum())


if __name__ == "__main__":
    main()
