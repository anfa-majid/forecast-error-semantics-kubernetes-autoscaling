[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$ServerIp,
 [Parameter(Mandatory)][string]$Worker1Ip,
 [Parameter(Mandatory)][string]$Worker2Ip,
 [string]$SshUser='researcher',
 [string]$ServerHostName='control-plane',
 [string]$Worker1HostName='worker-1',
 [string]$Worker2HostName='worker-2',
 [string]$SshKeyPath="$env:USERPROFILE\.ssh\id_ed25519",
 [string]$Kubeconfig="$env:USERPROFILE\.kube\config",
 [string]$ExpectedContext='research-cluster'
)
$ErrorActionPreference='Stop';$root=Split-Path -Parent $PSScriptRoot
$protocol=Get-Content (Join-Path $root 'configuration\execution-protocol.json') -Raw|ConvertFrom-Json
$stamp=[DateTimeOffset]::UtcNow.ToString('yyyyMMdd-HHmmss');$evidence=Join-Path $root "validation\cloud-preflight-$stamp"
New-Item -ItemType Directory -Force $evidence|Out-Null
function CheckExit([string]$m){if($LASTEXITCODE-ne0){throw $m}}
try{
 $context=(& kubectl --kubeconfig $Kubeconfig config current-context).Trim();CheckExit 'cannot read context';if($context-ne$ExpectedContext){throw "wrong context: $context"}
 & kubectl --kubeconfig $Kubeconfig get nodes -o json|Out-File (Join-Path $evidence 'nodes.json') -Encoding utf8;CheckExit 'node query failed'
 $nodes=Get-Content (Join-Path $evidence 'nodes.json') -Raw|ConvertFrom-Json
 $notReady=@($nodes.items|Where-Object{-not@($_.status.conditions|Where-Object{$_.type-eq'Ready'-and$_.status-eq'True'}).Count})
 if($nodes.items.Count-ne3-or$notReady.Count){throw "expected three Ready nodes; count=$($nodes.items.Count), notReady=$($notReady.Count)"}
 $versions=@($nodes.items.status.nodeInfo.kubeletVersion|Sort-Object -Unique);if($versions.Count-ne1-or$versions[0]-ne$protocol.fixed_system.cluster.kubernetes_version){throw "cluster version mismatch: $versions"}
 $app=& kubectl --kubeconfig $Kubeconfig -n default get deployment benchmark-app -o json|ConvertFrom-Json;CheckExit 'application query failed'
 if($app.spec.template.spec.containers[0].image-ne$protocol.fixed_system.application_image){throw "application image mismatch: $($app.spec.template.spec.containers[0].image)"}
 if($app.spec.replicas-ne1-or$app.status.readyReplicas-ne1){throw 'application is not exactly 1/1 Ready'}
 $hpas=(& kubectl --kubeconfig $Kubeconfig -n default get hpa -o json|ConvertFrom-Json).items;CheckExit 'HPA query failed'
 if(@($hpas|Where-Object{$_.spec.scaleTargetRef.name-eq'benchmark-app'}).Count){throw 'competing HPA found'}
 $controller=(& kubectl --kubeconfig $Kubeconfig -n default get deployment predictive-autoscaler --ignore-not-found -o name);CheckExit 'controller query failed';if(-not[string]::IsNullOrWhiteSpace(($controller-join''))){throw 'stale predictive controller found'}
 $hosts=[ordered]@{$ServerHostName=$ServerIp;$Worker1HostName=$Worker1Ip;$Worker2HostName=$Worker2Ip};$clocks=@()
 foreach($entry in $hosts.GetEnumerator()){$raw=@(& ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$($entry.Value)" 'hostname; date -u +%Y-%m-%dT%H:%M:%S.%3NZ; timedatectl show -p NTPSynchronized --value');CheckExit "clock SSH failed: $($entry.Key)";$clocks+=[pscustomobject]@{expected=$entry.Key;reported=$raw[0].Trim();utc=$raw[1].Trim();ntp=$raw[2].Trim()}}
 $clocks|ConvertTo-Json|Set-Content (Join-Path $evidence 'node-clocks.json') -Encoding utf8
 if(@($clocks|Where-Object{$_.expected-ne$_.reported-or$_.ntp-ne'yes'}).Count){throw 'node identity/NTP check failed'}
 $images=@(& ssh -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$ServerIp" "sudo k3s ctr images list | grep 'predictive-autoscaler' || true");CheckExit 'controller image SSH failed';$images|Set-Content (Join-Path $evidence 'controller-images.txt') -Encoding utf8
 $imageText=$images-join' ';if($imageText-notmatch'predictive-autoscaler:1.0.0'-or$imageText-notmatch'98dd73b9d092f4dc19f685318b7fb3a92cdb7dcda29f0e587f22d1cb83f4662b'){throw 'frozen controller image/manifest absent'}
 [ordered]@{schema_version='1.0.0';passed=$true;checked_utc=[DateTimeOffset]::UtcNow.ToString('o');context=$context;node_count=3;all_nodes_ready=$true;all_nodes_ntp=$true;kubernetes_version=$versions[0];application_image=$app.spec.template.spec.containers[0].image;application_ready='1/1';competing_hpa_count=0;controller_absent=$true;controller_manifest_present=$true;final_runs_claimed=0;evidence_directory=$evidence}|ConvertTo-Json|Set-Content (Join-Path $evidence 'preflight-result.json') -Encoding utf8
 Write-Host 'STEP 15 AZURE IDENTITY PREFLIGHT PASSED';Write-Host "Evidence: $evidence"
}catch{[ordered]@{passed=$false;failed_utc=[DateTimeOffset]::UtcNow.ToString('o');error=$_.Exception.Message}|ConvertTo-Json|Set-Content (Join-Path $evidence 'preflight-failure.json') -Encoding utf8;Write-Host "Preflight failed. Evidence: $evidence";throw}
