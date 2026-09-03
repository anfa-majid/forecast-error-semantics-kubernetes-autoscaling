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
 $expectedImage=[string]$protocol.fixed_system.controller_image;$expectedManifest=($expectedImage-split'@sha256:')[1];$images=@()
 foreach($entry in $hosts.GetEnumerator()){
   $raw=@(& ssh -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath "${SshUser}@$($entry.Value)" "sudo k3s ctr images list | grep 'predictive-autoscaler:1.1.2' || true");CheckExit "controller image SSH failed: $($entry.Key)"
   $text=$raw-join' ';if($text-notmatch[regex]::Escape($expectedManifest)){throw "frozen Step 16 controller manifest absent on $($entry.Key)"}
   $images+=[pscustomobject]@{node=$entry.Key;listing=$text}
 }
 $images|ConvertTo-Json|Set-Content (Join-Path $evidence 'controller-images.json') -Encoding utf8
 [ordered]@{schema_version='1.0.0';protocol_id=$protocol.protocol_id;passed=$true;checked_utc=[DateTimeOffset]::UtcNow.ToString('o');context=$context;node_count=3;all_nodes_ready=$true;all_nodes_ntp=$true;kubernetes_version=$versions[0];application_image=$app.spec.template.spec.containers[0].image;application_ready='1/1';competing_hpa_count=0;controller_absent=$true;controller_image=$expectedImage;controller_manifest_present_on_all_nodes=$true;safety_runs_claimed=0;evidence_directory=$evidence}|ConvertTo-Json|Set-Content (Join-Path $evidence 'preflight-result.json') -Encoding utf8
 Write-Host 'STEP 16 AZURE IDENTITY PREFLIGHT PASSED';Write-Host "Evidence: $evidence"
}catch{[ordered]@{passed=$false;failed_utc=[DateTimeOffset]::UtcNow.ToString('o');error=$_.Exception.Message}|ConvertTo-Json|Set-Content (Join-Path $evidence 'preflight-failure.json') -Encoding utf8;Write-Host "Preflight failed. Evidence: $evidence";throw}
