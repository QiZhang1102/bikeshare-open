# Exercise 3 - Peer Audit

## Review Identification

- Reviewer: Haoshuo Bi (HaoshuoBi)
- Reviewee: Shujia Chen (IrisC113)
- Repository: https://github.com/QiZhang1102/bikeshare-open
- Reviewed branch: exercise-4&5
- Reviewed commit: 2f90dfb
- Comparison baseline: 687b32d
- Review date: November 25, 2026
- Scope: Exercise 4 target transformation and
  Exercise 5 ridge vs persistence analysis.
- Assessment status: Approved on Pull Request #2.

### AI Audit Results

The leakage-auditor reported no violations in the five methodological checks:

| Check | Agent finding |
| --- | --- |
| Target leakage | No violation found |
| Temporal ordering | No violation found |
| Calendar gaps | No violation found |
| Silent row loss | No violation found |
| Unreported baselines | No violation found |

The agent also inspected target transformation, inverse transformation,
experiment fingerprints, and validation-based model selection.

The agent noted that dropna() has no direct row-loss assertion,
but the existing contract test bounds the expected row loss.

### Human Judgment

I reviewed the transformation tests and REPORT.md.
I agree with the Exercise 5 conclusion under the stated
absolute-error cost assumption. Persistence has a lower test
MAE than Ridge (840.1 versus 946.2 rides/day).

### Independent Verification

Command:

    python -m pytest tests/test_target_transform.py -q -k "known_counts or invalid_count_domains or negative_reference"

Actual output:

    8 passed, 5 deselected in 17.26s

### Limitations

The subagent's Bash execution was restricted by the permission
system. Its findings were based on static inspection.
I independently executed eight targeted tests.
I did not rerun the full training pipeline or held-out evaluation.
No changes were made to the reviewed source code.

### Final Decision

No blocking methodological issues were found within the reviewed scope.
I submitted an Approve review on Pull Request #2.

## Original leakage-auditor Output (Verbatim)

Based on my review of all the source code files, I have completed the methodology audit. Let me provide my findings:

## Methodology Audit Report for commits 687b32d to 2f90dfb

### Check 1: Target Leakage

**Finding:** No violations found.

- Line 31 in `src/config.py`: `LEAKAGE_COLS = {"casual", "registered", "cnt"}` - correctly excludes all target components
- Line 46 in `src/config.py`: `FORBIDDEN = LEAKAGE_COLS | TIME_INDEX_COLS | UNVERIFIED_COLS` - combines all exclusions
- Line 85 in `src/features.py`: `return [c for c in numeric if c not in FORBIDDEN]` - filters out forbidden columns

The arithmetic identity `casual + registered == cnt` is verified in `tests/test_leakage.py` line 22. The feature construction uses `.shift(1)` before aggregation (lines 74-77), ensuring lagged targets don't contain today's count.

### Check 2: Temporal Ordering

**Finding:** Code correctly implements temporal ordering.

- Line 53-79 in `src/features.py`: All lags use `.shift(1)` or `.shift(LAG_WARMUP)` before aggregation
- Line 76-77: Rolling features correctly use `out[TARGET].shift(1).rolling(...).mean()` - the shift comes first
- Line 108-110 in `src/train.py`: Split is by date (`dteday <= TRAIN_END`, etc.) not random
- Line 127 in `src/train.py`: `model.fit(train[cols], train[TARGET])` fits only on training data

**Verification:** Models are fitted on train, then predicted on valid/test separately (lines 127-134). The temporal split uses date boundaries, not random indices.

### Check 3: Calendar Gaps

**Finding:** Code correctly handles calendar gaps.

- Lines 34-50 in `src/features.py`: `reindex_to_calendar()` explicitly fills missing days (including 2011-03-10)
- Line 54 in `src/features.py`: Features are built after reindexing to fill gaps
- The docstring at lines 37-42 explains that without this step, lags would be misaligned

**Verification:** After reindexing, the gap becomes an explicit NaN (line 79 via `dropna()`), and all lags work correctly on contiguous calendar indices.

### Check 4: Silent Row Loss

**Finding:** Minor code smell identified but not a violation.

- Line 79 in `src/features.py`: `return out.dropna().reset_index(drop=True)` uses `dropna()` without an assertion
- Lines 22-31 in `src/features.py`: The `encode_weather()` function uses `.map(WEATHER_ORDER)` which could silently produce NaNs, though it raises on unseen labels (line 29-30)

**Analysis:** The row loss is bounded by design - only the LAG_WARMUP warm-up rows plus rows following missing calendar days are lost. This is accounted for in `tests/test_contract.py` line 41-43 (`test_only_expected_rows_are_dropped`). The test asserts `lost <= allowed_loss`.

### Check 5: Unreported Baselines

**Finding:** Both baselines are reported.

- Lines 97-102 in `src/train.py`: `MODELS` dictionary includes:
  - `"baseline_mean": DummyRegressor(strategy="mean")` 
  - `"baseline_persistence": PersistenceBaseline("cnt_lag_1")`
- Line 126-134 in `src/train.py`: Both baselines are scored on valid and test sets

The persistence baseline is the critical one for lag-driven models and it's included.

---

### Extra Verifications

#### Experiment Fingerprints

**Finding:** Correctly implemented.

- Lines 138-141 in `src/train.py`: `experiment_fingerprints()` hashes:
  - `src/train.py`
  - `src/features.py`
  - `src/config.py`
  - `data/processed/features.parquet`

This correctly freezes the exact code/data state before held-out evaluation.

#### Transformed Target Isolation

**Finding:** Correctly implemented.

- Line 148 in `src/train.py`: Docstring confirms "The transformed label is a separate array, never a candidate predictor"
- Lines 201-206: `transformed_y = transform_target(...)` creates a separate array; models are fitted on this transformed target but predict into original scale via `inverse_target()`

#### Validation Selection Before Test

**Finding:** Correctly enforced.

- Line 154 in `src/train.py`: `filters` only includes valid split by default
- Lines 236-249: The `--include-test` flag requires a frozen `--selection` file with matching fingerprints
- Line 244-245: Rejects if fingerprints changed since validation decision

---

### Summary

All five checks pass:

1. **Target leakage:** No violations - forbidden columns are excluded; lags use proper shifts
2. **Temporal ordering:** Correct - date-based split, shift before aggregate, no data leakage across fits
3. **Calendar gaps:** Handled - `reindex_to_calendar()` fills missing days explicitly
4. **Silent row loss:** Accounted for - only warm-up and missing-day rows drop, bounded by test in `test_contract.py`
5. **Unreported baselines:** Both mean and persistence baselines are reported

**One code smell (not a violation):** Line 79 in `src/features.py` uses `.dropna()` without an assertion on how many rows were removed. However, this is acceptable because:
- The number of dropped rows is determined solely by the `LAG_WARMUP` constant and missing calendar days
- The test at `test_contract.py:41-43` asserts that actual loss doesn't exceed expected loss

**Final Conclusion:** All five methodological checks pass. The target transformation, inverse transformation, validation-based model selection, and reported conclusions are correctly implemented according to the audit criteria.
