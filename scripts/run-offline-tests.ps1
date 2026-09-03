[CmdletBinding()]
param(
    [string]$Python = 'python',
    [switch]$RequireGo
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

function Invoke-PythonTests([string]$Label, [string]$Directory) {
    Write-Host "[$Label]"
    Push-Location $Directory
    try {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "$Label failed." }
    } finally {
        Pop-Location
    }
}

Invoke-PythonTests 'oracle tests' (Join-Path $repo 'forecasts\oracle')
Invoke-PythonTests 'mutation tests' (Join-Path $repo 'forecasts\mutations')
Invoke-PythonTests 'matching tests' (Join-Path $repo 'forecasts\matched')

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $repo 'monitoring\src'
try {
    Invoke-PythonTests 'observability tests' (Join-Path $repo 'monitoring')
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Host '[primary experiment tests]'
& $Python (Join-Path $repo 'experiments\primary\tests\test_offline.py')
if ($LASTEXITCODE -ne 0) { throw 'Primary experiment tests failed.' }
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $repo 'monitoring\src'
try {
    Invoke-PythonTests 'safety experiment tests' (Join-Path $repo 'experiments\safety')
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
Invoke-PythonTests 'processing tests' (Join-Path $repo 'processing')
Invoke-PythonTests 'statistical tests' (Join-Path $repo 'analysis')

& (Join-Path $PSScriptRoot 'verify-deterministic-inputs.ps1') -Python $Python
& (Join-Path $PSScriptRoot 'reproduce-figures.ps1') -Python $Python

$go = Get-Command go -ErrorAction SilentlyContinue
if ($go) {
    foreach ($directory in @('app', 'controller')) {
        Write-Host "[Go tests: $directory]"
        Push-Location (Join-Path $repo $directory)
        try {
            & go test ./... -count=1
            if ($LASTEXITCODE -ne 0) { throw "Go tests failed: $directory" }
        } finally {
            Pop-Location
        }
    }
} elseif ($RequireGo) {
    throw 'Go was required but is not available.'
} else {
    Write-Warning 'Go not found; Go tests were explicitly skipped. Use -RequireGo for release certification.'
}

Write-Host 'PASS: all available offline checks completed.'
