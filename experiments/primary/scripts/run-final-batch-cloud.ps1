[CmdletBinding()]
param(
    [ValidateRange(1, 100)]
    [int]$MaxRuns = 10,

    [ValidateRange(10, 1440)]
    [int]$MaxWallMinutes = 180,

    [Parameter(Mandatory)][string]$ServerIp,
    [Parameter(Mandatory)][string]$Worker1Ip,
    [Parameter(Mandatory)][string]$Worker2Ip,
    [string]$SshUser = 'researcher',
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$Kubeconfig = "$env:USERPROFILE\.kube\config",
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$manager = Join-Path $root 'tools\campaign.py'
$matrixPath = Join-Path $root 'matrix\primary-execution-order.csv'
$singleRunner = Join-Path $PSScriptRoot 'run-one-final-cloud.ps1'
$logDirectory = Join-Path $root 'validation'
$stamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMdd-HHmmss')
$batchLog = Join-Path $logDirectory "batch-$stamp.log"
$batchSummary = Join-Path $logDirectory "batch-$stamp.json"
$started = [DateTimeOffset]::UtcNow
$deadline = $started.AddMinutes($MaxWallMinutes)
$completed = [System.Collections.Generic.List[object]]::new()

function Get-CampaignStatus {
    $text = & $Python $manager status
    if ($LASTEXITCODE -ne 0) { throw 'Could not read campaign state' }
    return ($text | ConvertFrom-Json)
}

function Write-BatchSummary([string]$Status, [string]$Reason) {
    $state = Get-CampaignStatus
    $document = [ordered]@{
        schema_version = '1.0.0'
        batch_started_utc = $started.ToString('o')
        batch_finished_utc = [DateTimeOffset]::UtcNow.ToString('o')
        status = $Status
        reason = $Reason
        maximum_runs = $MaxRuns
        maximum_wall_minutes = $MaxWallMinutes
        completed_runs = @($completed)
        completed_count = $completed.Count
        campaign_status = $state
        log_path = $batchLog
    }
    [IO.File]::WriteAllText(
        $batchSummary,
        ($document | ConvertTo-Json -Depth 20) + [Environment]::NewLine,
        [Text.UTF8Encoding]::new($false)
    )
}

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) { throw "Python runtime missing: $Python" }
if (-not (Test-Path -LiteralPath $singleRunner)) { throw "Single-run executor missing: $singleRunner" }
if (-not (Test-Path -LiteralPath $matrixPath)) { throw "Frozen matrix missing: $matrixPath" }
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$initial = Get-CampaignStatus
if ($initial.active_attempt) { throw 'A campaign attempt is already active; batch start refused' }
if (-not $initial.paused) { throw 'Campaign must be paused before a batch starts' }
if ($initial.complete) {
    Write-BatchSummary 'complete' 'campaign_already_complete'
    Write-Host 'STEP 15 CAMPAIGN IS ALREADY COMPLETE'
    exit 0
}

$matrix = @(Import-Csv -LiteralPath $matrixPath)
$batchStatus = 'completed'
$batchReason = 'maximum_runs_reached'

try {
    for ($index = 1; $index -le $MaxRuns; $index++) {
        $state = Get-CampaignStatus
        if ($state.active_attempt) { throw 'Unexpected active attempt before batch iteration' }
        if ($state.complete -or [string]::IsNullOrWhiteSpace([string]$state.next_run_id)) {
            $batchStatus = 'complete'
            $batchReason = 'campaign_complete'
            break
        }

        $row = $matrix | Where-Object { $_.run_id -eq [string]$state.next_run_id } | Select-Object -First 1
        if (-not $row) { throw "Next campaign run is absent from frozen matrix: $($state.next_run_id)" }

        $plannedSeconds = [int]$row.planned_wall_duration_s
        $remainingSeconds = ($deadline - [DateTimeOffset]::UtcNow).TotalSeconds
        if ($remainingSeconds -lt $plannedSeconds) {
            $batchStatus = 'completed'
            $batchReason = 'wall_time_budget_reached_before_next_run'
            Write-Host "BATCH STOPPED BEFORE $($row.run_id): planned $plannedSeconds seconds, remaining $([math]::Floor($remainingSeconds)) seconds"
            break
        }

        $before = Get-CampaignStatus
        $runStarted = [DateTimeOffset]::UtcNow
        Write-Host "[$index/$MaxRuns] STARTING $($row.run_id) (sequence $($row.step15_sequence), planned $plannedSeconds seconds)"

        & $singleRunner `
            -RunId $row.run_id `
            -ServerIp $ServerIp `
            -Worker1Ip $Worker1Ip `
            -Worker2Ip $Worker2Ip `
            -SshUser $SshUser `
            -SshKeyPath $SshKeyPath `
            -Kubeconfig $Kubeconfig `
            -Python $Python 2>&1 | Tee-Object -FilePath $batchLog -Append

        if ($LASTEXITCODE -ne 0) { throw "Run executor failed for $($row.run_id)" }

        $after = Get-CampaignStatus
        if ($after.active_attempt) { throw "Run left an active attempt: $($row.run_id)" }
        if (-not $after.paused) { throw "Campaign did not pause after run: $($row.run_id)" }
        if ([int]$after.counts.valid -ne ([int]$before.counts.valid + 1)) {
            throw "Run was not finalized valid: $($row.run_id)"
        }

        $completed.Add([ordered]@{
            run_id = $row.run_id
            step15_sequence = [int]$row.step15_sequence
            started_utc = $runStarted.ToString('o')
            finished_utc = [DateTimeOffset]::UtcNow.ToString('o')
            result = 'valid'
        })
        Write-Host "[$index/$MaxRuns] VALID: $($row.run_id)"
    }
}
catch {
    $batchStatus = 'stopped_on_failure'
    $batchReason = $_.Exception.Message
    Write-BatchSummary $batchStatus $batchReason
    Write-Host "STEP 15 BATCH STOPPED: $batchReason"
    Write-Host "Summary: $batchSummary"
    throw
}

Write-BatchSummary $batchStatus $batchReason
Write-Host "STEP 15 BATCH FINISHED: $($completed.Count) valid run(s)"
Write-Host "Reason: $batchReason"
Write-Host "Summary: $batchSummary"
