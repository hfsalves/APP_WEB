[CmdletBinding()]
param(
    [string]$TaskName = 'StationZero Startup'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
Write-Host "Tarefa removida: $TaskName"
