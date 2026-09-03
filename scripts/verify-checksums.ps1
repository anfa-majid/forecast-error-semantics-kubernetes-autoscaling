[CmdletBinding()]
param(
    [string]$Manifest = 'audit/release-checksums.sha256'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$manifestPath = Join-Path $repo $Manifest
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Checksum manifest not found: $manifestPath"
}

function Get-PortableSha256([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $bytesToHash = $bytes

    # Keep release verification invariant across Git's CRLF/LF checkout
    # behavior while retaining byte-exact verification for binary artifacts.
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

$checked = 0
foreach ($line in Get-Content -LiteralPath $manifestPath) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -notmatch '^([0-9a-fA-F]{64})  (.+)$') { throw "Malformed checksum line: $line" }
    $expected = $Matches[1].ToLowerInvariant()
    $relative = $Matches[2]
    $path = Join-Path $repo ($relative.Replace('/', [IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing release file: $relative" }
    $actual = Get-PortableSha256 -Path $path
    if ($actual -ne $expected) { throw "Checksum mismatch: $relative" }
    $checked++
}

Write-Host "PASS: verified $checked release-file checksums."
