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

## 2026-08-15 — Pre-freeze amendment: adversarial review fixes

A four-lens adversarial code review was run before the design freeze.
Engine verified clean line-by-line; twelve defensive fixes were applied,
all BEFORE any holdout data existed:

1. Anchor alignment for the holdout fetch (the one blocker): yfinance
   auto_adjust anchors prices to the fetch date, so the two snapshots
   could sit on different adjustment bases if a dividend occurred between
   fetches. fetch_holdout.py now fetches an overlap month (from
   2015-12-01), asserts the design/holdout ratio is a per-ticker constant
   (< 1e-6 relative variation), rescales onto the design basis, and writes
   only rows dated 2016-01-01 onward. If no dividend occurred between
   fetches the factors are exactly 1.0.
2. Champion/median selection now uses full-precision Sharpe (rounding
   first could fake a tie); grid CSVs store full precision.
3. Per-cell CAPM columns added to grid CSVs (Section 11 deliverable).
4. Trades whose first accrual day would fall outside the sample are
   skipped (their cost could never land).
5. Four new contract tests: hand-computed golden ledger, affine-in-cost
   linearity (underpins the exact break-even solve), composite window
   placement, tie-break determinism. Suite: 11 passed.

Design-period headline numbers unchanged by these fixes
(median 0.4031 at full precision, champion lb126/s21/k4).
