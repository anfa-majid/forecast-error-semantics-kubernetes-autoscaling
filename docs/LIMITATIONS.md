# Artifact limitations

## Scientific limits

The evidence is limited to one benchmark application, one three-node Azure/K3s
cluster, CPU-oriented behavior, horizontal scaling from one to four replicas,
five workload families, one fixed predictive policy, and one fixed overload
safety rule. The artifact does not establish production prevalence or universal
effects across autoscalers, applications, clusters, or forecasting models.

## Reproduction limits

- Exact statistical analysis and figure reproduction are self-contained.
- Full raw-to-processed reconstruction requires the separately archived
  multi-gigabyte raw campaign.
- The representative run omits request-level JSONL to keep the Git repository
  compact; its aggregate summary and normalized timeline are included.
- The local kind workflow is a functional demonstration. Its latency and Pod
  readiness distributions are not performance-equivalent to the Azure/K3s
  experiment environment.
- The local example reaches the Service through `kubectl port-forward`, which
  can remain attached to one backend. Its request latency therefore does not
  validate multi-Pod load balancing or the empirical capacity profile.
- Cloud setup, registry access, VM provisioning, and SSH credentials cannot be
  distributed and must be supplied by the reproducer.
- Container image digests from the original environment document what was run;
  rebuilding the supplied source creates new registry digests.
- Step 16 Pod-event fields are missing because remote Kubernetes snapshot
  collection failed there; Ready replicas came from the controller's live
  Deployment reads and the limitation is preserved in the data dictionary.

## Statistical limits

Primary comparisons contain eight matched pairs. Safety and prospective
robustness comparisons contain five pairs, making the smallest possible
two-sided exact p-value 0.0625. Most primary effects did not cross 0.05 after
the prespecified domain-wise Holm correction. These facts are preserved in the
analysis and must not be reinterpreted as equivalence or universal null effects.
