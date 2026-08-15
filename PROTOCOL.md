# Research Protocol

Pre-registered on 2026-08-15, before any backtest code was written.

## 1. Research question

How much alpha, if any, survives in a sector-momentum strategy on US sector
ETFs after accounting for (a) transaction costs, (b) market beta, and
(c) selection across a 24-cell parameter grid?

## 2. Universe

The universe is the nine original SPDR sector ETFs, all listed on the same
day (1998-12-16): XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY.

An investor in December 1998 could have formed this exact list using only
information available on that day — no part of the selection rule depends on
hindsight. Moreover, none of the nine funds has ever been delisted, so the
sample is free of survivorship gaps by construction.

XLRE (listed 2015) and XLC (listed 2018) are deliberately excluded. Adding
them mid-sample would change the meaning of a cross-sectional rank partway
through the backtest (top-3 of 9 is not top-3 of 11) and would leave the
panel unbalanced for no benefit.

This exclusion does not leave sectors uncovered: real estate stocks lived
inside XLF until 2015, and communications stocks inside XLK and XLY until
2018, so the nine funds spanned the full market throughout the sample.

## 3. Sample period and data

Daily adjusted closes, 2000-01-01 through 2025-12-31, for the nine sector
ETFs and SPY. Source: Yahoo Finance via yfinance with auto_adjust=True.

**Snapshot policy (also part of the run-once mechanism, Section 11).** The
data are committed in two separate snapshots:

- `data/prices_design.csv` — through 2015-12-31 — fetched once, within seven
  days of this protocol's commit, and committed alongside the early code.
  Its SHA-256 is recorded in NOTES.md.
- `data/prices_holdout.csv` — 2016-01-01 onward — fetched only on the day of
  the pre-registered holdout run and committed in the same commit as the
  holdout results. Holdout prices never sit in the repository before that
  day.

The yfinance version is pinned in requirements.txt. Any refetch requires a
dated amendment in NOTES.md, written before the holdout run, with the
difference explained. Every number in this study is reproducible from the
committed snapshots with no network access; the fetch script exists only to
generate snapshots and is not part of the default pipeline.

Data alignment: all series are aligned on SPY's trading days. A missing
sector close on an SPY trading day is forward-filled, and the count of
filled cells is reported in NOTES.md.

**Sample split, fixed in advance.**

- Design period: 2000-01-01 to 2015-12-31. Used to build and debug the
  pipeline and to produce the design-period version of every table in
  Sections 10-11. It also produces one labeled object: the *in-sample
  champion*, the cell with the highest design-period net Sharpe at 10 bps
  (ties broken by smaller lookback, then smaller top_k, then skip = 21).
  The champion's holdout performance is reported next to the grid median
  solely to measure selection shrinkage. No other design-period quantity
  feeds any holdout claim.
- Holdout period: 2016-01-01 to 2025-12-31. Run once. See Section 11.

**Holdout boundary.** The strategy runs continuously from 2000. The holdout
return series consists of every daily accrual dated 2016-01-01 through
2025-12-31, including the PnL of positions formed at the final
design-period rebalance in December 2015. No warm-up exclusion.

## 4. Signal

For each ETF i and day t:

    signal_i(t) = AdjClose_i(t - skip) / AdjClose_i(t - lookback) - 1

with offsets in trading days on the aligned calendar; lookback > skip holds
in every grid cell. When skip = 21, the most recent month is excluded — the
standard guard against short-term reversal (the "12-1" convention of
Jegadeesh and Titman). Ranking is invariant to log versus simple returns.

A signal is valid at day t iff the committed snapshot contains adjusted
closes at both t - lookback and t - skip. Because all nine ETFs share one
data start, validity is all-or-nothing across the nine. Ties in the
cross-sectional rank are broken by fixed ticker order (XLB, XLE, XLF, XLI,
XLK, XLP, XLU, XLV, XLY), so portfolio membership is deterministic.

## 5. Portfolio construction

On the last actual trading day of each month, rank the nine ETFs by signal
and hold the top-k, equally weighted. **Weights are reset to 1/k at every
rebalance, even when membership is unchanged**; between rebalances, shares
are held fixed and weights drift with returns. No shorting, no leverage.

Before the first rebalance at which signals are valid (early design period;
validity is all-or-nothing per Section 4), the portfolio holds 100% cash.
Each cell's performance is measured from its first valid rebalance onward;
because longer lookbacks start later, each cell's start date is a column in
results/grid.csv. The holdout period is unaffected (full history available).

## 6. Timing contract

| Step | When | Price involved |
|---|---|---|
| Compute momentum signal | day t, after the close | closes up to and including t |
| Select top-k portfolio | day t, after the close | — |
| New weights take effect | day t+1, at the close | close of t+1 |
| First PnL accrues | t+1 close to t+2 close | close-to-close |

**Why a one-day lag — not zero, not two.** A zero-day lag would execute at
the very close the signal is computed from — a price that is already history
by the time the signal exists. A two-day lag would remove no additional bias
(every piece of information used is public a full day before execution) while
trading on a stale signal. One day is the minimum lag that eliminates
lookahead entirely; any further delay buys nothing and costs signal freshness.

Execution is assumed at the t+1 close rather than the t+1 open: adjusted open
prices from free data sources are unreliable, a single close-to-close price
series keeps the ledger consistent, and the later execution is the
conservative side of the ambiguity.

