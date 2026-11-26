# Exercise 3: Peer Review of QI Zhang's Exercise 1

## Review identification

- Reviewer: **Shujia Chen**, GitHub account **IrisC113**.
- Reviewee: **QI Zhang**, GitHub account **QiZhang1102**.
- Reviewed repository: [QiZhang1102/bikeshare-open](https://github.com/QiZhang1102/bikeshare-open).
- Reviewed branch: **`main`**.
- Reviewed commit: **`5a395a1592feb403a30f409d88af29a160a23f83`** ([fixed source snapshot](https://github.com/QiZhang1102/bikeshare-open/tree/5a395a1592feb403a30f409d88af29a160a23f83)).
- Comparison baseline: starter commit `01669d7`.
- Review date: **November 25, 2026**, America/Los_Angeles.
- Scope: Exercise 1's `cnt_roll_3` implementation, its test, and the recorded experimental decision.
- Assessment status: **Draft for the reviewer's personal confirmation.**

The commit above identifies the reviewed work regardless of where this report
is stored. This report reviews QI Zhang's `main`, not the contents of the
reviewer's `exercise-4&5` branch or any later revision. The remote `main`
reference matched the local snapshot when checked through the GitHub REST API.

## Auditor output, verbatim

The actual run used **Claude Code 2.1.332**, the `leakage-auditor` agent,
and local Ollama **Qwen3.5 4B (4.2B, Q4_K_M)** under the alias
`bikeshare-coder`, with a 65,536-token context. Successful session:
`8a0b565d-2c7c-40b2-a652-7f353d200175`; exit code 0; `is_error=false`.

This was an **evidence-assisted review**. Fixed-commit source excerpts with
original line numbers, independent validation results, and fault-probe results
were supplied as input. The successful run made no tool calls; these supplied
checks are not credited to the agent as experiments it independently executed.
An earlier attempt ended at its turn limit and is not counted as a completed
audit. Original inputs, runtime records, and verification logs are retained
locally and are not included in this commit. The following successful reply
is reproduced unchanged:

````text
## Review Results

**Found critical discrepancy at `src/features.py` line 79.**

### File: `src/features.py`, Line 79
```python
out["cnt_roll_3"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
# where LAG_WARMUP=7 in config.py line 55
```

**Concrete fault:** The feature name `cnt_roll_3` and the test expect a 3-day rolling mean (d-1, d-2, d-3), but code creates it with `.rolling(7)`—a 7-day window (d-6 through d-2). This leaks information 5 days in advance of what the feature name promises.

**Minimal fix:** Change `LAG_WARMUP` to `3`:
```python
out["cnt_roll_3"] = out[TARGET].shift(1).rolling(3).mean()
# or set LAG_WARMUP=3 in config.py if other features use it
```

### Verification checks:
- **Target leakage:** None found. All forbidden columns (`casual`, `registered`, `cnt`) properly excluded via `FORBIDDEN`.
- **Temporal ordering:** Temporal split is correct (TRAIN_END, VALID_END, test). No fitted transformer sees validation/test rows during `.fit()`.
- **Calendar gaps:** Missing date in data handled by `reindex_to_calendar` and lag features. Row loss bounded by test expectations.
- **Silent row loss:** Line 79 does `.dropna()` after rolling—rows with NaNs are lost without reporting, but this is pre-existing behavior documented in tests.
- **Unreported baseline:** Both mean baseline and persistence (`cnt_lag_1`) scored alongside every model (line 49-52).

**Fix required:** Correct `LAG_WARMUP` value to match `cnt_roll_3`'s intended window size; verify other features are unaffected or rename them.
````

## Reviewer assessment — draft for personal confirmation

I reject the auditor's principal finding and proposed fix. At the reviewed
commit, `src/features.py:77` actually defines
`cnt_roll_3 = out[TARGET].shift(1).rolling(3).mean()`; line 79 returns
`out.dropna().reset_index(drop=True)`. The agent quoted code that is not
present. Independent checks matched the feature to the preceding three
calendar days on all 714 retained dates. Even a seven-day window preceded by
`shift(1)` would still use past observations, so a window-name mismatch alone
would not establish future leakage. Changing `LAG_WARMUP` to 3 would alter
`cnt_lag_7` and `cnt_roll_7`, introducing a different error. I accept the
agent's general statements about temporal splitting, training-only scaling,
calendar reindexing, and the two baselines only within the limits of the
checks summarized below. The material issues supported by independent
verification are a misreported HGB validation delta and a suite that admits
an unclassified target-alias column. The first changes the reported magnitude
of deterioration; the second limits confidence in the verification barrier.
Neither establishes leakage in the existing `cnt_roll_3` implementation.

## Independent verification summary

The verification environment used Windows, Python 3.14.0, NumPy 2.5.3,
pandas 3.0.5, scikit-learn 1.9.1, and pytest 9.1.1, matching the reviewed
dependency pins. Comparisons used one thread and the fixed original estimator
settings. Faults were introduced only in disposable copies; tracked files in
the reviewed repository remained unchanged and its working tree remained clean.

### Feature availability and temporal safeguards

| Check | Observed result |
| --- | --- |
| Feature values | All 714 retained dates match raw counts on d-1, d-2, and d-3. For 2011-01-12, `(822 + 1321 + 1263) / 3 = 1135.3333333333333`. |
| Causal perturbation | Increasing `cnt` by 100000 on a selected date and later left all four demand lag/rolling features unchanged up to that date. Probes used 2011-01-12, 2011-03-18, 2012-01-01, and 2012-06-30. |
| Calendar gap | Reindexing produces 729 calendar days from 728 raw rows, including missing 2011-03-10. Retained rows resume on 2011-03-18 after the affected history window. |
| Bounded row loss | 714 model rows remain, consistent with seven warmup days plus seven days affected by missing history. |
| Temporal split and fitting | Training has 348 rows in 2011, validation 182 in H1 2012, and test 184 in H2 2012. The scaler's fitted row count is 348 and its means match the training columns. |
| Baselines | The scoring loop includes the training-mean and yesterday-count persistence baselines alongside Ridge and HGB on identical splits. |

### Tests and controlled faults

| Experiment | Actual result | Interpretation |
| --- | --- | --- |
| Full suite at the reviewed commit | 15 passed. | The current implementation passes its existing tests. |
| Full suite at the test-first commit `d83be76` | 1 failed, 14 passed; the new test raises `AttributeError` because `cnt_roll_3` is absent. | Correct red-state cause; this later reproduction does not replace the author's original failure record. |
| Remove the new feature's `shift(1)` in an isolated copy | Its test fails. | The test detects inclusion of today's target. |
| Add 1 to `cnt_roll_3` on 2011-03-18 and later in an isolated copy | Full suite: 15 passed. | The single-date test misses errors on other dates; this fault is not present in the reviewed implementation. |
| Add a new raw column `audit_count_hint = cnt` in an isolated copy | The column enters all 714 model-input rows, equals the target exactly, and the full suite still reports 15 passed. | A real classification-check blind spot, not evidence that the reviewed CSV already contains this column. |

### Validation results and the decision

The starter's actual feature builder recreated the 14-feature comparison;
the reviewed implementation produced 15. Dates and split sizes were identical.
Only validation comparisons were recomputed for the feature decision.

| Method | 14-feature validation R² | 15-feature validation R² | Delta R² | 14-feature validation MAE | 15-feature validation MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean baseline | -0.9318 | -0.9318 | 0.0000 | 2002.2 | 2002.2 |
| Persistence baseline | 0.4507 | 0.4507 | 0.0000 | 900.6 | 900.6 |
| Ridge | 0.6475 | 0.6439 | -0.0036 | 832.9 | 836.5 |
| HGB | **0.2185** | 0.1983 | **-0.0202** | 1296.6 | 1311.6 |

Two corrections follow from these checks:

1. **Experimental record:** `docs/DECISIONS.md:11` reports HGB as
   `0.1985 -> 0.1983 (delta -0.0002)`. The reproduced comparison is
   `0.2185 -> 0.1983 (delta -0.0202)`. Correct the values or provide an
   environment and original experiment that reproduce 0.1985. The correction
   changes the size of deterioration, not the conclusion that the feature
   fails the +0.01 guideline.
2. **Verification barrier:** add explicit raw-column classifications in
   `src/config.py` and a contract test reading the actual CSV header that fails
   on an unclassified column. Excluding only known `FORBIDDEN` names does not
   block a target alias under a new name.

The current decision distinguishes retaining 15 features to reproduce the
experiment from recommending the original 14 for forecasting. Default training
still includes `cnt_roll_3`; it has not switched to a 14-feature configuration.

## Limits of the review

The starter uses measured same-day weather without establishing availability
before the forecast. Its complete results therefore should not be described
as start-of-day forecasts based only on information available then.

The inherited pytest suite accesses test labels, and the training entry point
reports validation and test together. This review did not use test scores to
select the feature, but reproducing the tests did execute the inherited
test-set assertion. Final code alone cannot establish the author's complete
historical run order; these observations do not prove test-driven selection.

The fixed source and the checks above support the stated conclusions. The
auditor's original claims, the independent checks, and the assessment draft
are kept distinct. Supporting files remain local; this repository addition
contains only this self-contained audit document.
