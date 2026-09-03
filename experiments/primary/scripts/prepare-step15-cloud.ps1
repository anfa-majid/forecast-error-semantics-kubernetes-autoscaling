[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$ServerIp,
 [string]$SshUser='researcher',
 [string]$SshKeyPath="$env:USERPROFILE\.ssh\id_ed25519",
 [string]$Kubeconfig="$env:USERPROFILE\.kube\config",
 [string]$RemoteRoot='/tmp/forecast-error-step15-v1.0.0'
)
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot;$repositoryRoot=Split-Path -Parent (Split-Path -Parent $root);$step10=Join-Path $repositoryRoot 'monitoring'
$stamp=[DateTimeOffset]::UtcNow.ToString('yyyyMMdd-HHmmss');$evidence=Join-Path $root "validation\cloud-stage-$stamp"
New-Item -ItemType Directory -Force $evidence|Out-Null
function Check([string]$m){if($LASTEXITCODE-ne0){throw $m}}
try{
 if(-not(Test-Path (Join-Path $step10 'src\anfa_observability'))){throw 'Monitoring collector source missing from repository'}
 & ssh -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$ServerIp" "rm -rf '$RemoteRoot/staging'; mkdir -p '$RemoteRoot/staging/step10-src' '$RemoteRoot/runs' '$RemoteRoot/bin'";Check 'remote staging initialization failed'
 & scp -q -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath -r (Join-Path $step10 'src\anfa_observability') "${SshUser}@${ServerIp}:$RemoteRoot/staging/step10-src/";Check 'collector upload failed'
 $wrapper=Join-Path $env:TEMP "step15-kubectl-$stamp";[IO.File]::WriteAllText($wrapper,"#!/usr/bin/env bash`nexec sudo k3s kubectl `"`$@`"`n",[Text.UTF8Encoding]::new($false))
 & scp -q -o BatchMode=yes -i $SshKeyPath $wrapper "${SshUser}@${ServerIp}:$RemoteRoot/bin/kubectl";Check 'kubectl wrapper upload failed';Remove-Item $wrapper -Force
 & ssh -o BatchMode=yes -i $SshKeyPath "${SshUser}@$ServerIp" "chmod 0755 '$RemoteRoot/bin/kubectl'; PATH='$RemoteRoot/bin:/usr/bin:/bin' PYTHONPATH='$RemoteRoot/staging/step10-src' /usr/bin/python3 -m anfa_observability.loadgen --help >/dev/null; PATH='$RemoteRoot/bin:/usr/bin:/bin' PYTHONPATH='$RemoteRoot/staging/step10-src' /usr/bin/python3 -m anfa_observability.kubernetes --help >/dev/null";Check 'remote collector self-test failed'
 $pf=Start-Process kubectl -ArgumentList @('--kubeconfig',$Kubeconfig,'port-forward','-n','monitoring','svc/anfa-monitoring-kube-prome-prometheus','9090:9090') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $evidence 'prometheus.out') -RedirectStandardError (Join-Path $evidence 'prometheus.err')
 try{$ready=$false;foreach($i in 1..20){try{Invoke-RestMethod 'http://127.0.0.1:9090/-/ready' -TimeoutSec 3|Out-Null;$ready=$true;break}catch{Start-Sleep 1}};if(-not$ready){throw 'Prometheus readiness failed'}}finally{if($pf-and-not$pf.HasExited){Stop-Process $pf.Id -Force}}
 [ordered]@{schema_version='1.0.0';passed=$true;staged_utc=[DateTimeOffset]::UtcNow.ToString('o');remote_root=$RemoteRoot;collectors_tested=$true;prometheus_ready=$true}|ConvertTo-Json|Set-Content (Join-Path $evidence 'stage-result.json') -Encoding utf8
 Write-Host 'STEP 15 AZURE STAGING PASSED';Write-Host "Evidence: $evidence"
}catch{[ordered]@{passed=$false;error=$_.Exception.Message}|ConvertTo-Json|Set-Content (Join-Path $evidence 'stage-failure.json') -Encoding utf8;Write-Host "Staging failed. Evidence: $evidence";throw}
