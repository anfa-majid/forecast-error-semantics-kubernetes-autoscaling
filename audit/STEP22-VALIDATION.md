# Step 22 packaging validation

Validation date: 2026-09-03 (Asia/Karachi)

## Passed checks

- All required artifact categories are present in the normalized repository.
- No file exceeds 95 MiB; the complete repository is approximately 52 MiB.
- The privacy/portability scan found no personal home path, original cloud
  endpoint, SSH account, private-key block, or historical F-drive dependency.
- All JSON files parse, all PowerShell files parse, and all Python files
  compile.
- All packaged Python unit and contract test suites pass.
- The five workloads, five oracle timelines, 23 mutation candidates, and seven
  accepted accuracy-matched pairs pass their independent validators.
- Mutation regeneration compared 122 files byte-for-byte with no mismatch.
- Matching regeneration compared 239 files byte-for-byte with no mismatch.
- Statistical reconstruction validated all 142 accepted runs and regenerated
  six figures.
- The 12 core Step 18 tables and figures are byte-identical to the sealed
  reference outputs.
- Both pinned Docker images built successfully. The controller build executed
  and passed `go test ./... -count=1` with the pinned Go 1.24.6 toolchain.
- Every packaged Kustomize target rendered successfully.
- A three-node kind/Kubernetes v1.34.0 cluster became Ready, both packaged
  images were imported, and the live functional example passed its strict
  evidence validator. See `audit/LIVE-EXAMPLE-VALIDATION.md`.
- The Apache-2.0 and CC BY 4.0 files match their official legal texts after
  newline normalization. `CITATION.cff` passes the Citation File Format 1.2.0
  schema validator.
- The release manifest verifies 860 packaged, non-generated files by SHA-256.

## Checks still required before public release

- Repeat the release test from a fresh clone.
- Deposit the multi-gigabyte raw campaign separately and record its immutable
  URL/DOI and archive SHA-256.

The artifact is therefore **offline- and functional-reproduction validated**
but not yet **public-release certified**. The live kind run validates the
workflow, not statistical or performance equivalence with the Azure/K3s study.
