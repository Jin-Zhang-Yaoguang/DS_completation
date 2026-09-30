from pathlib import Path

from policy_portfolio import FactorizedPortfolioPolicy


def test_portfolio_rejects_missing_specialists_before_loading_checkpoints():
    try:
        FactorizedPortfolioPolicy(Path("router"), {0: Path("wheat")})
    except ValueError as error:
        assert "missing crop specialists" in str(error)
    else:
        raise AssertionError("missing specialists must be rejected")
