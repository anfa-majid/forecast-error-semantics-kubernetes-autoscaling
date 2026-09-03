[CmdletBinding()]
param([string]$Python='python')
$root=Split-Path -Parent $PSScriptRoot
& $Python (Join-Path $root 'tools\campaign.py') status
