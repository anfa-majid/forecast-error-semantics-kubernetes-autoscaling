param(
  [int[]]$Rates = @(25, 50, 75, 100, 125, 150),
  [int]$DurationSeconds = 60,
  [int]$RecoverySeconds = 30,
  [int]$PointWarmupSeconds = 0,
  [string]$RunLabel = "pilot",
  [int]$Replicas = 1,
  [switch]$SkipWarmup
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$go = Join-Path $env:LOCALAPPDATA "Programs\Go\bin\go.exe"
$runId = $RunLabel + "-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$runDir = Join-Path $root "step5\runs\$runId"
$summary = @()
$prometheusJob = $null

function Invoke-PrometheusQuery([string]$query) {
  $encoded = [uri]::EscapeDataString($query)
  try {
    return Invoke-RestMethod -Uri "http://127.0.0.1:9090/api/v1/query?query=$encoded" -TimeoutSec 15
  } catch {
    return [pscustomobject]@{ status = "unavailable"; error = $_.Exception.Message }
  }
}

function Save-Json($value, [string]$path) {
  $value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding utf8
}

function Save-KubernetesState([string]$path) {
  $state = [ordered]@{}
  $state.deployment = kubectl get deployment benchmark-app -n default -o json | ConvertFrom-Json
  $state.pods = kubectl get pods -n default -l app.kubernetes.io/name=benchmark-app -o json | ConvertFrom-Json
  $state.service = kubectl get service benchmark-app -n default -o json | ConvertFrom-Json
  $state.endpointslices = kubectl get endpointslices -n default -l kubernetes.io/service-name=benchmark-app -o json | ConvertFrom-Json
  Save-Json $state $path
}

function Invoke-LoadCheck([string]$outputPath) {
  $stderrPath = $outputPath + ".stderr"
  $process = Start-Process -FilePath $go -ArgumentList @("-C", (Join-Path $root "benchmark-app"), "run", "./cmd/loadcheck") -Wait -PassThru -NoNewWindow -RedirectStandardOutput $outputPath -RedirectStandardError $stderrPath
  return $process.ExitCode
}

if (!(Test-Path -LiteralPath $go)) { throw "Go executable not found at $go" }
if ((kubectl config current-context) -ne "kind-anfa-dev") { throw "Expected Kubernetes context kind-anfa-dev" }

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
Copy-Item -LiteralPath (Join-Path $root "step5\experiment-config.json") -Destination $runDir

try {
  kubectl scale deployment/benchmark-app --replicas=$Replicas -n default | Out-Null
  kubectl rollout status deployment/benchmark-app -n default --timeout=180s | Out-Null
  kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=benchmark-app -n default --timeout=120s | Out-Null
  $readyCount = [int](kubectl get pods -n default -l app.kubernetes.io/name=benchmark-app --field-selector=status.phase=Running -o jsonpath='{.items[*].status.containerStatuses[0].ready}' | Select-String -AllMatches 'true' | ForEach-Object { $_.Matches.Count })
  if ($readyCount -ne $Replicas) { throw "Expected $Replicas Ready benchmark Pods, found $readyCount" }

  kubectl get nodes -o json | Set-Content -LiteralPath (Join-Path $runDir "nodes-before.json") -Encoding utf8
  Save-KubernetesState (Join-Path $runDir "kubernetes-before.json")

  $prometheusJob = Start-Job -ScriptBlock { kubectl port-forward -n monitoring svc/anfa-monitoring-kube-prome-prometheus 9090:9090 }
  $deadline = (Get-Date).AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 500
    try { $ready = (Invoke-RestMethod -Uri "http://127.0.0.1:9090/-/ready" -TimeoutSec 2) } catch { $ready = $null }
  } until ($ready -or (Get-Date) -gt $deadline)

  if (!$SkipWarmup) {
    $env:TARGET_URL = "http://127.0.0.1:30080/work"
    $env:TARGET_RPS = "25"
    $env:DURATION_SECONDS = "60"
    [void](Invoke-LoadCheck (Join-Path $runDir "warmup.json"))
  }

  foreach ($rate in $Rates) {
    $pointDir = Join-Path $runDir ("rps-{0:D3}" -f $rate)
    New-Item -ItemType Directory -Force -Path $pointDir | Out-Null
    if ($PointWarmupSeconds -gt 0) {
      $env:TARGET_URL = "http://127.0.0.1:30080/work"
      $env:TARGET_RPS = $rate.ToString()
      $env:DURATION_SECONDS = $PointWarmupSeconds.ToString()
      [void](Invoke-LoadCheck (Join-Path $pointDir "point-warmup.json"))
    }
    $start = (Get-Date).ToUniversalTime()
    Save-KubernetesState (Join-Path $pointDir "kubernetes-before.json")

    $env:TARGET_URL = "http://127.0.0.1:30080/work"
    $env:TARGET_RPS = $rate.ToString()
    $env:DURATION_SECONDS = $DurationSeconds.ToString()
    $outputPath = Join-Path $pointDir "client-output.txt"
    $exitCode = Invoke-LoadCheck $outputPath
    $end = (Get-Date).ToUniversalTime()
    $raw = Get-Content -LiteralPath $outputPath
    $jsonLine = @($raw | Where-Object { $_ -match '^\{' })[0]
    if (!$jsonLine) { throw "No JSON result returned for $rate RPS" }
    $client = $jsonLine | ConvertFrom-Json
    Save-Json $client (Join-Path $pointDir "client-summary.json")

    $cpuQuery = 'sum(avg_over_time(rate(container_cpu_usage_seconds_total{namespace="default",container="benchmark-app"}[30s])[' + $DurationSeconds + 's:5s]))'
    $throttleQuery = 'sum(rate(container_cpu_cfs_throttled_periods_total{namespace="default",container="benchmark-app"}[' + $DurationSeconds + 's])) / sum(rate(container_cpu_cfs_periods_total{namespace="default",container="benchmark-app"}[' + $DurationSeconds + 's]))'
    $cpu = Invoke-PrometheusQuery $cpuQuery
    $throttle = Invoke-PrometheusQuery $throttleQuery
    $cpuByPodQuery = 'avg_over_time(rate(container_cpu_usage_seconds_total{namespace="default",container="benchmark-app"}[30s])[' + $DurationSeconds + 's:5s])'
    $throttledPeriods = 'sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="default",container="benchmark-app"}[' + $DurationSeconds + 's]))'
    $allPeriods = 'sum by (pod) (rate(container_cpu_cfs_periods_total{namespace="default",container="benchmark-app"}[' + $DurationSeconds + 's]))'
    $throttleByPodQuery = '((' + $throttledPeriods + ') or (0 * ' + $allPeriods + ')) / ' + $allPeriods
    $cpuByPod = Invoke-PrometheusQuery $cpuByPodQuery
    $throttleByPod = Invoke-PrometheusQuery $throttleByPodQuery
    Save-Json $cpu (Join-Path $pointDir "prometheus-cpu.json")
    Save-Json $throttle (Join-Path $pointDir "prometheus-throttling.json")
    Save-Json $cpuByPod (Join-Path $pointDir "prometheus-cpu-by-pod.json")
    Save-Json $throttleByPod (Join-Path $pointDir "prometheus-throttling-by-pod.json")
    Save-KubernetesState (Join-Path $pointDir "kubernetes-after.json")

    $summary += [pscustomobject]@{
      run_id = $runId; replicas = $Replicas; target_rps = $rate; start_utc = $start.ToString("o"); end_utc = $end.ToString("o")
      exit_code = $exitCode; completed = $client.completed; errors = $client.errors
      failure_rate = $client.failure_rate; completion_ratio = $client.completion_ratio
      achieved_rps = $client.measurement_throughput_rps; average_ms = $client.average_ms
      p50_ms = $client.p50_ms; p95_ms = $client.p95_ms; p99_ms = $client.p99_ms; max_ms = $client.max_ms
      serving_pods = (($client.serving_pods.psobject.Properties.Name | Sort-Object) -join ',')
      point_directory = $pointDir
    }
    $summary | Export-Csv -LiteralPath (Join-Path $runDir "summary.csv") -NoTypeInformation
    if ($RecoverySeconds -gt 0) { Start-Sleep -Seconds $RecoverySeconds }
  }

  Save-KubernetesState (Join-Path $runDir "kubernetes-after.json")
  Write-Output "Step 5 pilot complete: $runDir"
  $summary | Format-Table -AutoSize
} finally {
  if ($prometheusJob) { Stop-Job $prometheusJob -ErrorAction SilentlyContinue; Remove-Job $prometheusJob -Force -ErrorAction SilentlyContinue }
  Remove-Item Env:TARGET_URL,Env:TARGET_RPS,Env:DURATION_SECONDS -ErrorAction SilentlyContinue
}
