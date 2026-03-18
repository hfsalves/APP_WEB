[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Dev', 'ProdLike', 'Server', 'Local')]
    [string]$Mode = 'Auto'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'stationzero_common.ps1')

$status = Get-StationZeroStatus -Mode $Mode

$status.AppModes | Format-Table Mode, Host, Port, Running, ProcessIds, PortOwner -AutoSize

if ($status.NginxRunning) {
    Write-Host "nginx: ativo (PID $($status.NginxProcessId))"
} else {
    Write-Host 'nginx: inativo'
}

Write-Host "control log: $($status.ControlLog)"
Write-Host "status log:  $($status.StatusLog)"
Write-Host "update log:  $($status.UpdateLog)"
Write-Host "nginx logs:  $($status.NginxLogs)"
