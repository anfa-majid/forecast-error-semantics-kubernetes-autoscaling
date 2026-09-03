# Execution Amendment 002 — controller v1.1.2 replacement block

Two independent persistence-3s attempts returned HTTP 500 at the first observation after a safety-triggered scale-up. Controller v1.1.2 adds only a bounded Ready-replica read retry (three attempts, 50 ms spacing). Safety logic and all experimental inputs remain unchanged.

To prevent controller version from confounding the persistence comparison, all ten safety-persistence cells receive new v1.1.2 run IDs and must be rerun. Prior v1.1.1 evidence is preserved, explicitly superseded, and excluded from the replacement comparison. The twenty forecast-horizon cells remain valid because their family is analyzed independently and completed under v1.1.1. Remaining capacity cells will use v1.1.2 and will be version-bounded in reporting.
