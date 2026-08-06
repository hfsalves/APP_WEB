[CmdletBinding()]
param(
    [string]$OperatorAccount = "$env:USERDOMAIN\$env:USERNAME",
    [string]$NssmUrl = 'https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$logs = Join-Path $root 'logs'
$runtimeRoot = Join-Path $env:ProgramData 'SZero'
$runtimeBin = Join-Path $runtimeRoot 'bin'
$nssmExe = Join-Path $runtimeBin 'nssm.exe'
$nginxExe = 'C:\nginx\nginx.exe'
$waitressExe = Join-Path $root '.venv\Scripts\waitress-serve.exe'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Executa este instalador numa PowerShell aberta como administrador.'
}

foreach ($path in @($logs, $runtimeRoot, $runtimeBin)) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

foreach ($required in @($nginxExe, $waitressExe)) {
    if (-not (Test-Path $required)) {
        throw "Executavel nao encontrado: $required"
    }
}

if (-not (Test-Path $nssmExe)) {
    $archive = Join-Path $env:TEMP 'szero-nssm.zip'
    $extract = Join-Path $env:TEMP 'szero-nssm'
    Invoke-WebRequest -Uri $NssmUrl -OutFile $archive -UseBasicParsing
    if (Test-Path $extract) {
        Remove-Item $extract -Recurse -Force
    }
    Expand-Archive -Path $archive -DestinationPath $extract -Force
    $downloadedExe = Get-ChildItem $extract -Filter nssm.exe -Recurse |
        Where-Object { $_.FullName -match '[\\/]win64[\\/]' } |
        Select-Object -First 1
    if (-not $downloadedExe) {
        throw 'nssm.exe de 64 bits nao encontrado no arquivo descarregado.'
    }
    Copy-Item $downloadedExe.FullName $nssmExe -Force
}

function Invoke-Nssm {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & $nssmExe @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "NSSM falhou: $($Arguments -join ' ')"
    }
}

function Remove-ServiceIfPresent {
    param([Parameter(Mandatory = $true)][string]$Name)

    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $service) {
        return
    }
    if ($service.Status -ne 'Stopped') {
        Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }
    Invoke-Nssm remove $Name confirm
}

function Set-ServiceControlPermission {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Account
    )

    $sid = ([Security.Principal.NTAccount]$Account).Translate(
        [Security.Principal.SecurityIdentifier]
    ).Value
    $sddl = (& sc.exe sdshow $Name | Where-Object { $_ -match '^D:' } | Select-Object -First 1).Trim()
    if (-not $sddl) {
        throw "Nao foi possivel ler as permissoes do servico $Name."
    }
    if ($sddl.Contains($sid)) {
        return
    }

    $ace = "(A;;LCRPWPLO;;;$sid)"
    $auditIndex = $sddl.IndexOf('S:')
    if ($auditIndex -ge 0) {
        $sddl = $sddl.Insert($auditIndex, $ace)
    } else {
        $sddl += $ace
    }
    & sc.exe sdset $Name $sddl | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel atribuir controlo de $Name a $Account."
    }
}

$startupTask = Get-ScheduledTask -TaskName 'StationZero Startup' -ErrorAction SilentlyContinue
if ($startupTask) {
    Stop-ScheduledTask -TaskName 'StationZero Startup' -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName 'StationZero Startup' -Confirm:$false
}

. (Join-Path $PSScriptRoot 'stationzero_common.ps1')
$serverConfig = Get-StationZeroModeConfig -Mode Server
Stop-StationZeroMode -Config $serverConfig -IncludeNginx | Out-Null
Get-Process -Name nginx -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Remove-ServiceIfPresent -Name 'SZeroWaitress'
Remove-ServiceIfPresent -Name 'SZeroNginx'

Invoke-Nssm install SZeroNginx $nginxExe
Invoke-Nssm set SZeroNginx AppDirectory 'C:\nginx'
Invoke-Nssm set SZeroNginx DisplayName 'SZero Nginx'
Invoke-Nssm set SZeroNginx Description 'Reverse proxy do StationZero.'
Invoke-Nssm set SZeroNginx Start SERVICE_AUTO_START
Invoke-Nssm set SZeroNginx AppExit Default Restart
Invoke-Nssm set SZeroNginx AppRestartDelay 5000
Invoke-Nssm set SZeroNginx AppStdout (Join-Path $logs 'szero-nginx-service.out.log')
Invoke-Nssm set SZeroNginx AppStderr (Join-Path $logs 'szero-nginx-service.err.log')
Invoke-Nssm set SZeroNginx AppRotateFiles 1
Invoke-Nssm set SZeroNginx AppRotateOnline 1
Invoke-Nssm set SZeroNginx AppRotateBytes 10485760

Invoke-Nssm install SZeroWaitress $waitressExe '--host=0.0.0.0' '--port=8000' 'app:app'
Invoke-Nssm set SZeroWaitress AppDirectory $root
Invoke-Nssm set SZeroWaitress DisplayName 'SZero Waitress'
Invoke-Nssm set SZeroWaitress Description 'Servidor web Python do StationZero.'
Invoke-Nssm set SZeroWaitress Start SERVICE_AUTO_START
Invoke-Nssm set SZeroWaitress AppExit Default Restart
Invoke-Nssm set SZeroWaitress AppRestartDelay 5000
Invoke-Nssm set SZeroWaitress AppStdout (Join-Path $logs 'szero-waitress-service.out.log')
Invoke-Nssm set SZeroWaitress AppStderr (Join-Path $logs 'szero-waitress-service.err.log')
Invoke-Nssm set SZeroWaitress AppRotateFiles 1
Invoke-Nssm set SZeroWaitress AppRotateOnline 1
Invoke-Nssm set SZeroWaitress AppRotateBytes 10485760

& sc.exe config SZeroWaitress depend= SZeroNginx | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'Nao foi possivel configurar a dependencia do SZeroWaitress.'
}

Set-ServiceControlPermission -Name 'SZeroNginx' -Account $OperatorAccount
Set-ServiceControlPermission -Name 'SZeroWaitress' -Account $OperatorAccount

Start-Service -Name 'SZeroNginx'
(Get-Service -Name 'SZeroNginx').WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
Start-Service -Name 'SZeroWaitress'
(Get-Service -Name 'SZeroWaitress').WaitForStatus('Running', [TimeSpan]::FromSeconds(90))

if (-not (Wait-StationZeroPortState -Port 8000 -ShouldListen $true -TimeoutSeconds 90)) {
    throw 'SZeroWaitress arrancou, mas a porta 8000 nao ficou a escutar.'
}

Write-Host 'Servicos instalados e ativos:'
Write-Host '  SZeroNginx'
Write-Host '  SZeroWaitress'
Write-Host "Operador autorizado: $OperatorAccount"
