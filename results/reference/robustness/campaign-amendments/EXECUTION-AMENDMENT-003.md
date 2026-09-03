# Execution Amendment 003 — safety endpoint lifetime

Run `r19-v112-sp1-miss-r02-s1` attempt 1 completed 180 predictive decisions but lost safety observation 179 to `Connection refused`.

The controller remains alive after its predictive loop, but marks `/readyz` false. Kubernetes therefore removed the pod from the safety Service before the final observation was posted. The Service now sets `publishNotReadyAddresses: true`, preserving routing to the still-live safety endpoint until the runner terminates the controller.

This changes no workload, forecast, observation value, safety threshold, persistence, capacity lookup, arbitration, controller binary, or measured outcome. The runner still waits for controller readiness before T0. The invalid attempt remains preserved and excluded.
