"""ML Dataset builder aligning point-in-time features with forward targets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot
from quantlab.ml.contracts import MLDataset, MLFeatureRow


class MLDatasetBuilder:
    """Constructs aligned tabular ML datasets from factor snapshots and label dictionaries."""

    @classmethod
    def build(
        cls,
        dataset_id: str,
        factor_snapshots_by_name: Mapping[str, Mapping[date, FactorSnapshot]],
        labels_by_session: Mapping[date, Mapping[InstrumentId, float]],
        sessions: Sequence[date],
    ) -> MLDataset:
        feature_names = tuple(sorted(factor_snapshots_by_name.keys()))
        rows: list[MLFeatureRow] = []

        for s in sorted(sessions):
            session_labels = labels_by_session.get(s, {})
            valid_snaps: list[FactorSnapshot] = []
            for fn in feature_names:
                sn = factor_snapshots_by_name[fn].get(s)
                if sn is not None:
                    valid_snaps.append(sn)

            if len(valid_snaps) != len(feature_names):
                continue

            # Instruments present in all snapshots
            common_insts: set[InstrumentId] = set(valid_snaps[0].values.keys())
            for sn in valid_snaps[1:]:
                common_insts &= set(sn.values.keys())

            sorted_insts = sorted(common_insts, key=lambda x: str(x.value))
            for inst in sorted_insts:
                feat_vals = tuple(
                    float(valid_snaps[i].values[inst].value or 0.0)
                    for i in range(len(feature_names))
                )
                target_val = session_labels.get(inst)
                rows.append(
                    MLFeatureRow(
                        session=s,
                        instrument_id=inst,
                        features=feat_vals,
                        label=target_val,
                    )
                )

        return MLDataset(
            dataset_id=dataset_id,
            feature_names=feature_names,
            rows=tuple(rows),
        )
