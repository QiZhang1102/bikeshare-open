# Exercise 3 - Peer Audit

## Review by Haoshuo Bi

- Date: 2026-11-25
- Reviewed exercises: Exercise 4 and Exercise 5
- Reviewed branch: exercise-4&5
- Reviewed commit: 2f90dfb
- Reviewer: Haoshuo Bi
- AI tool: Claude Code with bikeshare-coder via Ollama
- Subagent: leakage-auditor
- Pull request: https://github.com/QiZhang1102/bikeshare-open/pull/2

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
