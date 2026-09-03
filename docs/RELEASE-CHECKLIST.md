# Release checklist

## Content

- [x] Benchmark application and Dockerfile included.
- [x] Predictive controller and reactive safety code included.
- [x] Kubernetes and monitoring manifests included.
- [x] Workload, forecast, mutation, matching, experiment, processing, and
  analysis programs included.
- [x] Analysis-ready dataset and representative run included.
- [x] Reference statistical and robustness results included.
- [x] Setup, reproduction, data, provenance, and limitations documented.

## Verification

- [x] Statistical outputs and six figures reproduced from the 142-run dataset.
- [x] Twelve core reproduced artifacts match the reference files byte-for-byte.
- [x] Deterministic workload/oracle/mutation/matching validators pass from the
  packaged paths.
- [x] All Python unit tests pass from the packaged paths.
- [x] Go unit tests pass with Go 1.24.6 through the pinned controller Docker build.
- [x] Kubernetes manifests render successfully.
- [x] One complete live example is executed and strictly validated on a
  disposable three-node kind cluster.
- [x] Execute the final corrected runner end-to-end once without invoking the
  recovery finalizer.
- [x] No credential, private endpoint, username, or machine-specific path is
  present.
- [x] Repository checksum manifest is generated and verified.

## Publication administration

- [x] Select and add explicit code and data licenses.
- [x] Add author and affiliation metadata to `CITATION.cff`.
- [ ] Add the paper DOI or archival citation when available.
- [ ] Upload the complete raw campaign to a durable repository and record its
  DOI/URL and SHA-256 digest in `docs/DATA.md`.
- [ ] Create an immutable Git tag and hosted release archive.
- [ ] Test the release from a fresh clone without access to the development
  machine.
