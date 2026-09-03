param(
    [Parameter(Mandatory)]
    [ValidateRange(1, 100000)]
    [int]$Rate,

    [Parameter(Mandatory)]
    [ValidateRange(1, 100)]
    [int]$Replicas,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$ServerIp,

    [string]$SshUser = "researcher",

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$SshKeyPath,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputRoot,

    [ValidateRange(30, 3600)]
    [int]$DurationSeconds = 120,

    [ValidateRange(1, 20)]
    [int]$Repetitions = 3,

    [ValidateRange(0, 600)]
    [int]$RecoverySeconds = 60,

    [string]$ExpectedContext = "research-cluster",

    [string]$PrometheusUrl = "http://127.0.0.1:9090"
)

$ErrorActionPreference = "Stop"

function Invoke-AnfaPrometheusQuery {
    param([Parameter(Mandatory)][string]$Query)

    $encodedQuery = [System.Uri]::EscapeDataString($Query)
    Invoke-RestMethod -Uri "$PrometheusUrl/api/v1/query?query=$encodedQuery" -TimeoutSec 15
}

function Save-CommandJson {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$Path
    )

    $value = & kubectl @Arguments | ConvertFrom-Json
    $value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Get-BenchmarkPodState {
    $state = kubectl get pods -n default -l app.kubernetes.io/name=benchmark-app -o json | ConvertFrom-Json
    $ready = @(
        $state.items | Where-Object {
            $_.status.phase -eq "Running" -and
            $_.status.containerStatuses.Count -eq 1 -and
            $_.status.containerStatuses[0].ready
        }
    ).Count
    $restarts = ($state.items.status.containerStatuses.restartCount | Measure-Object -Sum).Sum
    if ($null -eq $restarts) { $restarts = 0 }

    [pscustomobject]@{
        Raw = $state
        Ready = $ready
        Restarts = [int]$restarts
    }
}

if ((kubectl config current-context) -ne $ExpectedContext) {
    throw "Expected Kubernetes context '$ExpectedContext'."
}

if (-not (Test-Path -LiteralPath $OutputRoot)) {
    New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
}

Invoke-RestMethod -Uri "$PrometheusUrl/-/ready" -TimeoutSec 5 | Out-Null

$baseline = Get-BenchmarkPodState
if ($baseline.Ready -ne $Replicas -or $baseline.Restarts -ne 0) {
    throw "Preflight failed: expected $Replicas Ready Pods and zero restarts; found $($baseline.Ready) Ready and $($baseline.Restarts) restarts."
}

$campaignId = "${Replicas}-pod-rps-${Rate}-formal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$campaignDirectory = Join-Path $OutputRoot $campaignId
New-Item -ItemType Directory -Force -Path $campaignDirectory | Out-Null

$campaignResults = @()

