"""Forward return labels and cross-sectional target calculation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from quantlab.domain.identity import InstrumentId
from quantlab.ml.contracts import LabelSpec, LabelType


class LabelCalculator:
    """Computes lookahead-free forward return labels for cross-sectional ranking."""

    @classmethod
    def compute_forward_returns(
        cls,
        prices_by_date: Mapping[date, Mapping[InstrumentId, float]],
        sessions: Sequence[date],
        spec: LabelSpec,
    ) -> dict[date, dict[InstrumentId, float]]:
        """Computes H-session forward returns for each session t using t+1 open to t+1+H open."""
        sorted_sessions = sorted(sessions)
        h = spec.horizon_sessions
        labels_by_session: dict[date, dict[InstrumentId, float]] = {}

        for i in range(len(sorted_sessions) - h - 1):
            t = sorted_sessions[i]
            t_entry = sorted_sessions[i + 1]
            t_exit = sorted_sessions[i + 1 + h]

            p_entry_map = prices_by_date.get(t_entry, {})
            p_exit_map = prices_by_date.get(t_exit, {})

            common_insts = sorted(
                set(p_entry_map.keys()) & set(p_exit_map.keys()),
                key=lambda x: str(x.value),
            )
            if not common_insts:
                continue

            raw_rets: dict[InstrumentId, float] = {}
            for inst in common_insts:
                p_in = p_entry_map[inst]
                p_out = p_exit_map[inst]
                if p_in > 1e-4:
                    raw_rets[inst] = (p_out / p_in) - 1.0

            if not raw_rets:
                continue

            if spec.label_type == LabelType.FORWARD_RETURN:
                labels_by_session[t] = raw_rets
            elif spec.label_type == LabelType.CROSS_SECTIONAL_EXCESS:
                mean_ret = sum(raw_rets.values()) / len(raw_rets)
                labels_by_session[t] = {inst: r - mean_ret for inst, r in raw_rets.items()}
            elif spec.label_type == LabelType.CROSS_SECTIONAL_RANK:
                # Rank standardized to [-1, 1]
                n = len(raw_rets)
                sorted_by_ret = sorted(raw_rets.items(), key=lambda x: (x[1], str(x[0].value)))
                labels_by_session[t] = {
                    inst: 2.0 * (rank / (n - 1)) - 1.0 if n > 1 else 0.0
                    for rank, (inst, _) in enumerate(sorted_by_ret)
                }

        return labels_by_session