## 7. Transaction costs and metrics

**Turnover.** At each rebalance executed at the t+1 close:

    turnover = (1/2) * sum_i | w_i,target - w_i,drift |

where w_drift are the previous target weights carried forward by realized
returns through the t+1 close, and w_target are the new equal weights.
Pulling drifted weights back to 1/k counts as turnover even when membership
is unchanged. Under this half-sum convention, replacing one name in a top-3
book costs approximately 1/3 of the round-trip rate.

**Costs.** Cost = turnover × round-trip rate, deducted from the strategy
return over the first accrual day of the new weights (t+1 close to t+2
close). Rates are swept over {0, 2, 5, 10, 20, 50} basis points; headline
figures use 10 bps. EW9 (Section 8) is charged under the identical formula
on its own rebalancing turnover.

**Sharpe.** For any return series in this study:

    Sharpe = mean(r_daily) / std(r_daily, ddof=1) * sqrt(252)

computed on daily close-to-close net returns over the stated window.
Reported alphas are daily alpha × 252. These conventions apply to every
cell, the composite, EW9, and SPY.

**Risk-free rate.** rf ≡ 0 throughout. This overstates Sharpe ratios by
roughly 0.1 and is disclosed as a limitation rather than patched, to keep
the pipeline free of a second data dependency. Consequently "excess return"
in this study means the raw net return.

## 8. Benchmarks

The honest benchmark is EW9: all nine ETFs equally weighted, rebalanced on
the same monthly schedule as the strategy, and charged transaction costs on
its own turnover under the Section 7 formula. Any claim of sector-selection
skill must clear EW9, not SPY — comparing a sector rotation to SPY would
credit the strategy for the sector universe itself. The operational meaning
of "clears EW9" is pre-committed in Section 11 (secondary judgment). SPY
enters only as the market factor in the CAPM regression.

## 9. Parameter grid (frozen)

- lookback ∈ {63, 126, 189, 252} trading days — 3, 6, 9, and 12 months,
  the range the momentum literature considers standard.
- skip ∈ {0, 21} — with and without the short-term-reversal guard.
- top_k ∈ {2, 3, 4} — a reasonable concentration range in a nine-asset
  universe; k = 4 already approaches the equal-weight benchmark.

4 × 2 × 3 = 24 configurations. This grid is frozen before any backtest runs.
No cell may be added or removed after results are observed: the grid itself
is a researcher degree of freedom, and expanding it after peeking would
reintroduce selection bias through the back door.

## 10. Reporting rule

The headline number is the MEDIAN net Sharpe across the 24-cell grid, in the
holdout period, at 10 bps. I report the median, because the best cell is
exactly what in-sample selection would have handed me. All 24 cells are
published in results/grid.csv; the best cell and the in-sample champion
(Section 3) are reported alongside, clearly labeled, but never as the
headline. Formal inference runs on the grid composite defined in Section 11.

## 11. Decision rule (pre-committed)

**Primary series.** All Section 11 tests run on the *grid composite*: the
equally weighted average of the 24 cells' daily net return series, each at
10 bps. The composite is the family-level claim made testable — it depends
on no selection. Per-cell regressions appear in results/grid.csv as
descriptive statistics only and support no headline claim.

**Primary judgment.** CAPM regression on daily returns over the holdout
period:

    r_composite,d = alpha + beta * r_SPY,d + epsilon_d

Since rf ≡ 0 (Section 7), excess returns equal raw returns. Standard errors
are Newey-West with lag 21 (21 daily lags, approximately one month).

| Outcome | Conclusion |
|---|---|
| alpha > 0 and Newey-West \|t\| >= 2.0 | "Alpha survives costs and beta." |
| Newey-West \|t\| < 2.0 | "Cannot reject zero alpha." |
| alpha < 0 and \|t\| >= 2.0 | Significantly negative; reported as such. |

**Secondary judgment (the operational meaning of "clears EW9").**
Sector-selection skill is claimed only if BOTH (a) the primary judgment
passes AND (b) the composite's holdout net Sharpe exceeds EW9's holdout net
Sharpe, both at 10 bps with EW9 charged its own costs.

**Falsification clause.** The break-even round-trip cost c* is the cost rate
at which the composite's holdout CAPM alpha equals zero. Because net returns
are linear in the cost rate, c* is solved exactly, not interpolated from the
sweep. If c* < 10 bps, the strategy is declared not implementable at
realistic costs, regardless of the t-statistic at any cost level.

**Run-once mechanism.** The holdout will be run exactly once. Before the
holdout script is first executed: the design-period analysis is complete and
committed, the repository is tagged `design-freeze`, and the tag is pushed
to GitHub and published as a Release (a server-side timestamp that cannot be
forged locally). The holdout data (`data/prices_holdout.csv`) is fetched
only on that day and committed together with the holdout results; NOTES.md
records the date and commit hash. The holdout numbers must be exactly
reproducible by running the pipeline against the `design-freeze` code.

I cannot prove I never peeked; what this mechanism proves is that peeking
could not have changed anything, because every definition in this protocol
is closed before the freeze.

**After the holdout is opened**, no parameter, rule, or grid cell changes.
Any new idea requires a new pre-registered protocol (v2), and the results of
this protocol remain in the README unchanged.
