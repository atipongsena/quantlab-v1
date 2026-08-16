from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from quantlab.common.errors import QuantLabError
from quantlab.domain.identity import InstrumentId, SymbolHistory


class InstrumentIdentityError(QuantLabError):
    """Raised when instrument or symbol history validation fails."""


def validate_non_overlapping_history(histories: Sequence[SymbolHistory]) -> None:
    """Validate that no two histories for the same (symbol, exchange) have overlapping intervals."""
    by_symbol_exchange: dict[tuple[str, str], list[SymbolHistory]] = {}
    for h in histories:
        key = (h.symbol.upper(), h.exchange.upper())
        by_symbol_exchange.setdefault(key, []).append(h)

    for (symbol, exchange), symbol_histories in by_symbol_exchange.items():
        sorted_histories = sorted(symbol_histories, key=lambda x: x.valid_from)
        for i in range(len(sorted_histories) - 1):
            current_h = sorted_histories[i]
            next_h = sorted_histories[i + 1]

            if current_h.valid_to is None:
                raise InstrumentIdentityError(
                    f"Overlapping open-ended symbol history for {symbol} on {exchange}: "
                    f"from {current_h.valid_from} overlaps with next starting {next_h.valid_from}"
                )
            if current_h.valid_to >= next_h.valid_from:
                raise InstrumentIdentityError(
                    f"Overlapping symbol history for {symbol} on {exchange}: "
                    f"[{current_h.valid_from}, {current_h.valid_to}] overlaps with "
                    f"[{next_h.valid_from}, {next_h.valid_to}]"
                )


def resolve_symbol_in_memory(
    histories: Sequence[SymbolHistory],
    symbol: str,
    exchange: str,
    as_of: date,
) -> InstrumentId | None:
    """Resolve an instrument_id for (symbol, exchange, as_of) from a list of symbol histories."""
    symbol_norm = symbol.upper()
    exchange_norm = exchange.upper()

    matches: list[SymbolHistory] = []
    for h in histories:
        if h.symbol.upper() == symbol_norm and h.exchange.upper() == exchange_norm:
            if h.valid_from <= as_of and (h.valid_to is None or as_of <= h.valid_to):
                matches.append(h)

    if not matches:
        return None
    if len(matches) > 1:
        raise InstrumentIdentityError(
            f"Ambiguous resolution: multiple instruments for {symbol} on {exchange} as of {as_of}"
        )
    return matches[0].instrument_id
