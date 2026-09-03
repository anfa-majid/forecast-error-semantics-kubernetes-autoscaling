[CmdletBinding()]
param(
    [string]$Python = 'python',
    [switch]$RunOfflineTests,
    [switch]$RequireGo,
    [switch]$SkipKubernetesRender
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check([string]$Name, [bool]$Passed, [string]$Details) {
    $checks.Add([ordered]@{ name = $Name; passed = $Passed; details = $Details })
    if (-not $Passed) { throw "$Name failed: $Details" }
    Write-Host "PASS: $Name - $Details"
}

$required = @(
    'README.md', 'LICENSE', 'LICENSE-DATA', 'NOTICE', 'CITATION.cff',
    'requirements.txt', 'versions.lock.yml',
    'app/Dockerfile', 'controller/Dockerfile',
    'kubernetes/cluster/kind-config.yaml', 'scripts/run-example.ps1',
    'workloads/workloads/narrow-spike-v1.csv',
    'forecasts/oracle/policy-config.json',
    'forecasts/matched/accepted-pairs',
    'data/processed/run-level.csv',
    'analysis/tools/analyze_step18.py',
    'results/reference/statistical/output',
    'docs/REPRODUCTION.md', 'docs/DATA.md', 'docs/LIMITATIONS.md',
    'audit/live-example-validation.json'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $repo $_)) })
$details = if ($missing) { $missing -join ', ' } else { "$($required.Count) required paths present" }
Add-Check 'required-content' ($missing.Count -eq 0) $details

$tooLarge = @(Get-ChildItem -LiteralPath $repo -Recurse -File | Where-Object { $_.Length -gt 95MB })
$details = if ($tooLarge) { $tooLarge.FullName -join ', ' } else { 'no file exceeds 95 MiB' }
Add-Check 'hosted-file-size' ($tooLarge.Count -eq 0) $details

$textExtensions = @('.csv','.go','.json','.md','.ps1','.py','.tex','.txt','.yaml','.yml','.mod','.sum','.cff')
$sensitive = [regex]'(?i)([A-Za-z]:\\Users\\[^\\]+|F:\\|/home/[A-Za-z0-9._-]+|85\.211\.(196\.55|177\.42|178\.82)|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY)'
$hits = [System.Collections.Generic.List[string]]::new()
Get-ChildItem -LiteralPath $repo -Recurse -File | Where-Object { $textExtensions -contains $_.Extension.ToLowerInvariant() -and $_.FullName -ne $PSCommandPath } | ForEach-Object {
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $_.FullName) {
        $lineNumber++
        if ($sensitive.IsMatch($line)) {
            $relative = [IO.Path]::GetRelativePath($repo, $_.FullName)
            $hits.Add("${relative}:$lineNumber")
        }
    }
}
$details = if ($hits) { $hits -join ', ' } else { 'no private key, personal home path, original endpoint, or F-drive path found' }
Add-Check 'privacy-and-path-scan' ($hits.Count -eq 0) $details

$jsonFailures = [System.Collections.Generic.List[string]]::new()
Get-ChildItem -LiteralPath $repo -Recurse -File -Filter '*.json' | ForEach-Object {
    try { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json | Out-Null }
    catch { $jsonFailures.Add([IO.Path]::GetRelativePath($repo, $_.FullName)) }
}
$details = if ($jsonFailures) { $jsonFailures -join ', ' } else { 'all JSON files parse' }
Add-Check 'json-syntax' ($jsonFailures.Count -eq 0) $details

$psFailures = [System.Collections.Generic.List[string]]::new()
Get-ChildItem -LiteralPath $repo -Recurse -File -Filter '*.ps1' | ForEach-Object {
    $tokens = $null; $errors = $null
    [Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors) { $psFailures.Add([IO.Path]::GetRelativePath($repo, $_.FullName)) }
}
$details = if ($psFailures) { $psFailures -join ', ' } else { 'all PowerShell files parse' }
Add-Check 'powershell-syntax' ($psFailures.Count -eq 0) $details

$pythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { throw "Python executable not found: $Python" }
& $Python -m compileall -q -f $repo
Add-Check 'python-syntax' ($LASTEXITCODE -eq 0) 'all Python files compile'

$kubectl = Get-Command kubectl -ErrorAction SilentlyContinue
if ($SkipKubernetesRender) {
    Add-Check 'kubernetes-render' $true 'explicitly skipped; must be completed before release'
} elseif ($kubectl) {
    $kustomizations = @(Get-ChildItem -LiteralPath $repo -Recurse -File -Filter 'kustomization.yaml')
    foreach ($item in $kustomizations) {
        & kubectl kustomize $item.Directory.FullName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Kustomize render failed: $($item.Directory.FullName)" }
    }
    Add-Check 'kubernetes-render' $true "$($kustomizations.Count) kustomization(s) rendered"
} else {
    Add-Check 'kubernetes-render' $true 'kubectl unavailable; render check explicitly skipped'
}

& (Join-Path $PSScriptRoot 'verify-checksums.ps1')
Add-Check 'release-checksums' ($LASTEXITCODE -eq 0) 'release manifest verified'

if ($RunOfflineTests) {
    & (Join-Path $PSScriptRoot 'run-offline-tests.ps1') -Python $Python -RequireGo:$RequireGo
    Add-Check 'offline-reproduction' ($LASTEXITCODE -eq 0) 'unit tests, deterministic-input regeneration, and figure reproduction passed'
}

$report = [ordered]@{
    schema_version = '1.0.0'
    validated_utc = [DateTimeOffset]::UtcNow.ToString('o')
    repository = '.'
    offline_tests_requested = [bool]$RunOfflineTests
    go_required = [bool]$RequireGo
    kubernetes_render_skipped = [bool]$SkipKubernetesRender
    valid_for_requested_checks = -not ($checks | Where-Object { -not $_.passed })
    release_ready = (-not ($checks | Where-Object { -not $_.passed })) -and (-not $SkipKubernetesRender) -and $RunOfflineTests -and ((-not $RequireGo) -or [bool](Get-Command go -ErrorAction SilentlyContinue))
    checks = $checks
}
$reportPath = Join-Path $repo 'audit\verification-report.json'
New-Item -ItemType Directory -Path (Split-Path $reportPath -Parent) -Force | Out-Null
[IO.File]::WriteAllText(
    $reportPath,
    (($report | ConvertTo-Json -Depth 6) + [Environment]::NewLine),
    [Text.UTF8Encoding]::new($false)
)
Write-Host "PASS: artifact verification complete. Report: $reportPath"
