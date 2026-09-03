# Reactive safety-net reference

This directory contains the independently testable Python reference model for
the overload-triggered safety rule and its observation contract. The deployed
single-writer implementation is integrated into the Go controller under
`controller/`; the reference model is retained to make arbitration and release
semantics independently inspectable.

The safety net may raise the predictive command but never lower it. It is an
ablation component, not a second Kubernetes writer.
