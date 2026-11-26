# Bikeshare Demand Forecasting

DSC 180A — Methodology Assignment 6

Group Members: Haoshuo Bi, Qi Zhang, Shujia Chen

## Results

The goal of this project is to predict daily bikeshare demand while avoiding data leakage and maintaining a reproducible machine learning pipeline.

We used a chronological split, with 348 training samples from 2011, 182 validation samples from the first half of 2012, and 184 test samples from the second half of 2012.

In Exercise 1, we added `cnt_roll_3`, which represents the average number of rides over the previous three calendar days. This feature uses only historical information available before the prediction date.

The following table compares the original 14-feature pipeline with the updated 15-feature pipeline. All MAE values are measured in rides per day.

| Features | Model | Validation R2 | Validation MAE | Test R2 | Test MAE |
|---|---|---:|---:|---:|---:|
| 14 | Mean Baseline | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| 14 | Persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| 14 | Ridge | 0.6475 | 832.9 | 0.5833 | 947.1 |
| 14 | HGB | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| 15 | Mean Baseline | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| 15 | Persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| 15 | Ridge | 0.6439 | 836.5 | 0.5800 | 946.2 |
| 15 | HGB | 0.1983 | 1311.6 | -0.5338 | 1998.7 |

All results in this table use the original, untransformed prediction target.

## Headline finding

Ridge performed better than the original Histogram Gradient Boosting (HGB) model on the chronological test set. With 15 features, Ridge achieved a test R2 of 0.5800, while HGB achieved -0.5338. Despite its negative test R2, HGB still outperformed the mean baseline, which had a test R2 of -2.1441. One possible explanation is that bikeshare demand increased over time, and the tree-based model had difficulty extrapolating beyond its training range. However, Ridge's test MAE of 946.2 was higher than persistence's MAE of 840.1, showing that a higher R2 does not necessarily mean better daily forecasting performance. Adding `cnt_roll_3` decreased validation R2 by 0.0036 for Ridge and 0.0202 for HGB, so we retained the feature for reproducibility but recommend the original 14-feature set based on validation performance.

## Exercise 4: target transformation

**Design.** We investigated whether transforming the prediction target could help HGB compete with Ridge. Instead of directly predicting daily ride counts, we used the average ride count from the previous seven days as a historical demand reference.

Let `m_t = mean(y_(t-1), ..., y_(t-7))`.

We compared two target transformations:

- Additive residual: `z_t = y_t - m_t`, inverted as `y_hat_t = m_t + z_hat_t`.
- Log ratio: `z_t = log(1 + y_t) - log(1 + m_t)`, inverted as `y_hat_t = exp(log(1 + m_t) + z_hat_t) - 1`.

Only training labels are transformed. The transformed targets are not included in the input features. Predictions are converted back to the original ride-count scale before calculating R2 and MAE, without clipping or inverse-log bias correction.

**Selection and results.** All comparisons use the same 15 input features and chronological split. Ridge uses `alpha=1`, while HGB uses `max_iter=300` and `random_state=0`. Neither model is refitted on validation.

| Model | Validation R2 | Validation MAE | Test R2 | Test MAE |
|---|---:|---:|---:|---:|
| Seven-day Mean Baseline | 0.5945 | 823.9 | 0.4796 | 871.6 |
| Ridge - Additive Residual | 0.6545 | 822.0 | 0.5890 | 932.8 |
| HGB - Additive Residual | 0.7209 | 722.4 | - | - |
| Ridge - Log Ratio | 0.5144 | 972.4 | 0.1948 | 1360.7 |
| HGB - Log Ratio (Selected) | 0.7488 | 687.6 | 0.6166 | 847.5 |

The selection rule maximized HGB validation R2, using MAE to break ties. We selected the log-ratio transformation for HGB and additive residual Ridge as the main linear comparison.

The choices, source and data hashes, and output destination were frozen before the transformed test evaluation. One subsequent comparison batch evaluated the frozen models on the 184 test days. The unselected residual HGB model was not evaluated on the test set.

The original pipeline's test results were already available from earlier exercises. Therefore, the test set was not completely unseen across the entire assignment. However, no transformed test score was used to select the transformation.

**Interpretation.** The selected HGB model achieved a test R2 of 0.6166 and an MAE of 847.5, compared with 0.5890 and 932.8 for residual Ridge. However, persistence still achieved a slightly lower test MAE of 840.1.

The transformation is defensible because it separates the historical demand level from short-term changes in demand. It allows HGB to predict relative changes rather than directly extrapolate future ride counts.

The original HGB predictions peaked at 5625.3, below the training maximum of 6043. The transformed HGB predictions reached 9497.0 and exceeded the training maximum on 79 test days.

However, the method assumes that the previous seven daily ride counts are available when making each prediction. The historical reference may lag behind sudden demand changes, and inverse-log bias remains uncorrected. The experiments also assume that the required calendar and weather inputs are available at prediction time. The availability of observed same-day weather at the start of the day has not been verified.

Overall, target transformation improved HGB substantially, but the results do not prove that it is always better than simpler forecasting methods.

**Reproduction.** The command `make all` reproduces the untransformed canonical metrics. The transformation experiment remains behind the `--target-transform` option. Additional reproduction instructions are provided in `README.md`.

## Exercise 5: ridge vs persistence

