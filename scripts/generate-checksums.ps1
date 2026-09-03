[CmdletBinding()]
param(
    [string]$Output = 'audit/release-checksums.sha256'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$outputPath = Join-Path $repo $Output
$excludedPrefixes = @('.git/', '.venv/', 'results/reproduced/', 'audit/release-checksums.sha256', 'audit/verification-report.json')

$lines = Get-ChildItem -LiteralPath $repo -Recurse -File |
    ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($repo, $_.FullName).Replace('\', '/')
        $excluded = $false
        foreach ($prefix in $excludedPrefixes) {
            if ($relative.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                $excluded = $true
                break
            }
        }
        if ($relative -match '(^|/)__pycache__/' -or $relative -match '\.py[co]$') { $excluded = $true }
        if (-not $excluded) {
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$hash  $relative"
        }
    } | Sort-Object

New-Item -ItemType Directory -Path (Split-Path $outputPath -Parent) -Force | Out-Null
[IO.File]::WriteAllLines($outputPath, $lines, [Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($lines.Count) SHA-256 entries to $outputPath"
