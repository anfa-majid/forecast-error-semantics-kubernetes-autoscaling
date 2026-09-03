[CmdletBinding()]
param([string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
& $Python (Join-Path $root 'tools\finalize_campaign.py') --write-manifest
if($LASTEXITCODE-ne 0){throw 'Step 15 final campaign audit failed'}
