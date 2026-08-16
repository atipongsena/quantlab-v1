"""Tests for MLDatasetBuilder alignment."""

import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue
from quantlab.ml.dataset import MLDatasetBuilder


def test_dataset_builder_aligns_features_and_labels() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    s1 = date(2026, 1, 2)
    s2 = date(2026, 1, 5)

    snap1_s1 = FactorSnapshot.create(
        "f1", "v1", s1, datetime.now(tz=UTC), {inst1: FactorValue(inst1, 1.5)}
    )
    snap1_s2 = FactorSnapshot.create(
        "f1", "v1", s2, datetime.now(tz=UTC), {inst1: FactorValue(inst1, 2.5)}
    )

    factor_map = {
        "f1": {s1: snap1_s1, s2: snap1_s2},
    }
    labels_map = {
        s1: {inst1: 0.05},
        s2: {inst1: -0.02},
    }

    dataset = MLDatasetBuilder.build("ML-DATA-01", factor_map, labels_map, [s1, s2])
    assert len(dataset.rows) == 2
    assert dataset.feature_names == ("f1",)
    assert dataset.rows[0].features == (1.5,)
    assert dataset.rows[0].label == 0.05
