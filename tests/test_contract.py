# tests/test_contract.py
#
# Research-invariant tests, PROTOCOL.md + frozen spec Section 6.
# These test the RESEARCH, not toy functions. Every test name states the
# invariant it defends. All start skipped; each block un-skips its own.

import numpy as np
import pandas as pd
import pytest

from src.data import load_prices
from src.signal import momentum_score


def test_data_contract_shape_and_no_nans():
    """load_prices returns (T,10), no NaNs after the fill policy,
    dates strictly increasing."""
    dates, prices, tickers, n_filled = load_prices()
    assert prices.shape == (len(dates), 10)
    assert len(tickers) == 10
    assert not np.isnan(prices).any()
    assert all(dates[i] < dates[i + 1] for i in range(len(dates) - 1))


def test_monotone_asset_gets_top_rank():
    """On a synthetic panel where one asset rises every day and the rest
    fall, that asset must hold the top momentum rank once signals are
    valid."""
    T, N, rising = 300, 4, 2
    prices = 100.0 * np.cumprod(np.full((T, N), 0.999), axis=0)  # all drift down
    prices[:, rising] = 100.0 * 1.001 ** np.arange(T)            # one rises daily
    scores = momentum_score(prices, lookback=63, skip=21)
    assert np.isnan(scores[:63]).all()          # not yet valid -> NaN
    assert not np.isnan(scores[63:]).any()      # valid from lookback on
    winners = np.argmax(scores[63:], axis=1)
    assert (winners == rising).all()


def _sharpe(daily):
    return daily.mean() / daily.std(ddof=1) * np.sqrt(252)


def test_leakage_positive_control():
    """A deliberately cheating signal built from FUTURE returns must
    produce Sharpe > 3; the honest pipeline on the same data must stay
    below 2. If this test can't tell them apart, the harness is blind."""
    from src.backtest import run_with_scores, run_backtest

    rng = np.random.default_rng(42)
    T, N = 2000, 9
    daily = rng.normal(0.0003, 0.01, (T, N))     # pure random walk: no edge
    prices = 100.0 * np.cumprod(1.0 + daily, axis=0)

    # Cheating scores: today's signal is the NEXT month's realized return.
    cheat = np.full((T, N), np.nan)
    cheat[:-21] = prices[21:] / prices[:-21] - 1.0
    cheat[:63] = np.nan                          # same warm-up shape as honest

    cheat_res = run_with_scores(prices, _fake_dates(T), cheat, 3, 0.0)
    honest_res = run_backtest(prices, _fake_dates(T), 252, 21, 3, 0.0)

    s0 = cheat_res["start_index"]
    cheat_sharpe = _sharpe(cheat_res["net_returns"][s0 + 1:])
    h0 = honest_res["start_index"]
    honest_sharpe = _sharpe(honest_res["net_returns"][h0 + 1:])

    assert cheat_sharpe > 3.0, f"cheat Sharpe {cheat_sharpe:.2f} too low - harness is blind"
    assert abs(honest_sharpe) < 2.0, f"honest Sharpe {honest_sharpe:.2f} suspicious on a random walk"


def _fake_dates(T):
    """Synthetic weekday calendar for tests that need month boundaries."""
    return list(pd.bdate_range("2000-01-03", periods=T))


def test_zero_cost_full_hold_equals_ew9():
    """With cost = 0 and top_k = 9, the strategy IS the EW9 benchmark:
    NAV paths must agree to 1e-10 pointwise from the strategy's start.

    NOTE: strategy and EW9 share run_with_scores, so this test is blind to
    any bug common to both. Engine-level correctness is pinned by
    test_golden_ledger_one_cycle."""
    from src.backtest import run_backtest, ew9_benchmark
    from src.data import SECTORS

    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]

    strat = run_backtest(sect, dates, 63, 0, 9, 0.0)
    ew9 = ew9_benchmark(sect, dates, 0.0)

    s0 = strat["start_index"]
    ratio_s = strat["nav"][s0:] / strat["nav"][s0]
    ratio_e = ew9["nav"][s0:] / ew9["nav"][s0]
    assert np.max(np.abs(ratio_s - ratio_e)) < 1e-10


def test_single_rebalance_turnover_in_bounds():
    """Half-sum turnover of one rebalance lies in [0, 1]; weights row sums
    are 1 (invested) or 0 (cash)."""
    from src.backtest import run_backtest
    from src.data import SECTORS

    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]
    res = run_backtest(sect, dates, 252, 21, 3, 10.0)

    tv = np.array(res["turnovers"])
    assert len(tv) > 100                       # ~monthly over 16 years
    assert (tv >= 0.0).all() and (tv <= 1.0 + 1e-12).all()

    sums = res["weights"].sum(axis=1)
    invested = np.abs(sums - 1.0) < 1e-9
    cash = np.abs(sums) < 1e-12
    assert (invested | cash).all()


