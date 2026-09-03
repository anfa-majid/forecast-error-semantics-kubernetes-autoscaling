[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repo 'results\reproduced\step18'
}
$analysisOutput = Join-Path $OutputDirectory 'output'
$figureOutput = Join-Path $OutputDirectory 'figures'
$reference = Join-Path $repo 'results\reference\statistical'

New-Item -ItemType Directory -Path $analysisOutput, $figureOutput -Force | Out-Null

& $Python (Join-Path $repo 'analysis\tools\analyze_step18.py') `
    --run-level (Join-Path $repo 'data\processed\run-level.csv') `
    --output-directory $analysisOutput
if ($LASTEXITCODE -ne 0) { throw 'Statistical analysis failed.' }

& $Python (Join-Path $repo 'analysis\tools\create_step18_figures.py') `
    --analysis-directory $analysisOutput `
    --output-directory $figureOutput
if ($LASTEXITCODE -ne 0) { throw 'Figure generation failed.' }

& $Python (Join-Path $repo 'analysis\tools\validate_step18.py') `
    --dataset-directory $analysisOutput `
    --figures-directory $figureOutput
if ($LASTEXITCODE -ne 0) { throw 'Step 18 validation failed.' }

$relativeFiles = @(
    'output\paired-comparisons.csv',
    'output\condition-descriptives.csv',
    'output\individual-run-points.csv',
    'output\interaction-contrasts.csv',
    'output\ranking-agreement.csv',
    'output\condition-rankings.csv',
    'figures\figure-01-primary-effect-forest.svg',
    'figures\figure-02-safety-paired-runs.svg',
    'figures\figure-03-ranking-spearman.svg',
    'figures\figure-04-ranking-disagreement.svg',
    'figures\figure-05-harm-versus-cost.svg',
    'figures\figure-06-primary-slo-paired-runs.svg'
)

$comparisons = foreach ($relative in $relativeFiles) {
    $expectedPath = Join-Path $reference $relative
    $actualPath = Join-Path $OutputDirectory $relative
    if (-not (Test-Path -LiteralPath $expectedPath)) {
        throw "Reference artifact is missing: $relative"
    }
    if (-not (Test-Path -LiteralPath $actualPath)) {
        throw "Reproduced artifact is missing: $relative"
    }
    $expected = (Get-FileHash -Algorithm SHA256 -LiteralPath $expectedPath).Hash
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $actualPath).Hash
    [pscustomobject]@{
        file = $relative.Replace('\', '/')
        identical = ($expected -eq $actual)
        sha256 = $actual.ToLowerInvariant()
    }
}

$failed = @($comparisons | Where-Object { -not $_.identical })
$record = [ordered]@{
    schema_version = '1.0.0'
    valid = ($failed.Count -eq 0)
    compared_files = $comparisons.Count
    identical_files = $comparisons.Count - $failed.Count
    comparisons = $comparisons
}
$recordPath = Join-Path $OutputDirectory 'reproduction-validation.json'
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8NoBOM

if ($failed) {
    $failed | Format-Table -AutoSize
    throw "$($failed.Count) reproduced artifacts differ from their references."
}

Write-Host "PASS: $($comparisons.Count)/$($comparisons.Count) byte-identical reference artifacts."
Write-Host "Output: $OutputDirectory"
