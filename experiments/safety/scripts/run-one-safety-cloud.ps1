[CmdletBinding()]
param(
    [string]$RunId,
    [Parameter(Mandatory)][string]$ServerIp,
    [Parameter(Mandatory)][string]$Worker1Ip,
    [Parameter(Mandatory)][string]$Worker2Ip,
    [string]$SshUser = 'researcher',
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$Kubeconfig = "$env:USERPROFILE\.kube\config",
    [string]$Python = 'python',
    [string]$RemoteRoot = '/tmp/forecast-error-step16-v1.0.0'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $root)
$controllerRoot = Join-Path $repositoryRoot 'controller'
$controllerManifests = Join-Path $repositoryRoot 'kubernetes\controller'
$step10 = Join-Path $repositoryRoot 'monitoring'
$env:PYTHONPATH = Join-Path $step10 'src'
$env:KUBECONFIG = $Kubeconfig
$execution = Get-Content (Join-Path $root 'configuration\execution-protocol.json') -Raw | ConvertFrom-Json
$protocol = [pscustomobject]@{inter_run_stable_s=$execution.fixed_system.inter_run_stable_s;t0_lead_s=$execution.fixed_system.t0_lead_s;post_run_s=$execution.fixed_system.post_run_s;pre_run_s=$execution.fixed_system.pre_run_s;collection_interval_ms=1000;maximum_clock_skew_ms=$execution.fixed_system.maximum_clock_skew_ms;maximum_dispatch_lateness_ms=$execution.fixed_system.maximum_dispatch_lateness_ms}
$manager=Join-Path $root 'tools\campaign.py'
if(-not(Get-Command $Python -ErrorAction SilentlyContinue)){throw "Python runtime missing: $Python"}
& $Python $manager resume|Out-Null;if($LASTEXITCODE-ne0){throw 'Could not resume campaign for claim'}
$claimArgs=@('claim');if($RunId){$claimArgs+=@('--run-id',$RunId)}
$claimText=& $Python $manager @claimArgs;if($LASTEXITCODE-ne0){throw 'Could not claim next frozen cell'}
$claim=$claimText|ConvertFrom-Json;$row=$claim.matrix_row;$attempt=[int]$claim.attempt
$runId=[string]$row.run_id;$Condition=[string]$row.forecast_condition;$Repetition=[int]$row.repetition;$workloadId=[string]$row.workload_id;$duration=[int]$row.workload_duration_s
$stamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMdd-HHmmss')
$resourceId = ($runId+'-a'+$attempt).Replace('_','-')
$runRoot = Join-Path $root "results\$runId\attempt-$('{0:d2}' -f $attempt)"
$temporary = Join-Path $env:TEMP $resourceId
$remoteRun = "$RemoteRoot/runs/$runId/attempt-$('{0:d2}' -f $attempt)"
$runtimeName = "anfa-runtime-$resourceId"
$forecastName = "anfa-forecast-$resourceId"
$prometheusProcess = $null
$remoteProcess = $null
$controllerApplied = $false

