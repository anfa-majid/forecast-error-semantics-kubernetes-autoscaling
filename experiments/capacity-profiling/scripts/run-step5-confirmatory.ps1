param(
  [int]$StartRepetition = 1,
  [int]$Repetitions = 5,
  [int]$DurationSeconds = 120,
  [int]$PointWarmupSeconds = 30,
  [int]$RecoverySeconds = 60
)

$ErrorActionPreference = "Stop"
$orders = @(
  @(55, 60, 65, 70, 75),
  @(65, 70, 75, 55, 60),
  @(75, 55, 60, 65, 70),
  @(60, 65, 70, 75, 55),
  @(70, 75, 55, 60, 65)
)

for ($rep = $StartRepetition; $rep -lt ($StartRepetition + $Repetitions); $rep++) {
  $order = $orders[($rep - 1) % $orders.Count]
  Write-Output "Starting confirmatory repetition $rep; order: $($order -join ', ')"
  & (Join-Path $PSScriptRoot "run-step5-pilot.ps1") `
    -Rates $order `
    -DurationSeconds $DurationSeconds `
    -PointWarmupSeconds $PointWarmupSeconds `
    -RecoverySeconds $RecoverySeconds `
    -RunLabel ("confirmatory-r{0:D2}" -f $rep) `
    -SkipWarmup
}
