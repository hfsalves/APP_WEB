[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Server', 'Dev', 'ProdLike', 'Local')]
    [string]$Mode = 'Server',

    [string]$TaskName = 'StationZero Startup',
    [switch]$InstallRequirements
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot 'start_stationzero.ps1'

if (-not (Test-Path $scriptPath)) {
    throw "Script de arranque nao encontrado: $scriptPath"
}

$extra = if ($InstallRequirements) { ' -InstallRequirements' } else { '' }
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Mode $Mode$extra"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argument -WorkingDirectory (Split-Path -Parent $scriptPath)
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Tarefa agendada criada: $TaskName"
Write-Host "Modo configurado: $Mode"
Write-Host "Script: $scriptPath"