function Check([string]$Message) { if ($LASTEXITCODE -ne 0) { throw $Message } }
function Write-Utf8([string]$Path,[string]$Value) { [IO.File]::WriteAllText($Path,$Value,[Text.UTF8Encoding]::new($false)) }
function Invoke-SshEncoded([string]$Command,[string]$Message) {
    $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Command))
    foreach($try in 1..3){
        $output=@(& ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o ConnectionAttempts=2 -i $SshKeyPath "${SshUser}@$ServerIp" "echo $encoded | base64 -d | bash")
        if($LASTEXITCODE-eq0){return $output}
        if($try-lt3){Start-Sleep -Seconds 2}
    }
    throw $Message
}
function Invoke-Ssh([string]$Address,[string]$Command) {
    & ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o ConnectionAttempts=2 -i $SshKeyPath "${SshUser}@$Address" $Command
    Check "SSH command failed on $Address"
}
function Measure-CloudClocks([string]$Output) {
    $attestationDirectory=Get-ChildItem (Join-Path $root 'validation') -Directory -Filter 'cloud-preflight-*' |
        Where-Object{Test-Path (Join-Path $_.FullName 'preflight-result.json')} |
        Sort-Object CreationTimeUtc -Descending | Select-Object -First 1
    if(-not$attestationDirectory){throw 'No passed Azure clock attestation is available'}
    $attestation=Get-Content (Join-Path $attestationDirectory.FullName 'preflight-result.json') -Raw|ConvertFrom-Json
    $nodeClocks=Get-Content (Join-Path $attestationDirectory.FullName 'node-clocks.json') -Raw|ConvertFrom-Json
    if(-not$attestation.passed-or-not$attestation.all_nodes_ntp-or@($nodeClocks|Where-Object{$_.ntp-ne'yes'}).Count){
        throw 'Azure NTP attestation is not valid'
    }
    # Controller, load generator, Kubernetes observation and Prometheus scrape
    # timestamps are all generated in the Azure server clock domain. Worker
    # request processing is recorded as monotonic duration; worker wall time is
    # not used to align the causal timeline.
    $result=[ordered]@{schema_version='1.0.0';measured_utc=[DateTimeOffset]::UtcNow.ToString('o');method='native UTC/NTP attestation for all three Azure nodes; single authoritative server/API/Prometheus timestamp domain for causal alignment';mode='native_sync';clock_scope='single_authoritative_timestamp_domain';maximum_allowed_skew_ms=[double]$protocol.maximum_clock_skew_ms;maximum_absolute_skew_ms=0;runner_correction_ms=0;maximum_corrected_residual_ms=0;passed=$true;attestation_directory=$attestationDirectory.FullName;attested_nodes=$nodeClocks}
    Write-Utf8 $Output ($result|ConvertTo-Json -Depth 20)
    if(-not$result.passed){throw "Azure clock skew $maximum ms exceeds $($protocol.maximum_clock_skew_ms) ms"}
}

@('metadata','inputs\rendered-manifests','raw\prometheus','normalized','validation','plots')|ForEach-Object{New-Item -ItemType Directory -Force -Path (Join-Path $runRoot $_)|Out-Null}
New-Item -ItemType Directory -Force -Path $temporary|Out-Null
Write-Utf8 (Join-Path $runRoot 'metadata\matrix-row.json') ($row|ConvertTo-Json -Depth 10)

