[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ClusterName = 'forecast-error-artifact',
    [string]$NodeImage = 'kindest/node:v1.34.0',
    [switch]$InstallMonitoring
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$required = @('docker', 'kind', 'kubectl')
if ($InstallMonitoring) { $required += 'helm' }
foreach ($command in $required) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command"
    }
}

docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running.' }

$expectedContext = "kind-$ClusterName"
if (kind get clusters | Where-Object { $_ -eq $ClusterName }) {
    Write-Host "Using existing disposable kind cluster: $ClusterName"
} elseif ($PSCmdlet.ShouldProcess($ClusterName, 'Create disposable kind cluster')) {
    kind create cluster --name $ClusterName --image $NodeImage --config (Join-Path $repo 'kubernetes\cluster\kind-config.yaml')
    if ($LASTEXITCODE -ne 0) { throw 'kind cluster creation failed.' }
}

kubectl config use-context $expectedContext | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to select context $expectedContext" }

if ($PSCmdlet.ShouldProcess('local Docker daemon', 'Build benchmark and controller images')) {
    docker build -t forecast-error-study/benchmark-app:0.1.0 (Join-Path $repo 'app')
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark image build failed.' }
    docker build -t forecast-error-study/predictive-autoscaler:1.1.2 (Join-Path $repo 'controller')
    if ($LASTEXITCODE -ne 0) { throw 'Controller image build failed.' }
}

kind load docker-image --name $ClusterName forecast-error-study/benchmark-app:0.1.0 forecast-error-study/predictive-autoscaler:1.1.2
if ($LASTEXITCODE -ne 0) { throw 'Image import into kind failed.' }

kubectl --context $expectedContext apply -f (Join-Path $repo 'kubernetes\benchmark\deployment.yaml')
kubectl --context $expectedContext apply -f (Join-Path $repo 'kubernetes\benchmark\service.yaml')
kubectl --context $expectedContext rollout status deployment/benchmark-app --timeout=180s

if ($InstallMonitoring) {
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    helm upgrade --install artifact-monitoring prometheus-community/kube-prometheus-stack `
        --version 88.0.1 --namespace monitoring --create-namespace `
        --values (Join-Path $repo 'kubernetes\monitoring\kube-prometheus-stack-values.yaml')
    kubectl --context $expectedContext apply -f (Join-Path $repo 'kubernetes\benchmark\servicemonitor.yaml')
}

Write-Host "PASS: local environment is ready on context $expectedContext"
