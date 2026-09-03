# Step 16 Safety-Net Ablation Report

Dataset contains 10 paired, accepted safety-on/off runs.

## Definitions

- **slo_harm_second**: one one-second timeline row where P99 latency >300 ms, failure/offered >=1%, or completed/offered <99%
- **replica_second**: one second of controller-requested replicas; safety on uses final arbitrated command
- **scaling_action**: change between adjacent one-second requested-replica commands
- **readiness_delay**: seconds from first intervention decision until Ready replicas reach its requested final command

## Condition summary

| Condition | Runs | Off harm s | On harm s | Avoided s | Added replica-s | Added actions |
|---|---:|---:|---:|---:|---:|---:|
| missed_peak | 5 | 300 | 75 | 225 | 870 | 10 |
| persistent_negative_bias | 5 | 132 | 86 | 46 | 1105 | 0 |

The dataset separates harm remaining after reactive intervention from the extra requested capacity and scaling actions. Classification is computed per paired repetition.
