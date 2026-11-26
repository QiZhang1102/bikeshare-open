"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    METRICS, PROCESSED, ROOT, TARGET, TARGET_REFERENCE, TARGET_TRANSFORMS,
    TRAIN_END, VALID_END,
)
from src.features import feature_columns


def transform_target(values, reference, kind):
    values = np.asarray(values, dtype=float)
    reference = np.asarray(reference, dtype=float)

    if values.ndim != 1 or reference.ndim != 1 or values.shape != reference.shape or values.size == 0:
        raise ValueError("values and reference must have the same shape")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(reference)):
        raise ValueError("values and reference must contain only finite values")
    if np.any(values < 0) or np.any(reference < 0):
        raise ValueError("counts and reference must be nonnegative")

    if kind == "residual":
        return values - reference

    elif kind == "log_ratio":
        return np.log1p(values) - np.log1p(reference)

    else:
        raise ValueError(f"Unknown kind: {kind}")


def inverse_target(prediction, reference, kind):
    prediction = np.asarray(prediction, dtype=float)
    reference = np.asarray(reference, dtype=float)

    if prediction.ndim != 1 or reference.ndim != 1 or prediction.shape != reference.shape or prediction.size == 0:
        raise ValueError("prediction and reference must have the same shape")
    if not np.all(np.isfinite(prediction)) or not np.all(np.isfinite(reference)):
        raise ValueError("prediction and reference must contain only finite values")
    if np.any(reference < 0):
        raise ValueError("reference must be nonnegative")

    if kind == "residual":
        return reference + prediction

    elif kind == "log_ratio":
        return np.expm1(np.log1p(reference) + prediction)

    else:
        raise ValueError(f"Unknown kind: {kind}")


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


def experiment_fingerprints() -> dict[str, str]:
    """Freeze the model/feature code and data before a held-out evaluation."""
    paths = [ROOT / "src/train.py", ROOT / "src/features.py", ROOT / "src/config.py", PROCESSED]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def score_target_experiment(kind: str, include_test: bool = False, ridge_control: str | None = None) -> dict:
    """Compare fixed estimators on the original count scale.

    Validation runs exclude H2 2012 at the Parquet reader. The transformed
    label is a separate array, never a candidate predictor in the frame.
    """
    if kind not in TARGET_TRANSFORMS:
        raise ValueError(f"unknown target transform: {kind}")
    if ridge_control is not None and ridge_control not in TARGET_TRANSFORMS:
        raise ValueError(f"unknown ridge control transform: {ridge_control}")
    filters = None if include_test else [("dteday", "<=", pd.Timestamp(VALID_END))]
    df = pd.read_parquet(PROCESSED, filters=filters)
    cols = feature_columns(df)
    if TARGET_REFERENCE not in cols:
        raise ValueError(f"missing known-history reference: {TARGET_REFERENCE}")
    train, valid, test = temporal_split(df)
    parts = [("valid", valid)] + ([("test", test)] if include_test else [])
    result = {
        "target_transform": kind, "reference": TARGET_REFERENCE,
        "ridge_control_transform": ridge_control,
        "evaluation_scope": "locked_validation_and_test" if include_test else "validation_only",
        "features": cols, "n_features": len(cols),
        "n_train": len(train), "n_valid": len(valid),
        "fingerprints": experiment_fingerprints(),
        "diagnostics": {
            "train_target_min": float(train[TARGET].min()),
            "train_target_max": float(train[TARGET].max()),
            "target_mean_train": float(train[TARGET].mean()),
            "target_mean_valid": float(valid[TARGET].mean()),
            "valid_targets_above_train_max": int((valid[TARGET] > train[TARGET].max()).sum()),
        },
    }
    if include_test:
        result["n_test"] = len(test)

    def record(name, fitted, inverse_kind=None):
        result[name] = {}
        result["diagnostics"][name] = {}
        for split, part in parts:
            prediction = fitted.predict(part[cols])
            if inverse_kind is not None:
                prediction = inverse_target(prediction, part[TARGET_REFERENCE], inverse_kind)
            result[name][split] = {
                "r2": round(float(r2_score(part[TARGET], prediction)), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], prediction)), 1),
            }
            result["diagnostics"][name][split] = {
                "prediction_min": float(np.min(prediction)),
                "prediction_max": float(np.max(prediction)),
                "predictions_above_train_target_max": int((prediction > train[TARGET].max()).sum()),
                "negative_predictions": int((prediction < 0).sum()),
            }

    comparisons = {**MODELS, "baseline_roll_7": PersistenceBaseline(TARGET_REFERENCE)}
    for name, template in comparisons.items():
        fitted = clone(template).fit(train[cols], train[TARGET])
        record(name, fitted)
    transformed_y = transform_target(train[TARGET], train[TARGET_REFERENCE], kind)
    result["diagnostics"]["transformed_training_target_min"] = float(np.min(transformed_y))
    result["diagnostics"]["transformed_training_target_max"] = float(np.max(transformed_y))
    for name in ("ridge", "hgb"):
        fitted = clone(MODELS[name]).fit(train[cols], transformed_y)
        record(name + "_transformed", fitted, inverse_kind=kind)
    if ridge_control is not None and ridge_control != kind:
        control_y = transform_target(train[TARGET], train[TARGET_REFERENCE], ridge_control)
        fitted = clone(MODELS["ridge"]).fit(train[cols], control_y)
        record("ridge_control", fitted, inverse_kind=ridge_control)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-transform", choices=TARGET_TRANSFORMS)
    parser.add_argument("--ridge-control", choices=TARGET_TRANSFORMS)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--validation-only", action="store_true")
    scope.add_argument("--include-test", action="store_true")
    parser.add_argument("--selection", type=Path, help="Frozen validation decision, required before test")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.target_transform is None:
        if args.validation_only or args.include_test or args.selection or args.ridge_control:
            parser.error("experiment scope/selection flags require --target-transform")
        res = fit_and_score()
        destination = args.out or METRICS
    else:
        if args.out is None:
            parser.error("target experiments require a separate --out path")
        destination = args.out
        if destination.resolve() == METRICS.resolve():
            parser.error("target experiments cannot overwrite canonical reports/metrics.json")
        if args.include_test:
            if args.selection is None:
                parser.error("--include-test requires a frozen --selection file")
            lock = json.loads(args.selection.read_text(encoding="utf-8"))
            if lock.get("selected_transform") != args.target_transform:
                parser.error("transform differs from the frozen validation decision")
            if lock.get("ridge_control") != args.ridge_control:
                parser.error("ridge control differs from the frozen validation decision")
            if lock.get("fingerprints") != experiment_fingerprints():
                parser.error("code/data changed since validation; do not inspect test")
            if Path(lock["test_output"]).resolve() != destination.resolve():
                parser.error("test output differs from the frozen destination")
            if destination.exists():
                parser.error("the frozen test evaluation already exists; refusing to rerun")
        res = score_target_experiment(args.target_transform, include_test=args.include_test,
                                      ridge_control=args.ridge_control)

    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if args.target_transform and args.include_test else "w"
    with destination.open(mode, encoding="utf-8") as output:
        output.write(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))


if __name__ == "__main__":
    main()
