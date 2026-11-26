---
name: seed-fault
description: Inject one controlled fault, capture verification failures, and restore the correct code.
---

# Seed fault: $ARGUMENTS

1. Inspect the relevant source file and confirm the requested fault.
2. Use the Edit tool to introduce only that fault.
3. Observe and preserve the actual PostToolUse hook stderr.
4. Run make test and show the real failing output.
5. Stop and wait for the user's permission before repairing the fault.
6. After approval, restore the correct code using Edit.
7. Run make test again and show the passing output.
8. Report the exact change, failure, repair, and number of agent turns.

Never modify raw data or weaken tests.
Never fabricate test or hook output.
Do not commit automatically.
