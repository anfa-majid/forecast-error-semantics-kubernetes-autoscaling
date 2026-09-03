[CmdletBinding()]
param([string]$Python = 'python')

$ErrorActionPreference = 'Stop'
$checks = [System.Collections.Generic.List[object]]::new()

function Add-CommandCheck([string]$Name, [string]$Command, [bool]$Required) {
    $found = Get-Command $Command -ErrorAction SilentlyContinue
    $checks.Add([pscustomobject]@{
        component = $Name
        required_for_analysis = $Required
        available = [bool]$found
        path = if ($found) { $found.Source } else { '' }
    })
}

Add-CommandCheck 'Python' $Python $true
Add-CommandCheck 'Git' 'git' $false
Add-CommandCheck 'Go' 'go' $false
Add-CommandCheck 'Docker' 'docker' $false
Add-CommandCheck 'kind' 'kind' $false
Add-CommandCheck 'kubectl' 'kubectl' $false
Add-CommandCheck 'Helm' 'helm' $false
Add-CommandCheck 'PowerShell' 'pwsh' $false

$checks | Format-Table -AutoSize

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python executable not found: $Python"
}

& $Python -c "import sys; print(sys.version); import numpy, pandas, PIL; print('numpy='+numpy.__version__); print('pandas='+pandas.__version__); print('Pillow='+PIL.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Pinned Python dependencies are unavailable.' }

Write-Host 'PASS: analysis environment is available. Optional live-tool status is shown above.'
