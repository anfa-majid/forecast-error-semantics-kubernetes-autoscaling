param(
    [Parameter(Mandatory = $true)][string]$ServerIp,
    [Parameter(Mandatory = $true)][string]$SshKeyPath,
    [string]$SshUser = "researcher",
    [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) "step6\cloud\runs"),
    [int]$Repetitions = 10,
    [int]$StartRepetition = 1,
    [int]$RecoverySeconds = 15,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$ProgressPath = Join-Path (Split-Path $OutputRoot -Parent) "campaign-progress.csv"
$EvidenceFiles = @(
    "trial-summary.json",
    "per-pod.csv",
    "service-probe.csv",
    "pods-baseline.json",
    "pods-final.json",
    "deployment-final.json",
    "events-final.json"
)

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$Progress = [System.Collections.ArrayList]::new()
if (Test-Path -LiteralPath $ProgressPath) {
    foreach ($ExistingRow in @(Import-Csv -LiteralPath $ProgressPath)) {
        [void]$Progress.Add($ExistingRow)
    }
}

for ($Repetition = $StartRepetition; $Repetition -lt ($StartRepetition + $Repetitions); $Repetition++) {
    switch (($Repetition - 1) % 3) {
        0 { $Order = @(2, 3, 4) }
        1 { $Order = @(3, 4, 2) }
        2 { $Order = @(4, 2, 3) }
    }

    foreach ($Target in $Order) {
        $CompletedRow = @(
            $Progress | Where-Object {
                [int]$_.repetition -eq $Repetition -and
                [int]$_.target_replicas -eq $Target -and
                $_.status -eq "valid"
            }
        ) | Select-Object -First 1
        if ($CompletedRow) {
            Write-Host "Skipping completed repetition $Repetition, scale 1->$Target"
            continue
        }

        $RecoveredRun = Get-ChildItem -LiteralPath $OutputRoot -Directory |
            Where-Object { $_.Name -like ("cloud-cached-1to{0}-rep{1:D2}-*" -f $Target, $Repetition) } |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1
        if ($RecoveredRun) {
            $RecoveredSummaryPath = Join-Path $RecoveredRun.FullName "trial-summary.json"
            if (Test-Path -LiteralPath $RecoveredSummaryPath) {
                $RecoveredSummary = Get-Content -LiteralPath $RecoveredSummaryPath -Raw | ConvertFrom-Json
                if ($RecoveredSummary.valid) {
                    [void]$Progress.Add([PSCustomObject]@{
                        repetition = $Repetition
                        target_replicas = $Target
                        increment = $Target - 1
                        started_utc = $RecoveredRun.CreationTimeUtc.ToString("o")
                        ended_utc = $RecoveredRun.LastWriteTimeUtc.ToString("o")
                        status = "valid"
                        reason = "recovered from downloaded evidence after progress-write interruption"
                        readiness_delay_s = $RecoveredSummary.trial_readiness_delay_s
                        effective_serving_delay_s = $RecoveredSummary.trial_effective_serving_delay_s
                        maximum_probe_gap_ms = $RecoveredSummary.probe_max_observed_gap_ms
                        run_directory = $RecoveredRun.FullName
                    })
                    $Progress | Export-Csv -LiteralPath $ProgressPath -NoTypeInformation
                    Write-Host "Recovered completed repetition $Repetition, scale 1->$Target"
                    continue
                }
            }
        }

        $StartedUtc = [DateTimeOffset]::UtcNow
        $RunName = "cloud-cached-1to{0}-rep{1:D2}-{2}" -f `
            $Target, $Repetition, (Get-Date -Format "yyyyMMdd-HHmmss")
        $RemoteDirectory = "/tmp/$RunName"
        $LocalDirectory = Join-Path $OutputRoot $RunName
        New-Item -ItemType Directory -Force -Path $LocalDirectory | Out-Null

        Write-Host ""
        Write-Host "Starting repetition $Repetition, scale 1->$Target"

        try {
            $RunnerOutput = @(
                ssh -i $SshKeyPath `
                    "${SshUser}@$ServerIp" `
                    "python3 -B /usr/local/bin/anfa-step6-runner --target-replicas $Target --repetition $Repetition --output $RemoteDirectory --recovery $RecoverySeconds --poll-ms 100 --timeout $TimeoutSeconds"
            )

            if ($LASTEXITCODE -ne 0) {
                throw "Remote runner returned exit code $LASTEXITCODE"
            }

            $RunnerOutput | Set-Content `
                -LiteralPath (Join-Path $LocalDirectory "runner-stdout.txt") `
                -Encoding utf8

            foreach ($EvidenceFile in $EvidenceFiles) {
                $LocalPath = Join-Path $LocalDirectory $EvidenceFile
                scp -i $SshKeyPath `
                    "${SshUser}@${ServerIp}:${RemoteDirectory}/${EvidenceFile}" `
                    "$LocalPath"
                if ($LASTEXITCODE -ne 0) {
                    throw "Evidence download failed: $EvidenceFile"
                }
            }

            $Summary = Get-Content `
                -LiteralPath (Join-Path $LocalDirectory "trial-summary.json") `
                -Raw | ConvertFrom-Json

            if (-not $Summary.valid) {
                throw "Runner produced an invalid summary"
            }

            $Status = "valid"
            $Reason = ""
            $ReadyDelay = $Summary.trial_readiness_delay_s
            $ServingDelay = $Summary.trial_effective_serving_delay_s
            $ProbeGap = $Summary.probe_max_observed_gap_ms

            [PSCustomObject]@{
                Repetition = $Repetition
                TargetReplicas = $Target
                ReadinessSeconds = $ReadyDelay
                ServingSeconds = $ServingDelay
                ProbeAttempts = $Summary.probe_attempts
                MaximumProbeGapMs = $ProbeGap
                RunDirectory = $LocalDirectory
            } | Format-List
        }
        catch {
            $Status = "invalid"
            $Reason = $_.Exception.Message
            $ReadyDelay = $null
            $ServingDelay = $null
            $ProbeGap = $null
        }

        [void]$Progress.Add([PSCustomObject]@{
            repetition = $Repetition
            target_replicas = $Target
            increment = $Target - 1
            started_utc = $StartedUtc.ToString("o")
            ended_utc = [DateTimeOffset]::UtcNow.ToString("o")
            status = $Status
            reason = $Reason
            readiness_delay_s = $ReadyDelay
            effective_serving_delay_s = $ServingDelay
            maximum_probe_gap_ms = $ProbeGap
            run_directory = $LocalDirectory
        })
        $Progress | Export-Csv -LiteralPath $ProgressPath -NoTypeInformation

        if ($Status -ne "valid") {
            throw "Campaign stopped after invalid trial: repetition $Repetition, target ${Target}: $Reason"
        }
    }
}

Write-Host ""
Write-Host "Step 6 cloud campaign block complete"
Write-Host "Progress: $ProgressPath"
