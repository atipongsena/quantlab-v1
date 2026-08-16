"""Tests for transaction costs and adverse slippage."""

from decimal import Decimal

from quantlab.backtest.costs import FeeModel, SlippageModel
from quantlab.domain.orders import OrderSide


def test_slippage_model_adverse_pricing() -> None:
    model = SlippageModel(slippage_bps=Decimal("10.0"))  # 10 bps = 0.1%

    ref = Decimal("50.00")
    buy_price, buy_slip = model.execute_price(ref, OrderSide.BUY)
    assert buy_price == Decimal("50.0500")
    assert buy_slip == Decimal("0.0500")

    sell_price, sell_slip = model.execute_price(ref, OrderSide.SELL)
    assert sell_price == Decimal("49.9500")
    assert sell_slip == Decimal("0.0500")


def test_fee_model_commission_calculation() -> None:
    fee_model = FeeModel(commission_per_share=Decimal("0.005"), min_commission=Decimal("1.00"))

    # 100 shares -> $0.50 -> min $1.00 applied
    f1 = fee_model.calculate_fees(Decimal("100.0"), Decimal("50.0"))
    assert f1 == Decimal("1.00")

    # 1000 shares -> $5.00
    f2 = fee_model.calculate_fees(Decimal("1000.0"), Decimal("50.0"))
    assert f2 == Decimal("5.00")
