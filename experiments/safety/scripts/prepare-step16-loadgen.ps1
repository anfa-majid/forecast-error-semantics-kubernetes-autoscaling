[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$ServerIp,
 [string]$SshUser='researcher',
 [string]$SshKeyPath="$env:USERPROFILE\.ssh\id_ed25519",
 [string]$RemoteRoot='/tmp/forecast-error-step16-v1.0.0'
)
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot;$repositoryRoot=Split-Path -Parent (Split-Path -Parent $root);$step10=Join-Path $repositoryRoot 'monitoring';$overlay=Join-Path $step10 'src\anfa_observability'
function Check([string]$message){if($LASTEXITCODE-ne0){throw $message}}
if(-not(Test-Path (Join-Path $step10 'src\anfa_observability'))){throw 'Step 10 collector source is missing'}
if(-not(Test-Path (Join-Path $overlay 'safety_observer.py'))){throw 'Step 16 safety load-generator overlay is missing'}
& ssh -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$ServerIp" "rm -rf '$RemoteRoot/staging/step16-loadgen'; mkdir -p '$RemoteRoot/staging/step16-loadgen' '$RemoteRoot/runs' '$RemoteRoot/bin'";Check 'remote staging initialization failed'
& scp -q -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath -r (Join-Path $step10 'src\anfa_observability') "${SshUser}@${ServerIp}:$RemoteRoot/staging/step16-loadgen/";Check 'base collector upload failed'
$overlayFiles=@(Get-ChildItem -LiteralPath $overlay -Filter '*.py'|ForEach-Object{$_.FullName})
& scp -q -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath @overlayFiles "${SshUser}@${ServerIp}:$RemoteRoot/staging/step16-loadgen/anfa_observability/";Check 'safety overlay upload failed'
& ssh -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$ServerIp" "PYTHONPATH='$RemoteRoot/staging/step16-loadgen' /usr/bin/python3 -m anfa_observability.loadgen --help >/dev/null; PYTHONPATH='$RemoteRoot/staging/step16-loadgen' /usr/bin/python3 -m anfa_observability.kubernetes --help >/dev/null";Check 'remote Step 16 load-generator self-test failed'
Write-Host 'STEP 16 LOAD-GENERATOR STAGING PASSED'
