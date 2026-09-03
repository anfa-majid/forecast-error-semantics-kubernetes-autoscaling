param(
  [int]$Repetition = 1,
  [int]$PollMilliseconds = 100,
  [int]$TimeoutSeconds = 180,
  [int]$RecoverySeconds = 15
)

$ErrorActionPreference="Stop"
$root=Split-Path -Parent $PSScriptRoot
$namespace="default"
$deployment="benchmark-app-cold"
$selector="app.kubernetes.io/name=benchmark-app,anfa.dev/cache-treatment=cold"
$targetUrl="http://127.0.0.1:30080/work"
$worker="anfa-dev-worker"
$runId="cold-registry-0to1-rep{0:D2}-{1}" -f $Repetition,(Get-Date -Format "yyyyMMdd-HHmmss")
$runDir=Join-Path $root "step6\runs\$runId"

function UtcNow{(Get-Date).ToUniversalTime().ToString("o")}
function Save-Json($v,[string]$p){$v|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $p -Encoding utf8}
function Get-ColdPods{kubectl get pods -n $namespace -l $selector -o json|ConvertFrom-Json}
function ConditionTime($pod,[string]$type){$c=@($pod.status.conditions|Where-Object{$_.type -eq $type -and $_.status -eq "True"})|Select-Object -First 1;if($c){$c.lastTransitionTime}else{$null}}
function StartedTime($pod){$c=@($pod.status.containerStatuses|Where-Object{$_.name -eq "benchmark-app"})|Select-Object -First 1;if($c -and $c.state.running){$c.state.running.startedAt}else{$null}}

New-Item -ItemType Directory -Force -Path $runDir|Out-Null
curl.exe --fail --silent --output NUL --max-time 5 "http://127.0.0.1:30080/livez"
if($LASTEXITCODE -ne 0){throw "NodePort bridge unavailable"}
kubectl scale deployment/$deployment -n $namespace --replicas=0|Out-Null
$deadline=(Get-Date).AddSeconds(120)
do{$existing=(Get-ColdPods).items.Count;if($existing -eq 0){break};Start-Sleep -Milliseconds 250}until((Get-Date)-ge $deadline)
if($existing -ne 0){throw "Cold treatment Pod did not terminate"}

# Remove only benchmark-image references/content from the idle treatment worker.
# crictl's positional image argument is not a filter in this version, so inspect
# its JSON output instead of risking removal of unrelated images.
$imageState=docker exec $worker crictl images -o json|ConvertFrom-Json
$ids=@($imageState.images|Where-Object{(@($_.repoTags)+@($_.repoDigests)) -match 'anfa/benchmark-app|anfa-step6-registry'}|ForEach-Object{$_.id})|Sort-Object -Unique
foreach($id in $ids){docker exec $worker crictl rmi $id|Out-Null}
$imageState=docker exec $worker crictl images -o json|ConvertFrom-Json
$remaining=@($imageState.images|Where-Object{(@($_.repoTags)+@($_.repoDigests)) -match 'anfa/benchmark-app|anfa-step6-registry'})
if($remaining.Count -ne 0){throw "Treatment image is still cached on $worker"}
if($RecoverySeconds -gt 0){Start-Sleep -Seconds $RecoverySeconds}

