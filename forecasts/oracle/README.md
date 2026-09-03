# ANFA Step 8 oracle reference

This package implements the deterministic desired-replica reference for the Step 7 workload suite.

## Regenerate

From this directory, run:

```powershell
python tools/generate_oracle.py --step7-root "..\..\workloads"
python -m unittest discover -s tests -v
python tools/validate_oracle.py
```

The policy engine in `tools/policy.py` accepts any workload input. Oracle mode supplies true workload at `t+6`; experimental mode must supply its forecast to this same policy behavior.

The future Go controller must reproduce `samples/golden-policy-vectors.json` before it is accepted. The current environment did not provide a Go compiler, so no unverified Go implementation is included.
