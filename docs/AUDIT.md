# Exercise 3 — Haoshuo's peer audit of Shujia's Exercises 4 and 5

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

I agree with the auditor's main findings within the
reviewed scope. I found no verified issue that changes
the reported experimental results. The potential row-loss
concern is addressed by the existing contract test.
However, the audit was limited to static inspection and
targeted testing, not full experimental reproduction.

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

---

# Exercise 3 — Mia’s peer audit of Nate’s Exercise 2

**Reviewer:** Qi (Mia) Zhang (`QiZhang1102`)  
**Reviewee:** Haoshuo (Nate) Bi (`HaoshuoBi`)  
**Repository:** <https://github.com/QiZhang1102/bikeshare-open>  
**Pull request:** [#1 — Nate’s Exercise 2](https://github.com/QiZhang1102/bikeshare-open/pull/1)  
**Branch and version reviewed:** `haoshuobi-exercise2` at [`c5ab5bb`](https://github.com/QiZhang1102/bikeshare-open/commit/c5ab5bba098f17333ca6a447c1a658f2c94e18b0), compared with `5a395a1`  
**Review date:** November 25, 2026

## Original leakage-auditor output (verbatim)

The course’s `leakage-auditor` ran in Claude Code with `qwen2.5-coder:3b` through Ollama. It received excerpts from the code and fault log, the list of files changed in the PR, and the test output.

```text
The peer review of Exercise 2, PR #1, shows that all five checks passed. The changes made in the code do not produce a wrong result for any of the checks. No changes were made that would introduce any of the historical faults identified in the `SEEDED_FAULTS.md` document. The code meets all the requirements set by the project instructions, and there are no style preferences noted.
```

## Checks against the code

| Check | What the code and tests show |
|---|---|
| Target leakage | The model inputs exclude `cnt`, `casual`, and `registered`. The test for January 12 checks the three-day average against the raw counts from January 9, 10, and 11. |
| Time order | Both rolling averages shift the count back one day before averaging. The split follows calendar dates, and the models fit only on training rows. |
| Calendar gaps | The pipeline adds March 10, 2011 to the calendar before building lags. That keeps the March 9 count from being treated as yesterday’s count on March 11. |
| Dropped rows | Of 728 observed days, 714 remain. The first seven days lack a full history, and the next seven days after the March 10 gap also have incomplete history. That accounts for all 14 dropped observations. |
| Baselines | The training code scores the training-mean and previous-day baselines on the same validation and test dates as Ridge and HGB. |

## Independent verification

Claude Code received the full pytest output from a separate test run on a clean checkout of `c5ab5bb`.

```bash
python -m pytest tests/ -q
```

```text
.................                                                        [100%]
17 passed in 1.37s
```

One test matters especially for Nate’s third fault. Removing the weather-label check used to let an unknown label turn into a missing value and a row get dropped. The new test passes `UNKNOWN` to the encoder and checks that it raises `ValueError`.

## Human judgment

I agree with the auditor on the five forecasting checks. I don’t see a reason to change a reported R² or MAE based on Nate’s Exercise 2 changes. The 14 missing observations are accounted for, and the new weather test catches a case the old tests missed. I do have one follow-up for Nate. His fourth fault record shows that Bash blocked `touch` in `data/raw/`. The assignment asks what happens when Bash copies a file there with `cp`. I’d ask him to record that result before calling the fault experiment complete. The missing result matters for the write-protection claim, but it gives me no evidence that a model score changed. [Nate’s fault record](https://github.com/QiZhang1102/bikeshare-open/blob/c5ab5bba098f17333ca6a447c1a658f2c94e18b0/docs/SEEDED_FAULTS.md#L363) · [Assignment instructions](https://github.com/DSC-Capstone/2026-27/blob/main/assignments/methodology/07-open.md#L663)

## Limits of this review

The tests cover the code at the reviewed commit. For the four earlier fault experiments, this review uses Nate’s saved output. It did not recreate the faults or rerun training to reproduce the model scores.

### Follow-up

HaoshuoBi completed the Bash `cp` permission test and documented the actual denial and unchanged raw-data hash in [SEEDED_FAULTS.md](https://github.com/QiZhang1102/bikeshare-open/blob/haoshuobi-exercise2/docs/SEEDED_FAULTS.md#L378). The issue identified during my peer review has been addressed.
