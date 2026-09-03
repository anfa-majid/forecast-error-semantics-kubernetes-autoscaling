# ANFA Step 11 forecast mutation framework

Version `1.0.0` generates 23 deterministic forecast candidates from the five Step 7 workloads. Every forecast follows the Step 9 six-second-horizon CSV contract and includes mutation metadata, error metrics, exact Step 8/9 policy replay, SVG/PNG plots, validation, and hashes.

See `STEP11.md` for the full research design and results.

## Regenerate and validate

```powershell
$root = $PWD
python tools/generate_mutations.py `
  --step7-root "..\..\workloads" `
  --policy "..\oracle\policy-config.json" `
  --catalog "$root\configuration\mutation-catalog.json" `
  --output $root

python -m unittest discover -s tests -v

python tools/validate_mutations.py `
  --root $root `
  --step7-root "..\..\workloads" `
  --step8-root "..\oracle" `
  --policy "..\oracle\policy-config.json" `
  --catalog "$root\configuration\mutation-catalog.json"
```

Only candidates selected by the later experiment-design step should enter repeated scientific runs. This package is the complete reproducible candidate catalog.
