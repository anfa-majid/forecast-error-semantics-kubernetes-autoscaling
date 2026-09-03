[CmdletBinding()]
param([string]$Python = 'python')

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

function Invoke-Checked([string]$Label, [scriptblock]$Command) {
    Write-Host "[$Label]"
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Label failed." }
}

Invoke-Checked 'workload suite' {
    & $Python (Join-Path $repo 'workloads\tools\validate_workload_suite.py')
}

Invoke-Checked 'oracle policy and timelines' {
    & $Python (Join-Path $repo 'forecasts\oracle\tools\validate_oracle.py')
}

Invoke-Checked 'forecast mutations' {
    & $Python (Join-Path $repo 'forecasts\mutations\tools\validate_mutations.py') `
        --root (Join-Path $repo 'forecasts\mutations') `
        --step7-root (Join-Path $repo 'workloads') `
        --step8-root (Join-Path $repo 'forecasts\oracle') `
        --policy (Join-Path $repo 'forecasts\oracle\policy-config.json') `
        --catalog (Join-Path $repo 'forecasts\mutations\configuration\mutation-catalog.json')
}

Invoke-Checked 'accuracy-matched forecast pairs' {
    & $Python (Join-Path $repo 'forecasts\matched\tools\validate_dataset.py') `
        --root (Join-Path $repo 'forecasts\matched') `
        --step7-root (Join-Path $repo 'workloads') `
        --step8-policy (Join-Path $repo 'forecasts\oracle\policy-config.json') `
        --step11-root (Join-Path $repo 'forecasts\mutations')
}

Write-Host 'PASS: deterministic input packages validated.'
