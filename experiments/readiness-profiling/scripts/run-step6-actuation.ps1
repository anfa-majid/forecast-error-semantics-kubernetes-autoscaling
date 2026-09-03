param(
  [ValidateSet(2,3,4)][int]$TargetReplicas = 2,
  [int]$Repetition = 1,
  [int]$PollMilliseconds = 100,
  [int]$TimeoutSeconds = 180,
  [int]$RecoverySeconds = 15,
  [string]$RunLabel = "cached"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$namespace = "default"
$deployment = "benchmark-app"
$selector = "app.kubernetes.io/name=benchmark-app"
$targetUrl = "http://127.0.0.1:30080/work"
$runId = "{0}-1to{1}-rep{2:D2}-{3}" -f $RunLabel,$TargetReplicas,$Repetition,(Get-Date -Format "yyyyMMdd-HHmmss")
$runDir = Join-Path $root "step6\runs\$runId"

function UtcNow { (Get-Date).ToUniversalTime().ToString("o") }
function Save-Json($value,[string]$path) { $value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding utf8 }
function Get-BenchmarkPods { kubectl get pods -n $namespace -l $selector -o json | ConvertFrom-Json }
function Get-ConditionTime($pod,[string]$type) {
  $c = @($pod.status.conditions | Where-Object { $_.type -eq $type -and $_.status -eq "True" }) | Select-Object -First 1
  if ($c) { return $c.lastTransitionTime }
  return $null
}
function Get-ContainerStarted($pod) {
  $c = @($pod.status.containerStatuses | Where-Object { $_.name -eq "benchmark-app" }) | Select-Object -First 1
  if ($c -and $c.state.running) { return $c.state.running.startedAt }
  return $null
}
function Wait-ExactReady([int]$count,[int]$timeout) {
  $deadline=(Get-Date).AddSeconds($timeout)
  do {
    $pods=Get-BenchmarkPods
    $ready=@($pods.items | Where-Object { (Get-ConditionTime $_ "Ready") }).Count
    if ($pods.items.Count -eq $count -and $ready -eq $count) { return $pods }
    Start-Sleep -Milliseconds 250
  } until ((Get-Date) -ge $deadline)
  throw "Timed out waiting for exactly $count Ready benchmark Pods"
}

if ((kubectl config current-context) -ne "kind-anfa-dev") { throw "Expected context kind-anfa-dev" }
if ($TargetReplicas -le 1) { throw "TargetReplicas must be greater than one" }
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
Copy-Item -LiteralPath (Join-Path $root "step6\experiment-config.json") -Destination $runDir

# First-service measurement is impossible without the documented local bridge.
# Fail before changing replica state instead of waiting for the trial timeout.
curl.exe --fail --silent --output NUL "http://127.0.0.1:30080/livez"
if ($LASTEXITCODE -ne 0) { throw "NodePort bridge is unavailable at http://127.0.0.1:30080" }

$valid=$false
$invalidReason=$null
try {
  kubectl scale deployment/$deployment -n $namespace --replicas=1 | Out-Null
  kubectl rollout status deployment/$deployment -n $namespace --timeout=180s | Out-Null
  $baseline=Wait-ExactReady 1 180
  if ($RecoverySeconds -gt 0) { Start-Sleep -Seconds $RecoverySeconds }
  $baseline=Get-BenchmarkPods
  $baselineUids=@($baseline.items | ForEach-Object { $_.metadata.uid })
  Save-Json $baseline (Join-Path $runDir "pods-baseline.json")
  kubectl get deployment $deployment -n $namespace -o json | Set-Content (Join-Path $runDir "deployment-baseline.json") -Encoding utf8

  $forecast=UtcNow
  $decision=UtcNow
  $scaleSent=UtcNow
  $sw=[System.Diagnostics.Stopwatch]::StartNew()
  kubectl scale deployment/$deployment -n $namespace --replicas=$TargetReplicas | Out-Null
  $scaleAck=UtcNow
  $scaleAckElapsedMs=$sw.Elapsed.TotalMilliseconds

  $observed=@{}
  $served=@{}
  $probeAttempts=0
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $observedAt=UtcNow
    $pods=Get-BenchmarkPods
    foreach($pod in $pods.items) {
      if ($baselineUids -contains $pod.metadata.uid) { continue }
      $uid=[string]$pod.metadata.uid
      if (!$observed.ContainsKey($uid)) {
        $observed[$uid]=[ordered]@{pod_name=$pod.metadata.name;pod_uid=$uid;node=$pod.spec.nodeName;first_observed_utc=$observedAt;first_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds;created_utc=$pod.metadata.creationTimestamp;scheduled_utc=$null;scheduled_observed_elapsed_ms=$null;container_started_utc=$null;container_started_observed_elapsed_ms=$null;ready_utc=$null;ready_observed_elapsed_ms=$null;image_id=$null;restart_count=$null}
      }
      $x=$observed[$uid]
      $x.node=$pod.spec.nodeName
      $scheduled=Get-ConditionTime $pod "PodScheduled"; if($scheduled -and !$x.scheduled_utc){$x.scheduled_utc=$scheduled;$x.scheduled_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
      $started=Get-ContainerStarted $pod; if($started -and !$x.container_started_utc){$x.container_started_utc=$started;$x.container_started_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
      $ready=Get-ConditionTime $pod "Ready"; if($ready -and !$x.ready_utc){$x.ready_utc=$ready;$x.ready_observed_elapsed_ms=$sw.Elapsed.TotalMilliseconds}
      $cs=@($pod.status.containerStatuses | Where-Object {$_.name -eq "benchmark-app"}) | Select-Object -First 1
      if($cs){$x.image_id=$cs.imageID;$x.restart_count=$cs.restartCount}
    }

    $probeAttempts++
    try {
      $probeStart=$sw.Elapsed.TotalMilliseconds
      # curl provides a hard per-request deadline and a fresh process/connection,
      # avoiding Windows PowerShell HTTP connection pooling and timeout hangs.
      $headerPath=Join-Path $runDir "probe-headers.tmp"
      curl.exe --silent --show-error --max-time 2 --no-keepalive --dump-header $headerPath --output NUL $targetUrl
      if($LASTEXITCODE -ne 0){throw "probe failed"}
      $probeEnd=$sw.Elapsed.TotalMilliseconds
      $headers=Get-Content -LiteralPath $headerPath
      $statusLine=@($headers | Where-Object {$_ -match '^HTTP/'})[-1]
      $uidLine=@($headers | Where-Object {$_ -match '^X-Benchmark-Pod-Uid:'})[-1]
      $readyLine=@($headers | Where-Object {$_ -match '^X-Benchmark-Ready-At:'})[-1]
      $uid=if($uidLine){($uidLine -split ':',2)[1].Trim()}else{$null}
      $appReady=if($readyLine){($readyLine -split ':',2)[1].Trim()}else{$null}
      if($uid -and $observed.ContainsKey($uid) -and !$served.ContainsKey($uid)) {
        $served[$uid]=[ordered]@{first_request_observed_utc=UtcNow;first_request_elapsed_ms=$probeEnd;probe_started_elapsed_ms=$probeStart;probe_rtt_ms=($probeEnd-$probeStart);app_ready_utc=$appReady;http_status=200}
      }
    } catch { }

    $allReady=($observed.Count -eq ($TargetReplicas-1)) -and (@($observed.Values | Where-Object {!$_.ready_utc}).Count -eq 0)
    $allServed=($served.Count -eq ($TargetReplicas-1))
    if($allReady -and $allServed){break}
    Start-Sleep -Milliseconds $PollMilliseconds
  } until ((Get-Date) -ge $deadline)
  $sw.Stop()

  if(!$allReady){throw "Not all new Pods became Ready before timeout"}
  if(!$allServed){throw "Not all new Pods served a request before timeout"}
  $perPod=@()
  foreach($uid in ($observed.Keys | Sort-Object)) {
    $x=$observed[$uid];$s=$served[$uid]
    $created=[datetimeoffset]$x.created_utc;$scheduled=[datetimeoffset]$x.scheduled_utc;$started=[datetimeoffset]$x.container_started_utc;$ready=[datetimeoffset]$x.ready_utc
    $scale=[datetimeoffset]$scaleSent
    $perPod += [pscustomobject]@{
      run_id=$runId;target_replicas=$TargetReplicas;increment=($TargetReplicas-1);pod_name=$x.pod_name;pod_uid=$uid;node=$x.node;image_id=$x.image_id;restart_count=$x.restart_count
      created_utc=$x.created_utc;scheduled_utc=$x.scheduled_utc;container_started_utc=$x.container_started_utc;ready_utc=$x.ready_utc;app_ready_utc=$s.app_ready_utc;first_request_utc=$s.first_request_observed_utc
      creation_delay_s=($x.first_observed_elapsed_ms/1000.0);scheduling_delay_s=($scheduled-$created).TotalSeconds;startup_delay_s=($started-$scheduled).TotalSeconds;container_to_ready_s=($ready-$started).TotalSeconds
      readiness_actuation_delay_s=($x.ready_observed_elapsed_ms/1000.0);effective_serving_delay_s=($s.first_request_elapsed_ms/1000.0);first_request_probe_rtt_ms=$s.probe_rtt_ms
      api_creation_from_scale_s=($created-$scale).TotalSeconds;api_readiness_from_scale_s=($ready-$scale).TotalSeconds;first_observed_utc=$x.first_observed_utc
    }
  }
  $perPod | Export-Csv -LiteralPath (Join-Path $runDir "per-pod.csv") -NoTypeInformation
  $trial=[ordered]@{
    schema_version=1;run_id=$runId;valid=$true;cache_treatment=$RunLabel;baseline_replicas=1;target_replicas=$TargetReplicas;increment=($TargetReplicas-1);repetition=$Repetition
    forecast_available_utc=$forecast;controller_decision_utc=$decision;scale_request_sent_utc=$scaleSent;scale_request_ack_utc=$scaleAck;scale_api_roundtrip_ms=$scaleAckElapsedMs
    decision_delay_ms=(([datetimeoffset]$decision-[datetimeoffset]$forecast).TotalMilliseconds);deployment_update_from_forecast_ms=(([datetimeoffset]$scaleAck-[datetimeoffset]$forecast).TotalMilliseconds)
    trial_readiness_delay_s=($perPod.readiness_actuation_delay_s | Measure-Object -Maximum).Maximum;trial_effective_serving_delay_s=($perPod.effective_serving_delay_s | Measure-Object -Maximum).Maximum
    new_pod_count=$perPod.Count;probe_attempts=$probeAttempts;poll_milliseconds=$PollMilliseconds;timeout_seconds=$TimeoutSeconds
  }
  Save-Json $trial (Join-Path $runDir "trial-summary.json")
  kubectl get deployment $deployment -n $namespace -o json | Set-Content (Join-Path $runDir "deployment-final.json") -Encoding utf8
  kubectl get replicasets -n $namespace -l $selector -o json | Set-Content (Join-Path $runDir "replicasets-final.json") -Encoding utf8
  kubectl get pods -n $namespace -l $selector -o json | Set-Content (Join-Path $runDir "pods-final.json") -Encoding utf8
  kubectl get endpointslices -n $namespace -l kubernetes.io/service-name=benchmark-app -o json | Set-Content (Join-Path $runDir "endpointslices-final.json") -Encoding utf8
  kubectl get events -n $namespace --sort-by=.metadata.creationTimestamp -o json | Set-Content (Join-Path $runDir "events-final.json") -Encoding utf8
  kubectl get nodes -o json | Set-Content (Join-Path $runDir "nodes.json") -Encoding utf8
  $valid=$true
  Write-Output "Step 6 trial complete: $runDir"
  $trial | ConvertTo-Json
} catch {
  $invalidReason=$_.Exception.Message
  Save-Json ([ordered]@{schema_version=1;run_id=$runId;valid=$false;reason=$invalidReason;captured_utc=UtcNow}) (Join-Path $runDir "invalid-trial.json")
  kubectl get deployment $deployment -n $namespace -o json | Set-Content (Join-Path $runDir "deployment-invalid.json") -Encoding utf8 -ErrorAction SilentlyContinue
  kubectl get pods -n $namespace -l $selector -o json | Set-Content (Join-Path $runDir "pods-invalid.json") -Encoding utf8 -ErrorAction SilentlyContinue
  kubectl get events -n $namespace --sort-by=.metadata.creationTimestamp -o json | Set-Content (Join-Path $runDir "events-invalid.json") -Encoding utf8 -ErrorAction SilentlyContinue
  throw
} finally {
  kubectl scale deployment/$deployment -n $namespace --replicas=1 | Out-Null
  kubectl rollout status deployment/$deployment -n $namespace --timeout=180s | Out-Null
}
