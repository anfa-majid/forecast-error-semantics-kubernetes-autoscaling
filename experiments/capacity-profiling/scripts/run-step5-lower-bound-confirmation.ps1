param(
  [int]$Rate = 50,
  [int]$Repetitions = 5,
  [int]$DurationSeconds = 120,
  [int]$PointWarmupSeconds = 30,
  [int]$RecoverySeconds = 60
)

$ErrorActionPreference = "Stop"

for ($rep = 1; $rep -le $Repetitions; $rep++) {
  Write-Output "Starting lower-bound confirmation $rep of $Repetitions at $Rate RPS"
  & (Join-Path $PSScriptRoot "run-step5-pilot.ps1") `
    -Rates @($Rate) `
    -DurationSeconds $DurationSeconds `
    -PointWarmupSeconds $PointWarmupSeconds `
    -RecoverySeconds $RecoverySeconds `
    -RunLabel ("confirmatory-lower-{0:D3}-r{1:D2}" -f $Rate, $rep) `
    -SkipWarmup
}
