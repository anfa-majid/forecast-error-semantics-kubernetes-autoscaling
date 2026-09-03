[CmdletBinding()]
param(
    [string]$Output = 'audit/release-checksums.sha256'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$outputPath = Join-Path $repo $Output
$excludedPrefixes = @('.git/', '.venv/', 'results/reproduced/', 'audit/release-checksums.sha256', 'audit/verification-report.json')

function Get-PortableSha256([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $bytesToHash = $bytes

    # Git may check valid UTF-8 text out with different line endings on
    # different platforms. Canonicalize only strict UTF-8 text; files with a
    # NUL byte or invalid UTF-8 remain binary and are hashed byte-for-byte.
    if (-not ($bytes -contains [byte]0)) {
        try {
            $strictUtf8 = [Text.UTF8Encoding]::new($false, $true)
            $text = $strictUtf8.GetString($bytes)
            $canonicalText = $text.Replace("`r`n", "`n").Replace("`r", "`n")
            $bytesToHash = [Text.UTF8Encoding]::new($false).GetBytes($canonicalText)
        }
        catch [Text.DecoderFallbackException] {
            $bytesToHash = $bytes
        }
    }

    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha256.ComputeHash($bytesToHash)
    }
    finally {
        $sha256.Dispose()
    }
    return [BitConverter]::ToString($digest).Replace('-', '').ToLowerInvariant()
}

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
            $hash = Get-PortableSha256 -Path $_.FullName
            "$hash  $relative"
        }
    } | Sort-Object

New-Item -ItemType Directory -Path (Split-Path $outputPath -Parent) -Force | Out-Null
[IO.File]::WriteAllLines($outputPath, $lines, [Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($lines.Count) SHA-256 entries to $outputPath"
