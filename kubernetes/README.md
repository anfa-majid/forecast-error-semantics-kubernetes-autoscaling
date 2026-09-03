# Kubernetes manifests

- `benchmark/`: benchmark Deployment, Service, ServiceMonitor, and validator.
- `controller/`: RBAC, fixed policy, runtime/forecast mounts, safety service,
  and the predictive-controller Deployment.
- `cluster/`: three-node kind topology for functional reproduction.
- `monitoring/`: pinned kube-prometheus-stack values and scrape configuration.

The local kind topology is not performance-equivalent to the three-node K3s
study environment. Review the active context before applying any manifest.
