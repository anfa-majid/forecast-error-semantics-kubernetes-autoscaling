param(
  [Parameter(Mandatory=$true)][int]$Replicas,
  [Parameter(Mandatory=$true)][int[]]$Rates,
  [int]$Repetitions = 3,
  [int]$DurationSeconds = 120,
  [int]$PointWarmupSeconds = 30,
  [int]$RecoverySeconds = 60,
  [string]$Label = "adaptive"
)

$ErrorActionPreference = "Stop"
if ($Rates.Count -lt 1) { throw "At least one rate is required" }

for ($rep = 1; $rep -le $Repetitions; $rep++) {
  $offset = ($rep - 1) % $Rates.Count
  if ($offset -eq 0) {
    $order = @($Rates)
  } else {
    $order = @($Rates[$offset..($Rates.Count - 1)] + $Rates[0..($offset - 1)])
  }
  Write-Output "Starting adaptive $Replicas-Pod repetition $rep; order: $($order -join ', ')"
  & (Join-Path $PSScriptRoot "run-step5-pilot.ps1") `
    -Replicas $Replicas `
    -Rates $order `
    -DurationSeconds $DurationSeconds `
    -PointWarmupSeconds $PointWarmupSeconds `
    -RecoverySeconds $RecoverySeconds `
    -RunLabel ("multipod-{0}-n{1}-r{2:D2}" -f $Label, $Replicas, $rep) `
    -SkipWarmup
}
