[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Dev', 'ProdLike', 'Server', 'Local')]
    [string]$Mode = 'Auto',

    [switch]$NoNginx,
    [switch]$NoUpdate,
    [switch]$InstallRequirements,
    [int]$DelaySeconds = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'stationzero_common.ps1')

$resolvedMode = Resolve-StationZeroMode -Mode $Mode -ForStatus
$config = Get-StationZeroModeConfig -Mode $resolvedMode

if ($resolvedMode -eq 'Server' -and -not $NoUpdate) {
    $updateOk = Invoke-StationZeroServerUpdate -InstallRequirements:$InstallRequirements
    if (-not $updateOk) {
        $message = 'Update do codigo falhou. Restart abortado; instancia atual mantida.'
        Write-StationZeroLog -Kind control -Message $message
        throw $message
    }
}

Stop-StationZeroMode -Config $config | Out-Null
Start-Sleep -Seconds $DelaySeconds
$result = Start-StationZeroMode -Config $config -NoNginx:$NoNginx

if ($result.AlreadyRunning) {
    Write-Host "$($config.Mode) ja estava ativo."
} else {
    Write-Host "$($config.Mode) reiniciado com sucesso na porta $($config.Port)."
}