We would not deploy the current untransformed Ridge model over persistence if the main objective is to minimize absolute daily forecasting error. Using the 15-feature pipeline, Ridge achieved a test R2 of 0.5800, compared with 0.5099 for persistence, corresponding to approximately 14.3% lower MSE. However, Ridge had an MAE of 946.2, while persistence had an MAE of 840.1. This means Ridge made an average absolute error that was 106.1 rides per day higher, or approximately 12.6% worse. Persistence also requires fewer inputs because it simply uses the previous day's ride count as the next prediction. If large prediction errors have a much higher operational cost, Ridge's higher R2 may be useful. However, without evidence of an improvement under that specific cost function, we would prefer persistence because it is simpler and has a lower MAE. This conclusion concerns the untransformed Ridge model, not the transformed HGB experiment in Exercise 4.

## Attribution

We used Claude Code with local language models served through Ollama, together with AI assistance during development and report preparation.

- Haoshuo Bi: Used Qwen3.5 9B via Ollama as `bikeshare-coder`, with Q4_K_M quantization and a configured context window of 65,536 tokens.
- Qi Zhang: Used Qwen3.5 2B via Ollama (`bikeshare-coder`, 65,536-token context), then switched to Recursive Flint via OpenRouter for Exercise 1. Used Qwen2.5-Coder 3B via Ollama for Exercise 3.
- Shujia Chen: Used Qwen3.5 4B (4.2B parameters, Q4_K_M quantization) via Ollama as `bikeshare-coder`, with a 65,536-token context window. No model switching occurred during local experiments and self-auditing.

**Agent-generated contributions**

- Exercise 1: Assisted with implementing `cnt_roll_3` in `src/features.py` and its corresponding test in `tests/test_leakage.py`.
- Exercise 2: Assisted with creating `.claude/skills/seed-fault/SKILL.md`, updating verification tests, and repairing controlled faults.
- Exercise 2: Assisted with updates to `src/config.py`, `tests/test_contract.py`, `tests/test_leakage.py`, and the leakage-checking hook.
- Exercise 3: Used the `leakage-auditor` subagent to examine teammate implementations.
- Exercise 4: Assisted with implementing target transformations, inverse transformations, and related verification tests.
- Report preparation: AI assisted with organizing experiment results and drafting this report.

**Human decisions and contributions**

- Qi Zhang (Exercise 1): Selected and evaluated the three-day rolling mean feature. Decided to retain the feature for reproducibility while recommending the original feature set based on validation performance.
- Haoshuo Bi (Exercise 2): Supervised the seeded-fault experiments, examined actual test failures and hook outputs, reviewed the verification changes, and documented limitations of automated enforcement.
- Shujia Chen (Exercises 4 and 5): Proposed the target transformations, defined the validation-based selection rule, and evaluated the trade-off between Ridge and persistence.
- Exercise 3: All three group members completed peer audits and independently evaluated the agent findings. Qi Zhang identified the missing Bash cp experiment, which Haoshuo Bi subsequently completed. Shujia Chen rejected an incorrect auditor recommendation to change LAG_WARMUP and verified the original three-day rolling mean implementation.

Haoshuo Bi independently executed eight targeted tests while reviewing Exercises 4 and 5. All eight selected tests passed. The peer audit was limited to static review and targeted testing rather than a complete training reproduction.


The peer reviews also identified an incorrect HGB validation delta and a missing Bash cp permission experiment. The validation record was corrected, and the cp experiment was completed. The project permission rules blocked the attempted copy, and the original raw-data hash remained unchanged.

Methodological decisions are recorded in `docs/DECISIONS.md`. Controlled fault experiments are recorded in `docs/SEEDED_FAULTS.md`. Peer audit findings, original agent outputs, and verification limitations are recorded in `docs/AUDIT.md`.
## Verification

On 2026-11-25, a fresh checkout of merged main `95a9507` was verified in a new
isolated Python 3.12.3 virtual environment on Ubuntu 24.04 / WSL, with the exact
versions in `requirements.txt`. `pip check` found no broken requirements,
`make all` completed successfully, and `make test` passed all **30 tests**
(22.95 seconds), reproducing the untransformed reference scores. Subsequent
documentation updates through `6683f55` were incorporated; source code, tests,
requirements, and Makefile were unchanged. Both
validation-only target experiments reproduced the reported scores:
residual Ridge 0.6545 / 822.0, residual HGB 0.7209 / 722.4, log-ratio Ridge
0.5144 / 972.4, and log-ratio HGB 0.7488 / 687.6 (R² / MAE).
No transformed held-out evaluation was rerun during these verification checks.

Independent checks also matched all four lag/rolling features against raw
calendar-day counts on every one of the 714 retained dates, verified that
future-count changes at four cutoffs did not affect available historical
features, and confirmed the Ridge scaler was fitted on the 348 training rows.
No exact affine target identity was found among subsets of up to three actual
model inputs. These checks do not prove the absence of every possible form of
leakage. Measured same-day weather must be available at the chosen forecast
time; a start-of-day deployment would require forecast weather or a revised
feature set and a new evaluation.

Final merged-main verification and artifact packaging were performed with
Codex (GPT-6). Codex reproduced the canonical pipeline and the two validation
experiments, checked the Exercise 5 arithmetic, and updated verification
documentation. It did not choose a new transformation, change model settings,
or rerun transformed test evaluation. The earlier Qwen attribution describes
the original experiments.
