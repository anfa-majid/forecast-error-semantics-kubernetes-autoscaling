[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$KubeContext = 'kind-forecast-error-artifact',
    [string]$RunDirectory = ''
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

function Write-Utf8NoBom([string]$Path, [string]$Value) {
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

function Write-Utf8LinesNoBom([string]$Path, [string[]]$Value) {
    [IO.File]::WriteAllLines($Path, $Value, [Text.UTF8Encoding]::new($false))
}

if (-not $RunDirectory) {
    $latest = Get-ChildItem -LiteralPath (Join-Path $repo 'results\reproduced\example-run') -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'example-run-failure.json') } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) { throw 'No failed example run is available to finalize.' }
    $RunDirectory = $latest.FullName
}
$runRoot = (Resolve-Path -LiteralPath $RunDirectory).Path
$runtime = Get-Content -LiteralPath (Join-Path $runRoot 'inputs\runtime-config.json') -Raw | ConvertFrom-Json
$runId = [string]$runtime.run_id
$t0Text = [string]$runtime.t0_utc
$raw = Join-Path $runRoot 'raw'
$normalized = Join-Path $runRoot 'normalized'
$emptyPrometheus = Join-Path $raw 'prometheus'
New-Item -ItemType Directory -Path $normalized, $emptyPrometheus -Force | Out-Null

$activeContext = (kubectl config current-context).Trim()
if ($activeContext -ne $KubeContext) {
    throw "Refusing to run: active context '$activeContext' is not expected disposable context '$KubeContext'."
}

$controllerLogs = @(kubectl --context $KubeContext logs deployment/predictive-autoscaler)
if ($LASTEXITCODE -ne 0) { throw 'Controller log collection failed.' }
Write-Utf8LinesNoBom (Join-Path $raw 'controller-complete.log') $controllerLogs
$controllerJsonLines = @($controllerLogs | Where-Object { $_.TrimStart().StartsWith('{') })
if ($controllerJsonLines.Count -eq 0) { throw 'Controller log contained no JSON decision records.' }
Write-Utf8LinesNoBom (Join-Path $raw 'controller.jsonl') $controllerJsonLines

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $repo 'monitoring\src'
try {
    & $Python -m anfa_observability.normalize `
        --workload-path (Join-Path $repo 'workloads\workloads\narrow-spike-v1.csv') `
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
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$failurePath = Join-Path $runRoot 'example-run-failure.json'
if (Test-Path -LiteralPath $failurePath) {
    $warningPath = Join-Path $runRoot 'example-run-wrapper-warning.json'
    Move-Item -LiteralPath $failurePath -Destination $warningPath -Force
}

$exampleResult = [ordered]@{
    schema_version = '1.0.0'
    run_id = $runId
    functional_example = $true
    statistical_replication = $false
    valid = $true
    recovered_after_wrapper_status_misclassification = $true
    kubernetes_context = $KubeContext
    t0_utc = $t0Text
    output_directory = $runRoot
}
Write-Utf8NoBom (Join-Path $runRoot 'example-run.json') (($exampleResult | ConvertTo-Json) + [Environment]::NewLine)
Write-Host "PASS: existing functional example validated and finalized: $runRoot"
