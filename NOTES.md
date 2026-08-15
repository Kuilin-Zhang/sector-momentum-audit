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

## 2026-08-15 — Amendment: anchor-check tolerance calibration (before any holdout data landed)

First execution of fetch_holdout.py stopped at the overlap-ratio assertion:
observed per-ticker relative variation 0.7-1.4e-6 against a 1e-6 threshold.
Diagnosis: Yahoo quote-rounding noise (both snapshots fetched the same day;
a genuine dividend-basis mismatch would be ~3e-3, three orders larger).
Threshold recalibrated to 5e-5. No holdout CSV was written and no holdout
statistic was computed before this change; the design-freeze tag was
re-pointed to the fix commit prior to publishing the Release.

## 2026-08-15 — THE holdout run (executed once)

- Code at execution: commit 53fcf7c (= design-freeze tag).
- data/prices_holdout.csv fetched this day, immediately before the run.
  Anchor-alignment factors: exactly 1.0 for all ten tickers (same-day
  fetch as the design snapshot). SHA-256: `520975140269befb64ad8fd9f88994b8850719e3df81f46b8631fac0abf1cb9e`
  Coverage: 2016-01-04..2025-12-31, 2514 trading days x 10 tickers,
  0 missing cells, 0 forward-filled.
- Verdict, per the pre-registered Section 11 rules:
    primary   : Cannot reject zero alpha. (alpha -1.06%/yr, NW t = -0.479)
    secondary : does NOT clear EW9 (composite 0.7219 vs EW9 0.7869)
    falsification: fires. Break-even cost -19.8 bps (alpha negative
    before costs) -> not implementable at 10 bps.
- No parameter, rule, or grid cell was changed after this run, and none
  will be (PROTOCOL.md Section 11).

## 2026-08-15 — Release ordering note

The design-freeze TAG was pushed to GitHub (server-side timestamp) before
the holdout was fetched or run; the Release UI entry for that same tag was
published later the same day. The binding timestamp is the tag push; the
Release page itself displays "2 commits to main since this release" — the
holdout commit and the README — making the freeze-then-open ordering
publicly visible.
