from __future__ import annotations

from collections.abc import Collection

from quantlab.domain.identity import Instrument, InstrumentType


class InstrumentTypeFilter:
    def __init__(
        self,
        allowed_types: Collection[InstrumentType] = (InstrumentType.EQUITY,),
    ) -> None:
        self._allowed_types = set(allowed_types)

    def allow_type(self, instrument_type: InstrumentType) -> bool:
        return instrument_type in self._allowed_types

    def allow(self, instrument: Instrument) -> bool:
        return self.allow_type(instrument.instrument_type)