foreach ($repetition in 1..$Repetitions) {
    $runId = "rep-$('{0:D2}' -f $repetition)"
    $runDirectory = Join-Path $campaignDirectory $runId
    New-Item -ItemType Directory -Force -Path $runDirectory | Out-Null

    Write-Host "Starting repetition $repetition of $Repetitions at $Rate RPS with $Replicas Pods"

    Save-CommandJson -Arguments @("get", "deployment", "benchmark-app", "-n", "default", "-o", "json") -Path (Join-Path $runDirectory "deployment-before.json")
    Save-CommandJson -Arguments @("get", "pods", "-n", "default", "-l", "app.kubernetes.io/name=benchmark-app", "-o", "json") -Path (Join-Path $runDirectory "pods-before.json")
    Save-CommandJson -Arguments @("get", "endpointslices", "-n", "default", "-l", "kubernetes.io/service-name=benchmark-app", "-o", "json") -Path (Join-Path $runDirectory "endpoints-before.json")

    $samples = @()
    $readinessViolation = $false
    $trialStartUtc = (Get-Date).ToUniversalTime()

    $loadJob = Start-Job -ScriptBlock {
        param($KeyPath, $Address, $TargetRate, $TestDuration)
        & ssh -i $KeyPath "${SshUser}@$Address" "TARGET_URL=http://127.0.0.1:30080/work TARGET_RPS=$TargetRate DURATION_SECONDS=$TestDuration /usr/local/bin/anfa-loadcheck"
        if ($LASTEXITCODE -ne 0) { throw "Remote load generator exited with code $LASTEXITCODE" }
    } -ArgumentList $SshKeyPath, $ServerIp, $Rate, $DurationSeconds

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        while ((Get-Job -Id $loadJob.Id).State -eq "Running") {
            Start-Sleep -Seconds 5

            $podState = Get-BenchmarkPodState
            if ($podState.Ready -ne $Replicas -or $podState.Restarts -ne 0) {
                $readinessViolation = $true
            }

            if ($timer.Elapsed.TotalSeconds -ge 30) {
                $cpu = Invoke-AnfaPrometheusQuery 'rate(container_cpu_usage_seconds_total{namespace="default",container="benchmark-app"}[30s])'
                $throttle = Invoke-AnfaPrometheusQuery 'rate(container_cpu_cfs_throttled_periods_total{namespace="default",container="benchmark-app"}[30s]) / rate(container_cpu_cfs_periods_total{namespace="default",container="benchmark-app"}[30s])'

                foreach ($cpuItem in $cpu.data.result) {
                    $podName = $cpuItem.metric.pod
                    $throttleItem = $throttle.data.result | Where-Object { $_.metric.pod -eq $podName } | Select-Object -First 1
                    if ($throttleItem) {
                        $samples += [pscustomobject]@{
                            TimestampUtc = (Get-Date).ToUniversalTime().ToString("o")
                            Pod = $podName
                            CpuMillicores = [double]$cpuItem.value[1] * 1000
                            ThrottlePercent = [double]$throttleItem.value[1] * 100
                        }
                    }
                }
            }
        }

        $rawResult = @(Receive-Job -Job $loadJob)
    }
    finally {
        $timer.Stop()
        Remove-Job -Job $loadJob -Force -ErrorAction SilentlyContinue
    }

    $trialEndUtc = (Get-Date).ToUniversalTime()
    $rawResult | Set-Content -LiteralPath (Join-Path $runDirectory "client-output.txt") -Encoding utf8
    $jsonLine = @($rawResult | Where-Object { $_ -match '^\{' })[-1]
    if (-not $jsonLine) { throw "Repetition $repetition returned no JSON result." }
    $client = $jsonLine | ConvertFrom-Json
    $client | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $runDirectory "client-summary.json") -Encoding utf8

    $samples | Export-Csv -LiteralPath (Join-Path $runDirectory "resource-samples.csv") -NoTypeInformation
    $resourceSummary = @(
        $samples | Group-Object Pod | ForEach-Object {
            [pscustomobject]@{
                Pod = $_.Name
                Samples = $_.Count
                MeanCpuMillicores = [math]::Round(($_.Group.CpuMillicores | Measure-Object -Average).Average, 2)
                PeakCpuMillicores = [math]::Round(($_.Group.CpuMillicores | Measure-Object -Maximum).Maximum, 2)
                MeanThrottlePct = [math]::Round(($_.Group.ThrottlePercent | Measure-Object -Average).Average, 2)
                PeakThrottlePct = [math]::Round(($_.Group.ThrottlePercent | Measure-Object -Maximum).Maximum, 2)
            }
        }
    )
    $resourceSummary | Export-Csv -LiteralPath (Join-Path $runDirectory "resource-summary.csv") -NoTypeInformation

    Save-CommandJson -Arguments @("get", "pods", "-n", "default", "-l", "app.kubernetes.io/name=benchmark-app", "-o", "json") -Path (Join-Path $runDirectory "pods-after.json")
    Save-CommandJson -Arguments @("get", "endpointslices", "-n", "default", "-l", "kubernetes.io/service-name=benchmark-app", "-o", "json") -Path (Join-Path $runDirectory "endpoints-after.json")

    $maxMeanCpu = ($resourceSummary.MeanCpuMillicores | Measure-Object -Maximum).Maximum
    $maxMeanThrottle = ($resourceSummary.MeanThrottlePct | Measure-Object -Maximum).Maximum
    $observedPodCount = @($client.serving_pods.psobject.Properties).Count
    $pass = (
        $client.p99_ms -le 300 -and
        $client.failure_rate -lt 0.01 -and
        $client.measurement_throughput_rps -ge ($Rate * 0.99) -and
        $maxMeanCpu -le 450 -and
        $maxMeanThrottle -lt 10 -and
        $observedPodCount -eq $Replicas -and
        -not $readinessViolation
    )

    [ordered]@{
        campaign_id = $campaignId
        run_id = $runId
        environment = "anfa-cloud"
        context = kubectl config current-context
        replicas = $Replicas
        target_rps = $Rate
        duration_seconds = $DurationSeconds
        repetition = $repetition
        start_utc = $trialStartUtc.ToString("o")
        end_utc = $trialEndUtc.ToString("o")
        readiness_violation = $readinessViolation
        pass = $pass
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDirectory "metadata.json") -Encoding utf8

    $trialResult = [pscustomobject]@{
        Repetition = $repetition
        Completed = $client.completed
        Errors = $client.errors
        AchievedRps = $client.measurement_throughput_rps
        P50ms = $client.p50_ms
        P95ms = $client.p95_ms
        P99ms = $client.p99_ms
        ObservedPods = $observedPodCount
        MaxMeanCpuM = [math]::Round($maxMeanCpu, 2)
        MaxMeanThrottlePct = [math]::Round($maxMeanThrottle, 2)
        ReadinessViolation = $readinessViolation
        Pass = $pass
        RunDirectory = $runDirectory
    }

    $campaignResults += $trialResult
    $campaignResults | Export-Csv -LiteralPath (Join-Path $campaignDirectory "campaign-summary.csv") -NoTypeInformation
    $trialResult | Format-List

    if ($repetition -lt $Repetitions -and $RecoverySeconds -gt 0) {
        Write-Host "Recovering for $RecoverySeconds seconds..."
        Start-Sleep -Seconds $RecoverySeconds
    }
}

Write-Host "Formal campaign complete"
$campaignResults | Format-Table -AutoSize
Write-Host "Evidence directory: $campaignDirectory"
