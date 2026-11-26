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
