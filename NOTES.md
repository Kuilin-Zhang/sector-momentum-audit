# NOTES

Operational log required by PROTOCOL.md. Append-only.

## 2026-08-15 — Design-period snapshot fetched

- File: `data/prices_design.csv`
- Fetched: 2026-08-15, via `fetch_data.py` (yfinance 1.6.0, pinned in requirements.txt)
- Coverage: 2000-01-03 to 2015-12-31, 4025 trading days x 10 tickers
- Missing values after download: 0 across all tickers (no forward-filling was needed)
- SHA-256: `151e292675e123b3c7c0f591f74849e9134e3b3eacfaab1ac2e59f0d3a8bb328`
- Size: 789,825 bytes

Per PROTOCOL.md Section 3, the holdout snapshot (`data/prices_holdout.csv`,
2016-01-01 onward) will be fetched only on the day of the pre-registered
holdout run.
