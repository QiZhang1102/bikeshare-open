"""Exercise 4: correct inverse scale and an explicit held-out boundary."""
import math
import sys

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from src import train
from src.config import METRICS, VALID_END


@pytest.mark.parametrize("kind,expected", [
    ("residual", [0.0, 2.0, 8.0, -2.0]),
    ("log_ratio", [0.0, math.log(2.0), math.log(2.0), math.log(2.0 / 3.0)]),
])
def test_target_transform_and_inverse_on_known_counts(kind, expected):
    counts = np.array([0.0, 3.0, 15.0, 3.0])
    history = np.array([0.0, 1.0, 7.0, 5.0])
    transformed = train.transform_target(counts, history, kind)
    assert transformed == pytest.approx(expected)
    assert train.inverse_target(transformed, history, kind) == pytest.approx(counts)


@pytest.mark.parametrize("kind", ["residual", "log_ratio"])
@pytest.mark.parametrize("counts,history", [([-1.0], [1.0]), ([1.0], [-1.0])])
def test_invalid_count_domains_raise(kind, counts, history):
    with pytest.raises(ValueError, match="nonnegative"):
        train.transform_target(counts, history, kind)


@pytest.mark.parametrize("kind", ["residual", "log_ratio"])
def test_inverse_rejects_negative_reference(kind):
    with pytest.raises(ValueError, match="nonnegative"):
        train.inverse_target([0.0], [-1.0], kind)


@pytest.mark.parametrize("kind", ["residual", "log_ratio"])
def test_validation_filters_test_and_scores_inverse_count_scale(monkeypatch, kind):
    real_read = pd.read_parquet

    def guarded_read(path, **kwargs):
        frame = real_read(path, **kwargs)
        assert frame.dteday.max() <= pd.Timestamp(VALID_END), "held-out rows were loaded"
        return frame

    monkeypatch.setattr(train.pd, "read_parquet", guarded_read)
    monkeypatch.setattr(train, "MODELS", {
        "baseline_mean": DummyRegressor(strategy="mean"),
        "baseline_persistence": train.PersistenceBaseline(),
        "ridge": DummyRegressor(strategy="constant", constant=0.0),
        "hgb": DummyRegressor(strategy="constant", constant=0.0),
    })
    result = train.score_target_experiment(kind)
    # A zero transformed prediction must invert to the known history level.
    assert result["hgb_transformed"]["valid"] == result["baseline_roll_7"]["valid"]
    assert result["ridge_transformed"]["valid"] == result["baseline_roll_7"]["valid"]
    assert "test" not in result["hgb_transformed"]
    assert "n_test" not in result


def test_experiment_cannot_overwrite_canonical_metrics(monkeypatch):
    before = METRICS.read_bytes()
    monkeypatch.setattr(sys, "argv", ["src.train", "--target-transform", "residual", "--out", str(METRICS)])
    with pytest.raises(SystemExit) as error:
        train.main()
    assert error.value.code == 2
    assert METRICS.read_bytes() == before


def test_ridge_control_uses_its_own_inverse(monkeypatch):
    monkeypatch.setattr(train, "MODELS", {
        "baseline_mean": DummyRegressor(strategy="mean"),
        "baseline_persistence": train.PersistenceBaseline(),
        "ridge": DummyRegressor(strategy="constant", constant=1.0),
        "hgb": DummyRegressor(strategy="constant", constant=1.0),
    })
    result = train.score_target_experiment("log_ratio", ridge_control="residual")
    frame = pd.read_parquet(train.PROCESSED, filters=[("dteday", "<=", pd.Timestamp(VALID_END))])
    _, valid, _ = train.temporal_split(frame)
    prediction = valid[train.TARGET_REFERENCE] + 1.0
    expected = {"r2": round(float(r2_score(valid[train.TARGET], prediction)), 4),
                "mae": round(float(mean_absolute_error(valid[train.TARGET], prediction)), 1)}
    assert result["ridge_control"]["valid"] == expected
    assert result["ridge_transformed"]["valid"] != expected
    assert "test" not in result["ridge_control"]


def test_test_evaluation_requires_a_frozen_selection(monkeypatch, tmp_path):
    destination = tmp_path / "test.json"
    monkeypatch.setattr(sys, "argv", ["src.train", "--target-transform", "residual", "--include-test", "--out", str(destination)])
    with pytest.raises(SystemExit) as error:
        train.main()
    assert error.value.code == 2
    assert not destination.exists()
