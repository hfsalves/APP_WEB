[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Dev', 'ProdLike', 'Server', 'Local')]
    [string]$Mode = 'Auto',

    [switch]$IncludeNginx
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'stationzero_common.ps1')

$targetModes = @()
if ((Normalize-StationZeroMode -Mode $Mode) -eq 'Auto') {
    if (Test-Path $script:StationZeroConfig.NginxExe) {
        $targetModes = @('Server')
    } else {
        $targetModes = @('Dev', 'ProdLike')
    }
} else {
    $targetModes = @((Resolve-StationZeroMode -Mode $Mode -ForStatus))
}

$stoppedAny = $false
foreach ($modeName in $targetModes) {
    $config = Get-StationZeroModeConfig -Mode $modeName
    $result = Stop-StationZeroMode -Config $config -IncludeNginx:$IncludeNginx
    if ($result.Stopped) {
        $stoppedAny = $true
        Write-Host "$($config.Mode) parado."
    } else {
        Write-Host "$($config.Mode) sem processos ativos."
    }
}

if (-not $stoppedAny) {
    Write-Host 'Nenhuma instancia StationZero estava ativa.'
}
