# Exercise 3 - Peer Audit

## Review Identification

- Reviewer: Shujia Chen (IrisC113)
- Reviewee: QI Zhang (QiZhang1102)
- Repository: https://github.com/QiZhang1102/bikeshare-open
- Reviewed branch: main
- Reviewed commit: [5a395a1592feb403a30f409d88af29a160a23f83](https://github.com/QiZhang1102/bikeshare-open/tree/5a395a1592feb403a30f409d88af29a160a23f83)
- Comparison baseline: 01669d7
- Review date: November 25, 2026
- Scope: Exercise 1's `cnt_roll_3` implementation, its test, and the recorded feature-selection decision.
- Assessment status: Final reviewer judgment; corrections recommended below.

The reviewed branch and commit identify the work being assessed. Storing
this report on `exercise-4&5` does not change its subject: QI Zhang's `main`
at the revision above.

### AI Audit Results

The local `leakage-auditor` alleged that `cnt_roll_3` used a seven-day window
and recommended changing `LAG_WARMUP` to 3. This principal finding is
inconsistent with the reviewed source. Its reply is preserved verbatim at
the end of this document; the assessment below explains why the finding is
rejected.

| Check | Agent finding |
| --- | --- |
| Target leakage | Reported no forbidden-column violation, but separately alleged leakage from a supposed rolling-window mismatch. The latter allegation is rejected. |
| Temporal ordering | Reported a date-based split and training-only fitting. |
| Calendar gaps | Reported that reindexing handles missing dates. |
| Silent row loss | Noted `dropna()` and considered the loss accounted for by the existing contract test. |
| Unreported baselines | Reported that both mean and persistence baselines are scored. |

The successful run used Claude Code 2.1.332 with local Ollama Qwen3.5 4B
(4.2B, Q4_K_M; alias `bikeshare-coder`; 65,536-token context).
Session `8a0b565d-2c7c-40b2-a652-7f353d200175` completed with exit code 0
and `is_error=false`.

### Human Judgment

I reject the auditor's principal finding and proposed fix. At the reviewed
commit, `src/features.py:77` actually uses
`out[TARGET].shift(1).rolling(3).mean()`, and line 79 returns
`out.dropna().reset_index(drop=True)`. The quoted seven-day definition is
not present, and independent checks matched the feature on all 714 retained
dates. Even a seven-day window preceded by `shift(1)` would still use past
observations, so a window-name mismatch alone would not establish future
leakage. Changing `LAG_WARMUP` to 3 would instead alter `cnt_lag_7` and
`cnt_roll_7`. I accept the agent's general observations about the split,
training-only scaling, calendar handling, and baselines only within the
limits of the checks below. The supported material issues are the HGB
validation delta recorded incorrectly in `docs/DECISIONS.md:11` and a suite
that fails to reject an unclassified target-alias column. These affect the
reported magnitude of deterioration and confidence in the verification
barrier, respectively; neither establishes leakage in the current
`cnt_roll_3` implementation.

### Independent Verification

Command, executed in a checkout of the reviewed commit:

```powershell
python -m pytest -q
```

Actual output:

```text
...............                                                          [100%]
15 passed in 6.85s
```

The verification environment used Windows, Python 3.14.0, NumPy 2.5.3,
pandas 3.0.5, scikit-learn 1.9.1, and pytest 9.1.1, matching the reviewed
dependency pins. Comparisons used one thread and fixed estimator settings.

Additional independent checks produced these results:

| Check | Observed result |
| --- | --- |
| Named-date calculation | For 2011-01-12, `(822 + 1321 + 1263) / 3 = 1135.3333333333333`. The feature matches this value and all 714 retained dates match their three prior calendar days. |
| Past-only availability | Increasing `cnt` by 100000 on a selected date and later left all four demand lag/rolling features unchanged up to that date. Probes used 2011-01-12, 2011-03-18, 2012-01-01, and 2012-06-30. |
| Missing calendar day and row loss | Reindexing represents 2011-03-10 explicitly. 728 raw rows become 714 model rows, consistent with seven warmup days and seven days affected by missing history. Retained rows resume on 2011-03-18. |
| Splits and scaling | Train/validation/test have 348/182/184 rows. The scaler's fitted row count is 348 and its means equal the training-column means. |
| Test-first commit `d83be76` | 1 failed, 14 passed; the new test raises `AttributeError` because `cnt_roll_3` does not yet exist. This later reproduction does not replace the author's original saved output. |
| Isolated same-day fault | Removing the new feature's `shift(1)` makes its test fail. |
| Isolated later-date fault | Adding 1 to `cnt_roll_3` on 2011-03-18 and later still produces 15 passed. This exposes the single-date test's limited coverage; the fault is not present in the reviewed code. |
| Isolated unclassified-column fault | Adding `audit_count_hint = cnt` to a disposable raw CSV admits a perfect target alias to all 714 model-input rows; the suite still produces 15 passed. This is a test blind spot, not an existing leaked column in the reviewed CSV. |

The starter's actual feature builder recreated the 14-feature comparison;
the reviewed implementation created 15. Dates and split sizes were identical.
Only validation comparisons were recomputed for the feature decision.

| Method | 14-feature validation R² | 15-feature validation R² | Delta R² | 14-feature validation MAE | 15-feature validation MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean baseline | -0.9318 | -0.9318 | 0.0000 | 2002.2 | 2002.2 |
| Persistence baseline | 0.4507 | 0.4507 | 0.0000 | 900.6 | 900.6 |
| Ridge | 0.6475 | 0.6439 | -0.0036 | 832.9 | 836.5 |
| HGB | **0.2185** | 0.1983 | **-0.0202** | 1296.6 | 1311.6 |

`docs/DECISIONS.md:11` instead records HGB as
`0.1985 -> 0.1983 (delta -0.0002)`. The reproduced values above change
the magnitude of deterioration, not the conclusion that the feature fails
the +0.01 guideline. The decision correctly distinguishes retaining 15
features to reproduce the experiment from recommending 14 for forecasting;
default training still includes `cnt_roll_3`.

### Limitations

The successful agent run was evidence-assisted: fixed-commit source excerpts
with original line numbers, validation results, and fault-probe observations
were supplied as input. It made no tool calls and was not a blind independent
verification. The independent checks above must not be credited as experiments
performed by that agent. An earlier tool-based attempt ended at its turn limit
and is not counted as a completed review.

The inherited pytest suite accesses test labels, and the training entry point
reports validation and test scores together. This review did not use test
scores to choose the feature, but reproducing the tests executed the inherited
test-set assertion. Final code alone cannot establish the author's complete
historical run order or prove test-driven selection. Measured same-day weather
also lacks a demonstrated start-of-day availability guarantee.

No changes were made to the reviewed source code. Its tracked-file hashes
remained unchanged and its working tree stayed clean. Original runtime records
and verification artifacts remain local; this repository update contains only
this audit document.

### Final Decision

Recommendation: retain the verified three-day implementation, correct the HGB
validation record, and add a raw-column contract that fails on unclassified
CSV headers. The agent's proposed `LAG_WARMUP` change should not be applied.
These recommendations are my final judgment for the reviewed commit.

## Original leakage-auditor Output (Verbatim)

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
