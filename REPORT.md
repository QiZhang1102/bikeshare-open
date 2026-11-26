# Exercises 4 and 5

## Reference results

All scores use the original daily-ride count scale; MAE is rides/day. These untransformed reference scores use the existing 15-feature pipeline, including `cnt_roll_3`. The split is 2011 training (348 rows), H1 2012 validation (182), and H2 2012 test (184).

| Feature set | Model | Validation R² | Validation MAE | Test R² | Test MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| 15 features | baseline_mean | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| 15 features | baseline_persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| 15 features | ridge | 0.6439 | 836.5 | 0.5800 | 946.2 |
| 15 features | hgb | 0.1983 | 1311.6 | -0.5338 | 1998.7 |

# Exercise 4: target transformation

**Design.** With the existing historical reference `m_t = mean(y_(t-1), ..., y_(t-7))`, compare two training targets:

- Additive residual: `z_t = y_t - m_t`; invert as `y_hat_t = m_t + z_hat_t`.
- Log ratio: `z_t = log(1 + y_t) - log(1 + m_t)`; invert as `y_hat_t = exp(log(1 + m_t) + z_hat_t) - 1`.

Only training labels are transformed; they never enter the predictors. Inversion uses predicted corrections and past counts. Scores are computed after inversion, without clipping or inverse-log bias correction. This assumes rolling one-day forecasts with seven observed preceding counts and the starter's calendar/weather availability; it is not a batch forecast without daily observations.

**Selection and results.** Every comparison uses the same 15 inputs and 2011 training rows, with Ridge `alpha=1` and HGB `max_iter=300, random_state=0`; neither is refitted on validation. The original-target comparisons are in Results; the additional comparisons are:

| Model / representation | Validation R² | Validation MAE | Test R² | Test MAE |
| --- | ---: | ---: | ---: | ---: |
| Prior-seven-day mean baseline | 0.5945 | 823.9 | 0.4796 | 871.6 |
| Ridge / additive residual | 0.6545 | 822.0 | 0.5890 | 932.8 |
| HGB / additive residual | 0.7209 | 722.4 | — | — |
| Ridge / log ratio | 0.5144 | 972.4 | 0.1948 | 1360.7 |
| HGB / log ratio (selected) | 0.7488 | 687.6 | 0.6166 | 847.5 |

The predeclared rule maximized HGB validation R², breaking ties by MAE, and selected the log ratio. The strongest validation-tested linear control, residual Ridge, was also fixed before evaluation. The choices, source/data hashes and output destination were frozen in a selection manifest. Validation runs excluded H2 2012 rows. One subsequent comparison batch evaluated the frozen models on all 184 test days; the unselected residual HGB was not tested (—). Earlier exercises had already exposed original-pipeline test scores, so the test set was not globally unseen; no transformed test score informed this selection.

**Interpretation.** Selected HGB beats residual Ridge on test R² (0.6166 versus 0.5890) and MAE (847.5 versus 932.8), but persistence retains a 7.4-ride MAE advantage. The method is defensible as a rolling demand level plus a nonlinear relative correction, with useful count-scale improvements over the rolling mean and linear controls. It does not show that an unmodified tree learned trend extrapolation: original HGB peaks at 5625.3, below the training maximum of 6043; normalized HGB reaches 9497.0 and exceeds that old maximum on 79 test days. Relative deviations must transfer over time, the seven-day level may lag changes, and inverse-log bias remains uncorrected. The validation advantage narrows on test; this is evidence of competitiveness on one split, rather than general superiority.

**Reproduction.** `make all` reproduces the untransformed canonical metrics. The transformation remains behind `--target-transform`; fresh-checkout validation and frozen-test commands are in [README.md](README.md#target-transformation-experiment-exercise-4). Experiment outputs under `reports/exercise4/` are local and ignored by Git.

# Exercise 5: ridge vs persistence

For daily operations with costs proportional to absolute forecast error, I would retain “yesterday again” rather than deploy the current untransformed Ridge. On the same 184 test days, Ridge raises R² from 0.5099 to 0.5800 (+0.0701, approximately 14.3% lower MSE), but increases MAE from 840.1 to 946.2 rides/day: 106.1 more, or 12.6% worse. Both beat the training mean (R² −2.1441, MAE 2847.7), which does not establish Ridge's value over persistence. Lower MSE could matter if large misses carry disproportionately high costs; that would require an explicit cost-weighted evaluation. Ridge also requires calendar/weather inputs, lag construction, scaling and fitted coefficients, while persistence needs only the latest count. Without a gain under the stated absolute-error objective, I would keep the simpler baseline. This judgment concerns canonical Ridge; Exercise 4's normalized HGB is a separate experiment.

# Experiment setup

Local Claude Code used Qwen3.5 4B via Ollama for Exercise 4.
The author proposed the transformations, validation selection rule and
Exercise 5 cost assumption, and reviewed the generated implementation.

## Verification

On 2026-11-25, all 28 tests passed. The ingestion, feature and untransformed training commands
completed successfully, reproducing the untransformed reference scores. Both
validation-only target experiments reproduced the reported scores:
residual Ridge 0.6545 / 822.0, residual HGB 0.7209 / 722.4, log-ratio Ridge
0.5144 / 972.4, and log-ratio HGB 0.7488 / 687.6 (R² / MAE).
No transformed held-out evaluation was rerun during these verification checks.
