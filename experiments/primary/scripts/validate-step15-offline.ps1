[CmdletBinding()]
param([string]$Python='python')
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot
& $Python (Join-Path $root 'tools\validate_framework.py');if($LASTEXITCODE-ne0){throw 'Step 15 framework validation failed'}
& $Python (Join-Path $root 'tests\test_offline.py');if($LASTEXITCODE-ne0){throw 'Step 15 offline tests failed'}
& $Python (Join-Path $root 'tools\campaign.py') status