try {
    & $Python $manager start --run-id $runId --attempt $attempt|Out-Null;if($LASTEXITCODE-ne0){throw 'Could not transition attempt to running'}
    if((& kubectl --kubeconfig $Kubeconfig config current-context).Trim()-ne'anfa-cloud'){throw 'Expected anfa-cloud context'}
    & kubectl --kubeconfig $Kubeconfig get nodes -o json|Out-File (Join-Path $runRoot 'metadata\nodes.json') -Encoding utf8;Check 'Nodes unavailable'
    $nodeData=Get-Content (Join-Path $runRoot 'metadata\nodes.json') -Raw|ConvertFrom-Json
    if(@($nodeData.items|Where-Object{-not@($_.status.conditions|Where-Object{$_.type-eq'Ready'-and$_.status-eq'True'}).Count}).Count){throw 'A node is not Ready'}
    $application=& kubectl --kubeconfig $Kubeconfig -n default get deployment benchmark-app -o json|ConvertFrom-Json;Check 'Application unavailable'
    if($application.spec.template.spec.containers[0].image-ne$execution.fixed_system.application_image){throw 'Application image differs from frozen execution protocol'}
    $hpas=(& kubectl --kubeconfig $Kubeconfig -n default get hpa -o json|ConvertFrom-Json).items
    if(@($hpas|Where-Object{$_.spec.scaleTargetRef.name-eq'benchmark-app'}).Count){throw 'An HPA targets benchmark-app'}
    & kubectl --kubeconfig $Kubeconfig -n default delete deployment predictive-autoscaler --ignore-not-found --wait=true|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default scale deployment benchmark-app --replicas=1|Out-Null;Check 'Reset scale failed'
    & kubectl --kubeconfig $Kubeconfig -n default rollout status deployment/benchmark-app --timeout=180s|Out-Null;Check 'Reset readiness failed'
    Start-Sleep -Seconds ([int]$protocol.inter_run_stable_s)
    Measure-CloudClocks (Join-Path $runRoot 'metadata\clock-preflight.json')

    $prometheusProcess=Start-Process kubectl -ArgumentList @('--kubeconfig',$Kubeconfig,'port-forward','-n','monitoring','svc/anfa-monitoring-kube-prome-prometheus','9090:9090') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runRoot 'raw\prometheus-port-forward.out') -RedirectStandardError (Join-Path $runRoot 'raw\prometheus-port-forward.err')
    $ready=$false;foreach($i in 1..20){try{Invoke-RestMethod 'http://127.0.0.1:9090/-/ready' -TimeoutSec 3|Out-Null;$ready=$true;break}catch{Start-Sleep 1}}
    if(-not$ready){throw 'Prometheus port-forward failed'}

    $monitorPatch=Join-Path $temporary 'servicemonitor-patch.json';Write-Utf8 $monitorPatch '{"spec":{"endpoints":[{"port":"http","path":"/metrics","interval":"1s","scrapeTimeout":"900ms"}]}}'
    & kubectl --kubeconfig $Kubeconfig -n default patch servicemonitor benchmark-app --type merge --patch-file $monitorPatch|Out-Null;Check 'ServiceMonitor patch failed'
    & kubectl --kubeconfig $Kubeconfig -n default get servicemonitor benchmark-app -o yaml|Out-File (Join-Path $runRoot 'inputs\rendered-manifests\servicemonitor.yaml') -Encoding utf8

    # Matrix paths retain the publication-bundle names used when the protocol
    # was frozen. Resolve them to the extracted canonical step directories.
    $workload=Join-Path $repositoryRoot "workloads\workloads\$workloadId.csv"
    $scheduleRelative=([string]$row.workload_path)-replace '^outputs/step-7-workload-suite-v1\.0\.0/',''
    $forecastRelative=([string]$row.forecast_path)-replace '^outputs/step-12-accuracy-matched-forecasts-v1\.0\.0/',''
    $oracleRelative=([string]$row.oracle_path)-replace '^outputs/step-8-oracle-reference-v1\.0\.0/',''
    $schedule=Join-Path (Join-Path $repositoryRoot 'workloads') ($scheduleRelative.Replace('/','\'))
    $forecast=Join-Path (Join-Path $repositoryRoot 'forecasts\matched') ($forecastRelative.Replace('/','\'))
    $oracle=Join-Path (Join-Path $repositoryRoot 'forecasts\oracle') ($oracleRelative.Replace('/','\'))
    foreach($file in @($workload,$schedule,$forecast,$oracle)){if(-not(Test-Path -LiteralPath $file)){throw "Frozen input missing: $file"}}
    if((Get-FileHash $schedule -Algorithm SHA256).Hash.ToLowerInvariant()-ne$row.workload_sha256){throw 'Workload schedule hash mismatch'}
    if((Get-FileHash $forecast -Algorithm SHA256).Hash.ToLowerInvariant()-ne$row.forecast_sha256){throw 'Forecast hash mismatch'}
    if((Get-FileHash $oracle -Algorithm SHA256).Hash.ToLowerInvariant()-ne$row.oracle_sha256){throw 'Oracle hash mismatch'}
    $policy=Join-Path $controllerRoot 'configuration\policy-config.json'
    $safetyPolicy=Join-Path $controllerRoot 'configuration\safety-policy.json'
    Copy-Item $workload (Join-Path $runRoot 'inputs\workload.csv')
    Copy-Item $schedule (Join-Path $runRoot 'inputs\schedule.csv')
    Copy-Item $forecast (Join-Path $runRoot 'inputs\forecast.csv')
    Copy-Item $oracle (Join-Path $runRoot 'inputs\oracle.csv')
    Copy-Item $policy (Join-Path $runRoot 'inputs\policy-config.json')
    Copy-Item $safetyPolicy (Join-Path $runRoot 'inputs\safety-policy.json')

    $t0=[DateTimeOffset]::UtcNow.AddSeconds([int]$protocol.t0_lead_s);$t0Text=$t0.ToString('o')
    $runtimePath=Join-Path $temporary 'runtime-config.json'
    $runtime=[ordered]@{experiment_id='step16-safety-ablation';run_id=$runId;controller_id='predictive-autoscaler-v1.1-safety';trace_id=$workloadId;condition=$Condition;namespace='default';deployment='benchmark-app';forecast_path='/etc/anfa/forecast/forecast.csv';policy_path='/etc/anfa/policy/policy-config.json';t0_utc=$t0Text;health_address=':8081';safety_enabled=$true;safety_policy_path='/etc/anfa/safety/safety-policy.json'}
    Write-Utf8 $runtimePath ($runtime|ConvertTo-Json)
    & kubectl --kubeconfig $Kubeconfig apply -f (Join-Path $controllerManifests 'serviceaccount.yaml')|Out-Null
    & kubectl --kubeconfig $Kubeconfig apply -f (Join-Path $controllerManifests 'rbac.yaml')|Out-Null
    & kubectl --kubeconfig $Kubeconfig apply -f (Join-Path $controllerManifests 'policy-configmap.yaml')|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default delete configmap predictive-autoscaler-safety-policy-v1 --ignore-not-found|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default create configmap predictive-autoscaler-safety-policy-v1 --from-file="safety-policy.json=$safetyPolicy"|Out-Null;Check 'Safety policy ConfigMap failed'
    $safetyImmutable=Join-Path $temporary 'safety-immutable.json';Write-Utf8 $safetyImmutable '{"immutable":true}'
    & kubectl --kubeconfig $Kubeconfig -n default patch configmap predictive-autoscaler-safety-policy-v1 --type merge --patch-file $safetyImmutable|Out-Null;Check 'Safety policy immutability failed'
    & kubectl --kubeconfig $Kubeconfig apply -f (Join-Path $controllerManifests 'safety-service.yaml')|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default create configmap $runtimeName --from-file="runtime-config.json=$runtimePath"|Out-Null;Check 'Runtime ConfigMap failed'
    & kubectl --kubeconfig $Kubeconfig -n default create configmap $forecastName --from-file="forecast.csv=$forecast"|Out-Null;Check 'Forecast ConfigMap failed'
    $immutable=Join-Path $temporary 'immutable.json';Write-Utf8 $immutable '{"immutable":true}'
    & kubectl --kubeconfig $Kubeconfig -n default patch configmap $runtimeName --type merge --patch-file $immutable|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default patch configmap $forecastName --type merge --patch-file $immutable|Out-Null
    $deployment=[IO.File]::ReadAllText((Join-Path $controllerManifests 'deployment.yaml')).Replace('anfa-autoscaler-runtime-current',$runtimeName).Replace('anfa-forecast-current',$forecastName).Replace('node-role.kubernetes.io/control-plane: ""','node-role.kubernetes.io/control-plane: "true"')
    $rendered=Join-Path $runRoot 'inputs\rendered-manifests\controller-deployment.yaml';Write-Utf8 $rendered $deployment

    $remoteScriptLocal=Join-Path $temporary 'run-evidence.sh'
    $remoteScriptPath="$remoteRun/input/run-evidence.sh"
    $collectorDuration=[int]$protocol.t0_lead_s+$duration+[int]$protocol.post_run_s
    Invoke-SshEncoded "set -euo pipefail; rm -rf '$remoteRun'; mkdir -p '$remoteRun/input' '$remoteRun/raw'" 'Remote attempt directory failed'|Out-Null
    & scp -q -o BatchMode=yes -i $SshKeyPath $schedule "${SshUser}@${ServerIp}:$remoteRun/input/schedule.csv";Check 'Schedule upload failed'
    $remoteScript=@"
#!/usr/bin/env bash
set -uo pipefail
export PATH="$RemoteRoot/bin:/usr/bin:/bin"
 export PYTHONPATH="$RemoteRoot/staging/step16-loadgen"
printf '{"started_utc":"%s","run_id":"%s"}\n' "`$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" '$runId' >'$remoteRun/raw/remote-started.json'
/usr/bin/python3 -m anfa_observability.kubernetes --output '$remoteRun/raw/kubernetes-snapshots.jsonl' --run-id '$runId' --duration-seconds '$collectorDuration' --interval-ms '$($protocol.collection_interval_ms)' >'$remoteRun/raw/kubernetes-collector.out' 2>'$remoteRun/raw/kubernetes-collector.err' &
KUBE_PID=`$!
 /usr/bin/python3 -m anfa_observability.loadgen --schedule '$remoteRun/input/schedule.csv' --output '$remoteRun/raw/load-generator-requests.jsonl' --target-url 'http://127.0.0.1:30080/work' --t0-utc '$t0Text' --experiment-id 'step16-safety-ablation' --run-id '$runId' --workload-id '$workloadId' --forecast-condition '$Condition' --safety-observation-url 'http://127.0.0.1:30081/v1/safety/observations' --safety-observation-grace-ms 150 --safety-observation-output '$remoteRun/raw/safety-observations.jsonl' >'$remoteRun/raw/load-generator.out' 2>'$remoteRun/raw/load-generator.err'
LOAD_STATUS=`$?
wait `$KUBE_PID
KUBE_STATUS=`$?
printf '{"load_exit":%s,"kubernetes_exit":%s}\n' "`$LOAD_STATUS" "`$KUBE_STATUS" >'$remoteRun/raw/remote-status.json'
test "`$LOAD_STATUS" -eq 0 -a "`$KUBE_STATUS" -eq 0
"@
    Write-Utf8 $remoteScriptLocal $remoteScript
    & scp -q -o BatchMode=yes -o ConnectTimeout=20 -i $SshKeyPath $remoteScriptLocal "${SshUser}@${ServerIp}:$remoteScriptPath";Check 'Remote runner upload failed'
    $expectedScriptHash=(Get-FileHash $remoteScriptLocal -Algorithm SHA256).Hash.ToLowerInvariant()
    $verifyText=(Invoke-SshEncoded "set -euo pipefail; test -s '$remoteScriptPath'; test -s '$remoteRun/input/schedule.csv'; sha256sum '$remoteScriptPath'" 'Remote runner verification failed') -join ' '
    if($verifyText-notmatch[regex]::Escape($expectedScriptHash)){throw 'Remote runner hash mismatch'}
    $launchCommand="exec bash '$remoteScriptPath'"
    $launchEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($launchCommand))
    # Allow a transient Azure network pause of up to one minute without
    # terminating the remote evidence runner. This affects transport only;
    # experiment timing and collection remain in the Azure clock domain.
    $remoteProcess=Start-Process ssh -ArgumentList @('-n','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','ConnectTimeout=20','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=12','-i',$SshKeyPath,"${SshUser}@$ServerIp","echo $launchEncoded | base64 -d | bash") -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runRoot 'raw\remote-runner.out') -RedirectStandardError (Join-Path $runRoot 'raw\remote-runner.err')
    Start-Sleep -Seconds 5
    $remoteProcess.Refresh()
    if($remoteProcess.HasExited){throw "Remote evidence runner exited during startup with code $($remoteProcess.ExitCode)"}

    & kubectl --kubeconfig $Kubeconfig apply -f $rendered|Out-Null;Check 'Controller apply failed';$controllerApplied=$true
    & kubectl --kubeconfig $Kubeconfig -n default rollout status deployment/predictive-autoscaler --timeout=90s|Out-Null
    if($LASTEXITCODE-ne0){
        & kubectl --kubeconfig $Kubeconfig -n default get pods -l app.kubernetes.io/name=predictive-autoscaler -o wide|Out-File (Join-Path $runRoot 'raw\controller-rollout-pods.txt') -Encoding utf8
        & kubectl --kubeconfig $Kubeconfig -n default describe pods -l app.kubernetes.io/name=predictive-autoscaler|Out-File (Join-Path $runRoot 'raw\controller-rollout-describe.txt') -Encoding utf8
        & kubectl --kubeconfig $Kubeconfig -n default logs -l app.kubernetes.io/name=predictive-autoscaler --all-containers --prefix|Out-File (Join-Path $runRoot 'raw\controller-rollout.log') -Encoding utf8
        & kubectl --kubeconfig $Kubeconfig -n default get events --sort-by=.metadata.creationTimestamp|Out-File (Join-Path $runRoot 'raw\controller-rollout-events.txt') -Encoding utf8
        throw 'Controller rollout failed; pod diagnostics preserved'
    }
    if([DateTimeOffset]::UtcNow.AddSeconds(30)-gt$t0){throw 'Less than 30 seconds remain before T0'}
    $remoteProcess.WaitForExit();$remoteProcess.Refresh()
    $remoteExit=$remoteProcess.ExitCode
    if($null-ne$remoteExit-and$remoteExit-ne0){throw "Remote evidence runner exited $remoteExit"}

    & scp -q -o BatchMode=yes -i $SshKeyPath -r "${SshUser}@${ServerIp}:$remoteRun/raw/." (Join-Path $runRoot 'raw');Check 'Evidence download failed'
    $remoteStatusPath=Join-Path $runRoot 'raw\remote-status.json'
    if(-not(Test-Path -LiteralPath $remoteStatusPath)){throw 'Remote completion status is missing'}
    $remoteStatus=Get-Content $remoteStatusPath -Raw|ConvertFrom-Json
    & kubectl --kubeconfig $Kubeconfig -n default logs deployment/predictive-autoscaler|Out-File (Join-Path $runRoot 'raw\controller-full.jsonl') -Encoding utf8;Check 'Controller log capture failed'
    if($remoteStatus.load_exit-ne0-or$remoteStatus.kubernetes_exit-ne0){throw "Remote evidence failure: load=$($remoteStatus.load_exit), kubernetes=$($remoteStatus.kubernetes_exit)"}
    & $Python (Join-Path $root 'tools\split_controller_log.py') --input (Join-Path $runRoot 'raw\controller-full.jsonl') --decisions (Join-Path $runRoot 'raw\controller.jsonl') --safety (Join-Path $runRoot 'raw\safety-controller.jsonl');Check 'Controller log split failed'
    & kubectl --kubeconfig $Kubeconfig -n default logs -l app.kubernetes.io/name=benchmark-app --all-containers --prefix|Out-File (Join-Path $runRoot 'raw\application.log') -Encoding utf8
    & kubectl --kubeconfig $Kubeconfig -n default get events --sort-by=.metadata.creationTimestamp -o json|Out-File (Join-Path $runRoot 'raw\kubernetes-events.json') -Encoding utf8
    & kubectl --kubeconfig $Kubeconfig -n default get deployment benchmark-app -o json|Out-File (Join-Path $runRoot 'raw\deployment-final.json') -Encoding utf8
    & kubectl --kubeconfig $Kubeconfig -n default get pods -l app.kubernetes.io/name=benchmark-app -o json|Out-File (Join-Path $runRoot 'raw\pods-final.json') -Encoding utf8
    & kubectl --kubeconfig $Kubeconfig -n default get endpointslices -l kubernetes.io/service-name=benchmark-app -o json|Out-File (Join-Path $runRoot 'raw\endpointslices-final.json') -Encoding utf8

    $startEpoch=$t0.ToUnixTimeSeconds()-[int]$protocol.pre_run_s;$endEpoch=$t0.ToUnixTimeSeconds()+$duration+[int]$protocol.post_run_s
    & $Python -m anfa_observability.prometheus --url http://127.0.0.1:9090 --queries (Join-Path $step10 'configuration\prometheus-queries.json') --output-directory (Join-Path $runRoot 'raw\prometheus') --start-epoch $startEpoch --end-epoch $endEpoch --step-seconds 1 --run-id $runId;Check 'Prometheus export failed'
    Measure-CloudClocks (Join-Path $runRoot 'metadata\clock-postflight.json')

    $identityPath=Join-Path $temporary 'identity.json';$mutation=(Import-Csv $forecast|Select-Object -First 1).mutation_id
    $identity=[ordered]@{experiment_id='step16-safety-ablation';run_id=$runId;workload_id=$workloadId;forecast_condition=$Condition;mutation_id=$mutation;pair_manifest_id=$row.pair_id;controller_version='1.1.1';controller_image=$execution.fixed_system.controller_image;controller_image_archive_sha256=$execution.fixed_system.controller_image_archive_sha256;application_image=$execution.fixed_system.application_image;cluster_version=$execution.fixed_system.cluster.kubernetes_version;random_seed='14001';namespace='default';deployment='benchmark-app';t0_utc=$t0Text;started_utc=$t0Text;ended_utc=[DateTimeOffset]::UtcNow.ToString('o');status='step16_safety_evidence';repetition=$Repetition;attempt=$attempt;safety_enabled=$true;step16_sequence=[int]$row.step16_sequence;safety_off_run_id=$row.safety_off_run_id;safety_off_valid_attempt=$row.safety_off_valid_attempt}
    Write-Utf8 $identityPath ($identity|ConvertTo-Json)
    & $Python -m anfa_observability.metadata --output (Join-Path $runRoot 'metadata\run-metadata.json') --identity-json $identityPath --input "workload=$workload" --input "schedule=$schedule" --input "forecast=$forecast" --input "oracle=$oracle" --input "policy=$policy" --input "protocol=$(Join-Path $root 'configuration\execution-protocol.json')";Check 'Metadata failed'
    & $Python -m anfa_observability.normalize --workload-path $workload --requests-path (Join-Path $runRoot 'raw\load-generator-requests.jsonl') --controller-path (Join-Path $runRoot 'raw\controller.jsonl') --kubernetes-path (Join-Path $runRoot 'raw\kubernetes-snapshots.jsonl') --prometheus-directory (Join-Path $runRoot 'raw\prometheus') --t0-utc $t0Text --duration-seconds $duration --output-path (Join-Path $runRoot 'normalized\joined-timeline.csv');Check 'Normalization failed'
    & $Python -m anfa_observability.plots --timeline (Join-Path $runRoot 'normalized\joined-timeline.csv') --output-directory (Join-Path $runRoot 'plots');Check 'Plots failed'
    & $Python -m anfa_observability.validate $runRoot --maximum-clock-skew-ms ([int]$protocol.maximum_clock_skew_ms) --maximum-dispatch-lateness-ms ([int]$protocol.maximum_dispatch_lateness_ms)|Out-Null
    & $Python (Join-Path $root 'tools\validate_safety_run.py') --run-root $runRoot --row-json (Join-Path $runRoot 'metadata\matrix-row.json') --protocol (Join-Path $root 'configuration\execution-protocol.json');Check 'Step 16 safety validation failed'
    & $Python -m anfa_observability.checksums $runRoot --output (Join-Path $runRoot 'validation\checksums.sha256');Check 'Checksums failed'
    & $Python $manager finish --run-id $runId --attempt $attempt --result valid|Out-Null;Check 'Campaign state finalization failed'
    Write-Host "STEP 16 SAFETY RUN PASSED: $runId attempt $attempt"
    Write-Host "Evidence: $runRoot"
}
catch{
    $reason=$_.Exception.Message;[ordered]@{run_id=$runId;attempt=$attempt;condition=$Condition;repetition=$Repetition;failed_utc=[DateTimeOffset]::UtcNow.ToString('o');error=$reason}|ConvertTo-Json|Set-Content (Join-Path $runRoot 'validation\run-failure.json') -Encoding utf8
    & $Python $manager finish --run-id $runId --attempt $attempt --result invalid --reason $reason|Out-Null
    Write-Host "Final run invalid. Evidence preserved: $runRoot";throw
}
finally{
    if($remoteProcess-and-not$remoteProcess.HasExited){Stop-Process -Id $remoteProcess.Id -Force}
    if($prometheusProcess-and-not$prometheusProcess.HasExited){Stop-Process -Id $prometheusProcess.Id -Force}
    if($controllerApplied){& kubectl --kubeconfig $Kubeconfig -n default delete deployment predictive-autoscaler --ignore-not-found --wait=true|Out-Null}
    & kubectl --kubeconfig $Kubeconfig -n default delete configmap $runtimeName $forecastName --ignore-not-found|Out-Null
    $restore=Join-Path $temporary 'restore-monitor.json';Write-Utf8 $restore '{"spec":{"endpoints":[{"port":"http","path":"/metrics","interval":"15s","scrapeTimeout":"5s"}]}}'
    & kubectl --kubeconfig $Kubeconfig -n default patch servicemonitor benchmark-app --type merge --patch-file $restore|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default scale deployment benchmark-app --replicas=1|Out-Null
    & kubectl --kubeconfig $Kubeconfig -n default rollout status deployment/benchmark-app --timeout=180s|Out-Null
    if(Test-Path $temporary){Remove-Item -LiteralPath $temporary -Recurse -Force}
}
