# Controller reliability amendment — v1.1.2

The safety endpoint intermittently returned HTTP 500 immediately after a safety-triggered scale-up because a transient Kubernetes Ready-replica read was treated as fatal. This occurred at the same intervention boundary in two independent Step 19 attempts.

Version 1.1.2 adds a bounded Ready-replica read retry: at most three attempts separated by 50 ms. It does not change observations, overload definition, persistence, capacity lookup, replica calculation, release hold, arbitration, or scaling commands. Exhausted retries remain fatal and invalidate the run.

Because controller version is part of the experimental treatment, all Step 19 safety-persistence cells must use the same v1.1.2 binary. Previously valid safety-persistence cells are retained as historical evidence but excluded from the replacement comparison.
