[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$KubeContext = 'kind-forecast-error-artifact',
    [int]$LeadSeconds = 30
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

function Write-Utf8NoBom([string]$Path, [string]$Value) {
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

function Write-Utf8LinesNoBom([string]$Path, [string[]]$Value) {
    [IO.File]::WriteAllLines($Path, $Value, [Text.UTF8Encoding]::new($false))
}

$activeContext = (kubectl config current-context).Trim()
if ($activeContext -ne $KubeContext) {
    throw "Refusing to run: active context '$activeContext' is not expected disposable context '$KubeContext'."
}

$runId = 'example-' + [DateTimeOffset]::UtcNow.ToString('yyyyMMdd-HHmmss')
$runRoot = Join-Path $repo "results\reproduced\example-run\$runId"
$inputs = Join-Path $runRoot 'inputs'
$raw = Join-Path $runRoot 'raw'
$normalized = Join-Path $runRoot 'normalized'
$emptyPrometheus = Join-Path $raw 'prometheus'
New-Item -ItemType Directory -Path $inputs, $raw, $normalized, $emptyPrometheus -Force | Out-Null

$workload = Join-Path $repo 'workloads\workloads\narrow-spike-v1.csv'
$schedule = Join-Path $repo 'workloads\request-schedules\narrow-spike-v1.requests.csv'
$forecast = Join-Path $repo 'controller\testdata\forecasts\narrow-spike-v1.oracle-forecast.csv'
$t0 = [DateTimeOffset]::UtcNow.AddSeconds($LeadSeconds)
$t0Text = $t0.ToString('yyyy-MM-ddTHH:mm:ss.fffZ')

$runtime = [ordered]@{
    experiment_id = 'artifact-functional-example'
    run_id = $runId
    controller_id = 'predictive-autoscaler-v1.1.2'
    trace_id = 'narrow-spike-v1'
    condition = 'oracle'
    namespace = 'default'
    deployment = 'benchmark-app'
    forecast_path = '/etc/anfa/forecast/forecast.csv'
    policy_path = '/etc/anfa/policy/policy-config.json'
    t0_utc = $t0Text
    health_address = ':8081'
    safety_enabled = $false
    safety_policy_path = '/etc/anfa/safety/safety-policy.json'
}
$runtimePath = Join-Path $inputs 'runtime-config.json'
Write-Utf8NoBom $runtimePath (($runtime | ConvertTo-Json) + [Environment]::NewLine)
Copy-Item -LiteralPath $workload, $schedule, $forecast -Destination $inputs

kubectl --context $KubeContext scale deployment/benchmark-app --replicas=1
kubectl --context $KubeContext rollout status deployment/benchmark-app --timeout=120s

$runtimeManifest = Join-Path $inputs 'runtime-configmap.yaml'
$runtimeYaml = @(kubectl --context $KubeContext create configmap anfa-autoscaler-runtime-current `
    --from-file="runtime-config.json=$runtimePath" --dry-run=client -o yaml)
if ($LASTEXITCODE -ne 0) { throw 'Runtime ConfigMap rendering failed.' }
Write-Utf8LinesNoBom $runtimeManifest $runtimeYaml
kubectl --context $KubeContext apply -f $runtimeManifest
if ($LASTEXITCODE -ne 0) { throw 'Runtime ConfigMap apply failed.' }

$forecastManifest = Join-Path $inputs 'forecast-configmap.yaml'
$forecastYaml = @(kubectl --context $KubeContext create configmap anfa-forecast-current `
    --from-file="forecast.csv=$forecast" --dry-run=client -o yaml)
if ($LASTEXITCODE -ne 0) { throw 'Forecast ConfigMap rendering failed.' }
Write-Utf8LinesNoBom $forecastManifest $forecastYaml
kubectl --context $KubeContext apply -f $forecastManifest
if ($LASTEXITCODE -ne 0) { throw 'Forecast ConfigMap apply failed.' }
kubectl --context $KubeContext delete deployment predictive-autoscaler --ignore-not-found --wait=true
if ($LASTEXITCODE -ne 0) { throw 'Previous controller cleanup failed.' }
kubectl --context $KubeContext apply -k (Join-Path $repo 'kubernetes\controller')
kubectl --context $KubeContext rollout status deployment/predictive-autoscaler --timeout=120s

$portForwardOut = Join-Path $raw 'port-forward.out'
$portForwardErr = Join-Path $raw 'port-forward.err'
$portForward = Start-Process kubectl -ArgumentList @('--context', $KubeContext, 'port-forward', 'service/benchmark-app', '18080:8080') `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput $portForwardOut -RedirectStandardError $portForwardErr
$collector = $null
$collectorExitCode = $null

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $repo 'monitoring\src'
try {
    $ready = $false
    foreach ($attempt in 1..20) {
        try {
            Invoke-WebRequest 'http://127.0.0.1:18080/readyz' -UseBasicParsing -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) { throw 'Benchmark port-forward did not become ready.' }

    $collectorOut = Join-Path $raw 'kubernetes-collector.out'
    $collectorErr = Join-Path $raw 'kubernetes-collector.err'
    $collectorDuration = $LeadSeconds + 190
    $collector = Start-Process $Python -ArgumentList @(
        '-m', 'anfa_observability.kubernetes',
        '--output', (Join-Path $raw 'kubernetes-snapshots.jsonl'),
        '--run-id', $runId,
        '--duration-seconds', [string]$collectorDuration,
        '--interval-ms', '1000'
    ) -WindowStyle Hidden -PassThru -RedirectStandardOutput $collectorOut -RedirectStandardError $collectorErr

    $loadgenOut = Join-Path $raw 'load-generator.out'
    $loadgenErr = Join-Path $raw 'load-generator.err'
    & $Python -m anfa_observability.loadgen `
        --schedule $schedule `
        --output (Join-Path $raw 'load-generator-requests.jsonl') `
        --target-url 'http://127.0.0.1:18080/work' `
        --t0-utc $t0Text `
        --experiment-id 'artifact-functional-example' `
        --run-id $runId `
        --workload-id 'narrow-spike-v1' `
        --forecast-condition 'oracle' `
        1> $loadgenOut 2> $loadgenErr
    if ($LASTEXITCODE -ne 0) { throw 'Load generation failed.' }

    $collector.WaitForExit()
    $collector.Refresh()
    $collectorExitCode = $collector.ExitCode

    # The bundled Python launcher can report a nonzero wrapper status under
    # Windows PowerShell 5.1 even when the child collector completed cleanly.
    # Treat the emitted evidence as authoritative and validate it below.
    $snapshotPath = Join-Path $raw 'kubernetes-snapshots.jsonl'
    $snapshotLines = @(Get-Content -LiteralPath $snapshotPath)
    $snapshotErrors = @($snapshotLines | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object { $_.collection_error })
    if ($snapshotLines.Count -lt $collectorDuration -or $snapshotErrors.Count -ne 0) {
        throw "Kubernetes collection evidence is incomplete (exit=$collectorExitCode, snapshots=$($snapshotLines.Count), errors=$($snapshotErrors.Count))."
    }
    if ($null -ne $collectorExitCode -and $collectorExitCode -ne 0) {
        Write-Warning "Collector wrapper returned exit code $collectorExitCode; complete error-free snapshot evidence will be validated."
    }

    $controllerLogs = @(kubectl --context $KubeContext logs deployment/predictive-autoscaler)
    if ($LASTEXITCODE -ne 0) { throw 'Controller log collection failed.' }
    Write-Utf8LinesNoBom (Join-Path $raw 'controller-complete.log') $controllerLogs
    $controllerJsonLines = @($controllerLogs | Where-Object { $_.TrimStart().StartsWith('{') })
    if ($controllerJsonLines.Count -eq 0) { throw 'Controller log contained no JSON decision records.' }
    Write-Utf8LinesNoBom (Join-Path $raw 'controller.jsonl') $controllerJsonLines

    & $Python -m anfa_observability.normalize `
        --workload-path $workload `
        --requests-path (Join-Path $raw 'load-generator-requests.jsonl') `
        --controller-path (Join-Path $raw 'controller.jsonl') `
        --kubernetes-path (Join-Path $raw 'kubernetes-snapshots.jsonl') `
        --prometheus-directory $emptyPrometheus `
        --t0-utc $t0Text `
        --duration-seconds 180 `
        --output-path (Join-Path $normalized 'joined-timeline.csv')
    if ($LASTEXITCODE -ne 0) { throw 'Timeline normalization failed.' }

    $validationPath = Join-Path $runRoot 'example-run-validation.json'
    & $Python (Join-Path $repo 'scripts\validate-example.py') `
        --run-directory $runRoot `
        --run-id $runId `
        --duration-seconds 180 `
        --expected-requests 5550 `
        --output $validationPath
    if ($LASTEXITCODE -ne 0) { throw 'Functional-example evidence validation failed.' }
} catch {
    $failure = [ordered]@{
        schema_version = '1.0.0'
        run_id = $runId
        functional_example = $true
        valid = $false
        failed_utc = [DateTimeOffset]::UtcNow.ToString('o')
        reason = $_.Exception.Message
    }
    Write-Utf8NoBom (Join-Path $runRoot 'example-run-failure.json') (($failure | ConvertTo-Json) + [Environment]::NewLine)
    throw
} finally {
    $env:PYTHONPATH = $previousPythonPath
    if ($collector -and -not $collector.HasExited) {
        Stop-Process -Id $collector.Id -Force
        $collector.WaitForExit()
    }
    if ($portForward -and -not $portForward.HasExited) { Stop-Process -Id $portForward.Id -Force }
}

$exampleResult = [ordered]@{
    schema_version = '1.0.0'
    run_id = $runId
    functional_example = $true
    statistical_replication = $false
    valid = $true
    collector_process_exit_code = $collectorExitCode
    kubernetes_context = $KubeContext
    t0_utc = $t0Text
    output_directory = $runRoot
}
Write-Utf8NoBom (Join-Path $runRoot 'example-run.json') (($exampleResult | ConvertTo-Json) + [Environment]::NewLine)

Write-Host "PASS: functional example completed: $runRoot"
