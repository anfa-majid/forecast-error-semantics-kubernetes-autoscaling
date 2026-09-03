# Execution Amendment 001 — T0 staging margin

Date: 2026-08-23  
Scope: prospective Step 19 cloud campaign execution only

## Trigger

Run `r19-h03-b-r02-s0`, attempt 1, was invalidated before outcome analysis. The workload was delivered exactly, but the predictive controller emitted zero decisions. Its preserved log reported `fatal class=t0 error="t0 must be in the future"`.

## Amendment

- Enforce a minimum 240-second interval between T0 construction and the measured workload start.
- Extend the Kubernetes collector by the same amount so the measured window remains fully covered.
- Refuse to apply the controller when fewer than 90 seconds remain before T0.
- Retain the existing post-rollout 30-second guard.

## Scientific impact

This changes only pre-run staging time. It does not change workload traces, forecast traces, forecast horizon, controller policy, safety policy, capacity assumptions, random seeds, measured duration, or validation criteria. The invalid attempt remains preserved and excluded under the frozen quality-only rules.