$forecast=UtcNow;$decision=UtcNow;$scaleSent=UtcNow
$sw=[System.Diagnostics.Stopwatch]::StartNew()
kubectl scale deployment/$deployment -n $namespace --replicas=1|Out-Null
$scaleAck=UtcNow;$apiMs=$sw.Elapsed.TotalMilliseconds
$observed=$null;$served=$null;$probeAttempts=0
$deadline=(Get-Date).AddSeconds($TimeoutSeconds)
do{
  $pods=Get-ColdPods
  if($pods.items.Count -gt 0){
    $pod=$pods.items[0]
    if(!$observed){$observed=[ordered]@{pod_name=$pod.metadata.name;pod_uid=$pod.metadata.uid;first_observed_utc=UtcNow;first_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds;created_utc=$pod.metadata.creationTimestamp;scheduled_utc=$null;scheduled_observed_elapsed_ms=$null;started_utc=$null;started_observed_elapsed_ms=$null;ready_utc=$null;ready_observed_elapsed_ms=$null;image_id=$null;restart_count=$null}}
    $scheduled=ConditionTime $pod "PodScheduled";if($scheduled -and !$observed.scheduled_utc){$observed.scheduled_utc=$scheduled;$observed.scheduled_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
    $started=StartedTime $pod;if($started -and !$observed.started_utc){$observed.started_utc=$started;$observed.started_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
    $ready=ConditionTime $pod "Ready";if($ready -and !$observed.ready_utc){$observed.ready_utc=$ready;$observed.ready_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
    $cs=@($pod.status.containerStatuses|Where-Object{$_.name -eq "benchmark-app"})|Select-Object -First 1
    if($cs){$observed.image_id=$cs.imageID;$observed.restart_count=$cs.restartCount}
  }
  $probeAttempts++
  try{
    $probeStart=$sw.Elapsed.TotalMilliseconds;$headerPath=Join-Path $runDir "probe-headers.tmp"
    curl.exe --silent --show-error --max-time 2 --no-keepalive --dump-header $headerPath --output NUL $targetUrl
    if($LASTEXITCODE -ne 0){throw "probe failed"}
    $probeEnd=$sw.Elapsed.TotalMilliseconds;$headers=Get-Content $headerPath
    $uidLine=@($headers|Where-Object{$_ -match '^X-Benchmark-Pod-Uid:'})[-1]
    $readyLine=@($headers|Where-Object{$_ -match '^X-Benchmark-Ready-At:'})[-1]
    $uid=if($uidLine){($uidLine -split ':',2)[1].Trim()}else{$null}
    if($observed -and $uid -eq $observed.pod_uid -and !$served){$served=[ordered]@{first_request_utc=UtcNow;elapsed_ms=$probeEnd;rtt_ms=($probeEnd-$probeStart);app_ready_utc=if($readyLine){($readyLine -split ':',2)[1].Trim()}else{$null}}}
  }catch{}
  if($observed -and $observed.ready_utc -and $served){break}
  Start-Sleep -Milliseconds $PollMilliseconds
}until((Get-Date)-ge $deadline)
$sw.Stop()
if(!$observed -or !$observed.ready_utc -or !$served){throw "Cold trial timed out"}

$created=[datetimeoffset]$observed.created_utc;$scheduled=[datetimeoffset]$observed.scheduled_utc;$started=[datetimeoffset]$observed.started_utc;$ready=[datetimeoffset]$observed.ready_utc;$scale=[datetimeoffset]$scaleSent
$row=[pscustomobject]@{run_id=$runId;cache_treatment="cold-registry";increment=1;repetition=$Repetition;pod_name=$observed.pod_name;pod_uid=$observed.pod_uid;node=$worker;image_id=$observed.image_id;restart_count=$observed.restart_count;created_utc=$observed.created_utc;scheduled_utc=$observed.scheduled_utc;container_started_utc=$observed.started_utc;ready_utc=$observed.ready_utc;app_ready_utc=$served.app_ready_utc;first_request_utc=$served.first_request_utc;creation_delay_s=($observed.first_observed_elapsed_ms/1000);scheduling_delay_s=($scheduled-$created).TotalSeconds;startup_delay_s=($started-$scheduled).TotalSeconds;container_to_ready_s=($ready-$started).TotalSeconds;readiness_actuation_delay_s=($observed.ready_observed_elapsed_ms/1000);effective_serving_delay_s=($served.elapsed_ms/1000);first_request_probe_rtt_ms=$served.rtt_ms;api_creation_from_scale_s=($created-$scale).TotalSeconds;api_readiness_from_scale_s=($ready-$scale).TotalSeconds}
$row|Export-Csv -LiteralPath (Join-Path $runDir "per-pod.csv") -NoTypeInformation
$trial=[ordered]@{schema_version=1;run_id=$runId;valid=$true;cache_treatment="cold-registry";baseline_replicas=1;target_replicas=2;increment=1;repetition=$Repetition;forecast_available_utc=$forecast;controller_decision_utc=$decision;scale_request_sent_utc=$scaleSent;scale_request_ack_utc=$scaleAck;scale_api_roundtrip_ms=$apiMs;decision_delay_ms=(([datetimeoffset]$decision-[datetimeoffset]$forecast).TotalMilliseconds);deployment_update_from_forecast_ms=(([datetimeoffset]$scaleAck-[datetimeoffset]$forecast).TotalMilliseconds);trial_readiness_delay_s=$row.readiness_actuation_delay_s;trial_effective_serving_delay_s=$row.effective_serving_delay_s;new_pod_count=1;probe_attempts=$probeAttempts;poll_milliseconds=$PollMilliseconds;timeout_seconds=$TimeoutSeconds}
Save-Json $trial (Join-Path $runDir "trial-summary.json")
kubectl get pods -n $namespace -l $selector -o json|Set-Content (Join-Path $runDir "pods-final.json") -Encoding utf8
kubectl get events -n $namespace --sort-by=.metadata.creationTimestamp -o json|Set-Content (Join-Path $runDir "events-final.json") -Encoding utf8
Write-Output "Cold Step 6 trial complete: $runDir";$trial|ConvertTo-Json
kubectl scale deployment/$deployment -n $namespace --replicas=0|Out-Null
