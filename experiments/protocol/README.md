# Step 14 Final Experimental Protocol v1.0.0

This directory is the frozen, outcome-blind specification for the final autoscaling experiments. The authoritative protocol is `configuration/frozen-protocol.json`; the execution order is `matrix/randomized-run-order.csv`.

Do not edit the matrix after final outcome collection begins. Record unavoidable operational changes in a new version and preserve this package unchanged.

Validation (using the bundled/project Python runtime):

```text
python scripts/validate_step14.py
```

Expected result: `STEP 14 VALIDATION PASSED: 142 unique frozen runs`.
