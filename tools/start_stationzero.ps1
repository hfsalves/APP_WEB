[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Dev', 'ProdLike', 'Server', 'Local')]
    [string]$Mode = 'Auto',

    [switch]$Foreground,
    [switch]$NoNginx,
    [switch]$NoUpdate,
    [switch]$InstallRequirements
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'stationzero_common.ps1')

$resolvedMode = Resolve-StationZeroMode -Mode $Mode
$config = Get-StationZeroModeConfig -Mode $resolvedMode

$alreadyRunning = @(Get-StationZeroModeProcesses -Config $config).Count -gt 0 -and (Test-StationZeroPortListening -Port $config.Port)
$portOwner = Get-StationZeroPortOwnerProcess -Port $config.Port
if ($portOwner -and -not (Test-StationZeroRootMatch -Process $portOwner)) {
    $message = "Porta $($config.Port) ocupada por processo nao relacionado: PID $($portOwner.ProcessId) [$($portOwner.Name)]."
    Write-StationZeroLog -Kind control -Message $message
    throw $message
}

if ($resolvedMode -eq 'Server' -and -not $NoUpdate -and -not $alreadyRunning) {
    $updateOk = Invoke-StationZeroServerUpdate -InstallRequirements:$InstallRequirements
    if (-not $updateOk) {
        $message = 'Update do codigo falhou. Arranque abortado.'
        Write-StationZeroLog -Kind control -Message $message
        throw $message
    }
}

$result = Start-StationZeroMode -Config $config -Foreground:$Foreground -NoNginx:$NoNginx

if ($result.AlreadyRunning) {
    Write-Host "$($config.Mode) ja estava ativo na porta $($config.Port)."
} else {
    Write-Host "$($config.Mode) iniciado na porta $($config.Port)."
}
