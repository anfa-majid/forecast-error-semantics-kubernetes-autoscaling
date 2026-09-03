# Validation Amendment 005 — capacity float comparison

The capacity validator used exact binary floating-point equality. For the 110% policy, Python represents `55 * 1.10` as `60.50000000000001`, while the canonical JSON value is `60.5`. The validator now uses zero-relative, `1e-9` absolute tolerance. This changes only validation arithmetic; the frozen policy, hashes, controller decisions, workload, evidence, and acceptance intent are unchanged.