def test_net_sharpe_monotone_in_costs():
    """Net Sharpe must be non-increasing as the cost rate rises."""
    from src.backtest import run_backtest
    from src.data import SECTORS

    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]

    sharpes = []
    for c in [0.0, 10.0, 50.0]:
        res = run_backtest(sect, dates, 252, 21, 3, c)
        s0 = res["start_index"]
        sharpes.append(_sharpe(res["net_returns"][s0 + 1:]))
    assert sharpes[0] >= sharpes[1] >= sharpes[2]


def test_golden_ledger_one_cycle():
    """Hand-computed two-asset ledger pins the engine to the timing
    contract numerically: entry cost lands the day AFTER execution (Q3),
    drift follows shares-fixed weights (Section 5), turnover is the
    half-sum against drifted weights (Q2), bps convert as /1e4."""
    from src.backtest import month_end_indices, run_with_scores

    dates = list(pd.bdate_range("2020-01-02", periods=60))
    T = len(dates)
    prices = np.full((T, 2), 100.0)
    mes = month_end_indices(dates)
    m1, m2 = mes[0], mes[1]
    e1, e2 = m1 + 1, m2 + 1
    d = e1 + 3                              # doubling day inside the month
    assert d < m2
    prices[d:, 0] = 200.0                   # asset 0 doubles at close d

    res = run_with_scores(prices, dates, np.ones((T, 2)), 2, 100.0)  # 100 bps
    ret, tv = res["net_returns"], res["turnovers"]

    assert len(tv) == 2
    assert tv[0] == pytest.approx(0.5, abs=1e-15)          # cash -> [.5,.5]
    assert ret[e1] == pytest.approx(0.0, abs=1e-15)        # old (cash) weights
    assert ret[e1 + 1] == pytest.approx(-0.005, abs=1e-15)  # 0.5 x 1% cost
    assert ret[d] == pytest.approx(0.5, abs=1e-15)         # .5*2 + .5*1 - 1
    assert tv[1] == pytest.approx(1.0 / 6.0, abs=1e-15)    # [2/3,1/3] -> [.5,.5]
    assert ret[e2 + 1] == pytest.approx(-0.01 / 6.0, abs=1e-15)
    expected_nav = (1 - 0.005) * 1.5 * (1 - 0.01 / 6.0)
    assert res["nav"][-1] == pytest.approx(expected_nav, rel=1e-12)


def test_net_returns_affine_in_cost_rate():
    """PROTOCOL Section 11 solves the break-even cost exactly via
    linearity. This test pins that linearity: the weight/turnover path is
    cost-independent, and net returns are affine in the cost rate."""
    from src.backtest import run_backtest
    from src.data import SECTORS

    dates, prices, tickers, _ = load_prices()
    sect = prices[:, [tickers.index(s) for s in SECTORS]]

    r0 = run_backtest(sect, dates, 252, 21, 3, 0.0)
    r10 = run_backtest(sect, dates, 252, 21, 3, 10.0)
    r50 = run_backtest(sect, dates, 252, 21, 3, 50.0)

    assert r0["turnovers"] == r10["turnovers"] == r50["turnovers"]
    pred = r0["net_returns"] + 0.2 * (r50["net_returns"] - r0["net_returns"])
    assert np.max(np.abs(r10["net_returns"] - pred)) < 1e-12


def test_composite_window_starts_after_last_cell():
    """The composite statistics window must begin one day after the LAST
    cell becomes valid, so no cell contributes cash-zeros to the stats."""
    from run_all import composite_and_window

    cells = [
        {"start_index": 5, "net_returns": np.arange(10.0)},
        {"start_index": 8, "net_returns": np.ones(10)},
    ]
    comp, window = composite_and_window(cells)
    assert window.start == 9
    assert np.allclose(comp, (np.arange(10.0) + np.ones(10)) / 2.0)


def test_select_top_k_tie_break_fixed_order():
    """Section 4: ties broken by fixed ticker order - deterministically."""
    from src.backtest import select_top_k

    assert list(select_top_k(np.array([1.0, 1.0, 1.0, 0.0]), 2)) == [0, 1]
    assert list(select_top_k(np.array([0.0, 2.0, 2.0, 1.0]), 2)) == [1, 2]


def test_ols_newey_west_match_statsmodels():
    """Hand-written OLS alpha/beta agree with statsmodels to 1e-10, and the
    Newey-West alpha t-stat to 1e-6 (oracle run with use_correction=False
    to match our no-small-sample-correction convention)."""
    import statsmodels.api as sm
    from src.stats import ols, newey_west_tstat

    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 0.01, 1500)
    y = 0.0002 + 0.9 * x + rng.normal(0.0, 0.005, 1500)

    mine = ols(y, x)
    oracle = sm.OLS(y, sm.add_constant(x)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 21, "use_correction": False}
    )
    assert abs(mine["alpha"] - oracle.params[0]) < 1e-10
    assert abs(mine["beta"] - oracle.params[1]) < 1e-10
    assert abs(newey_west_tstat(mine, lag=21) - oracle.tvalues[0]) < 1e-6
