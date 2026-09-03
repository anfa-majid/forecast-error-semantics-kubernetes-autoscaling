# ANFA Step 12 accuracy-matched forecast dataset

Version `1.0.0` contains seven fixed, same-workload forecast pairs with exactly equal MAE and RMSE but different error semantics. The outcome-blind grid search considered 96 candidates and 428 cross-semantic comparisons, recording 395 explicit rejections.

See `STEP12.md` for the complete protocol, accepted pairs, blinding controls, results, limitations, and completion assessment.

## Rebuild and validate

```powershell
python tools/build_dataset.py `
  --root . `
  --step7-root "..\..\workloads" `
  --step8-policy "..\oracle\policy-config.json" `
  --step11-root "..\mutations"

python -m unittest discover -s tests -v

python tools/validate_dataset.py `
  --root . `
  --step7-root "..\..\workloads" `
  --step8-policy "..\oracle\policy-config.json" `
  --step11-root "..\mutations"
```
