param(
  [int[]]$ReplicaCounts = @(2, 3, 4),
  [int]$Repetitions = 3,
  [int]$DurationSeconds = 120,
  [int]$PointWarmupSeconds = 30,
  [int]$RecoverySeconds = 60
)

$ErrorActionPreference = "Stop"
$rates = @{
  2 = @(81, 90, 99)
  3 = @(122, 135, 149)
  4 = @(162, 180, 198)
}

foreach ($replicas in $ReplicaCounts) {
  if (!$rates.ContainsKey($replicas)) { throw "No pre-registered rates for $replicas replicas" }
  for ($rep = 1; $rep -le $Repetitions; $rep++) {
    $base = @($rates[$replicas])
    $offset = ($rep - 1) % $base.Count
    $order = @($base[$offset..($base.Count - 1)] + $base[0..($offset - 1)])
    if ($offset -eq 0) { $order = $base }
    Write-Output "Starting $replicas-Pod repetition $rep; order: $($order -join ', ')"
    & (Join-Path $PSScriptRoot "run-step5-pilot.ps1") `
      -Replicas $replicas `
      -Rates $order `
      -DurationSeconds $DurationSeconds `
      -PointWarmupSeconds $PointWarmupSeconds `
      -RecoverySeconds $RecoverySeconds `
      -RunLabel ("multipod-n{0}-r{1:D2}" -f $replicas, $rep) `
      -SkipWarmup
  }
}
