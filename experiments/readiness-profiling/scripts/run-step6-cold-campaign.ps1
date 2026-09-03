param(
  [int]$Repetitions = 10,
  [int]$StartRepetition = 1,
  [int]$RecoverySeconds = 15,
  [int]$TimeoutSeconds = 180
)

$ErrorActionPreference="Stop"
$runner=Join-Path $PSScriptRoot "run-step6-cold-trial.ps1"
$root=Split-Path -Parent $PSScriptRoot
$progressPath=Join-Path $root "step6\cold-campaign-progress.csv"
$progress=@()
if(Test-Path $progressPath){$progress += @(Import-Csv $progressPath)}
for($rep=$StartRepetition;$rep -lt ($StartRepetition+$Repetitions);$rep++){
  $started=(Get-Date).ToUniversalTime()
  Write-Output ("Starting cold Step 6 repetition {0} at {1:o}" -f $rep,$started)
  & $runner -Repetition $rep -RecoverySeconds $RecoverySeconds -TimeoutSeconds $TimeoutSeconds
  $progress += [pscustomobject]@{repetition=$rep;started_utc=$started.ToString("o");ended_utc=(Get-Date).ToUniversalTime().ToString("o");status="valid"}
  $progress|Export-Csv -LiteralPath $progressPath -NoTypeInformation
}
Write-Output "Cold Step 6 campaign complete: $progressPath"
