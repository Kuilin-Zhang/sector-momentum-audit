# tests/test_contract.py
#
# Research-invariant tests, PROTOCOL.md + frozen spec Section 6.
# These test the RESEARCH, not toy functions. Every test name states the
# invariant it defends. All start skipped; each block un-skips its own.

import pytest


@pytest.mark.skip(reason="Block 1: data layer")
def test_data_contract_shape_and_no_nans():
    """load_prices returns (T,10), no NaNs after the fill policy,
    dates strictly increasing."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 1: signal sanity")
def test_monotone_asset_gets_top_rank():
    """On a synthetic panel where one asset rises every day and the rest
    fall, that asset must hold the top momentum rank once signals are
    valid."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 2: THE leakage positive control")
def test_leakage_positive_control():
    """A deliberately cheating signal built from FUTURE returns must
    produce Sharpe > 3; the honest pipeline on the same data must stay
    below 2. If this test can't tell them apart, the harness is blind."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 2: benchmark identity")
def test_zero_cost_full_hold_equals_ew9():
    """With cost = 0 and top_k = 9, the strategy IS the EW9 benchmark:
    NAV paths must agree to 1e-10 pointwise."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 2: turnover bounds")
def test_single_rebalance_turnover_in_bounds():
    """Half-sum turnover of one rebalance lies in [0, 1]; weights row sums
    are 1 (invested) or 0 (cash)."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 3: cost monotonicity")
def test_net_sharpe_monotone_in_costs():
    """Net Sharpe must be non-increasing as the cost rate rises."""
    raise NotImplementedError


@pytest.mark.skip(reason="Block 3: stats oracle")
def test_ols_newey_west_match_statsmodels():
    """Hand-written OLS alpha/beta and NW t agree with statsmodels to
    1e-8 on random data."""
    raise NotImplementedError
