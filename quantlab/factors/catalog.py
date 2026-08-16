"""Catalog registering all standard V1 factors."""

from __future__ import annotations

from quantlab.factors.contracts import Factor
from quantlab.factors.growth import OperatingIncomeGrowth, RevenueGrowth
from quantlab.factors.momentum import Momentum6M1M, Momentum12M1M
from quantlab.factors.quality import ROA, ROE, AccrualQuality, GrossProfitability
from quantlab.factors.registry import FactorRegistry
from quantlab.factors.risk import Beta, MaxDrawdown252D, Volatility60D
from quantlab.factors.value import BookToMarket, EarningsYield, FCFYield


def create_v1_factor_instances() -> tuple[Factor, ...]:
    """Create new instances of all 14 standard V1 factors."""
    return (
        Momentum12M1M(),
        Momentum6M1M(),
        EarningsYield(),
        BookToMarket(),
        FCFYield(),
        ROE(),
        ROA(),
        GrossProfitability(),
        AccrualQuality(),
        RevenueGrowth(),
        OperatingIncomeGrowth(),
        Volatility60D(),
        MaxDrawdown252D(),
        Beta(),
    )


def register_standard_factors(registry: FactorRegistry | None = None) -> FactorRegistry:
    """Register all 14 standard V1 factors into the provided (or global) registry."""
    target = registry or FactorRegistry.global_instance()
    for factor in create_v1_factor_instances():
        target.register(factor)
    return target
