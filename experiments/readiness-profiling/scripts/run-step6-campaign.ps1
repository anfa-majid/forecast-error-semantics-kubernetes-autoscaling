param(
  [int]$Repetitions = 10,
  [int]$StartRepetition = 1,
  [int]$RecoverySeconds = 15,
  [int]$TimeoutSeconds = 180,
  [string]$RunLabel = "cached-main"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run-step6-actuation.ps1"
$root = Split-Path -Parent $PSScriptRoot
$progressPath = Join-Path $root "step6\campaign-progress.csv"
$progress = if(Test-Path -LiteralPath $progressPath){@(Import-Csv -LiteralPath $progressPath)}else{@()}

for($rep=$StartRepetition; $rep -lt ($StartRepetition+$Repetitions); $rep++) {
  # Latin-style rotation reduces systematic time and thermal bias.
  switch(($rep-1) % 3) {
    0 { $order=@(2,3,4) }
    1 { $order=@(3,4,2) }
    2 { $order=@(4,2,3) }
  }
  foreach($target in $order) {
    $started=(Get-Date).ToUniversalTime()
    Write-Output ("Starting Step 6 repetition {0}, scale 1->{1} at {2:o}" -f $rep,$target,$started)
    try {
      & $runner -TargetReplicas $target -Repetition $rep -RecoverySeconds $RecoverySeconds -TimeoutSeconds $TimeoutSeconds -RunLabel $RunLabel
      $status="valid"
      $reason=""
    } catch {
      $status="invalid"
      $reason=$_.Exception.Message
    }
    $progress += [pscustomobject]@{repetition=$rep;target_replicas=$target;increment=($target-1);started_utc=$started.ToString("o");ended_utc=(Get-Date).ToUniversalTime().ToString("o");status=$status;reason=$reason}
    $progress | Export-Csv -LiteralPath $progressPath -NoTypeInformation
    if($status -ne "valid") { throw "Campaign stopped after invalid trial: repetition $rep, target ${target}: $reason" }
  }
}
Write-Output "Step 6 campaign block complete: $progressPath"
