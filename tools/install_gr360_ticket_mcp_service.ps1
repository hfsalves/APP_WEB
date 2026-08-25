[CmdletBinding()]
param(
    [string]$ServiceName = 'GR360TicketsMCP',
    [string]$DisplayName = 'GR360 Tickets MCP',
    [int]$Port = 8002,
    [string]$ApiBaseUrl = 'http://127.0.0.1:8000/api/gr360/tickets',
    [string]$PublicHost = 'app.gr360flooringsystems.com',
    [string]$NssmUrl = 'https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Executa este instalador numa PowerShell aberta como administrador.'
}

$root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$logs = Join-Path $root 'logs'
$requirements = Join-Path $root 'requirements-mcp.txt'
$entryPoint = Join-Path $root 'gr360_ticket_mcp_server.py'
$runtimeRoot = Join-Path $env:ProgramData 'SZero'
$runtimeBin = Join-Path $runtimeRoot 'bin'
$nssmExe = Join-Path $runtimeBin 'nssm.exe'

$venvRoot = $null
foreach ($candidateName in @('.venv', 'venv')) {
    $candidateRoot = Join-Path $root $candidateName
    if (Test-Path (Join-Path $candidateRoot 'Scripts\python.exe')) {
        $venvRoot = $candidateRoot
        break
    }
}
if (-not $venvRoot) {
    throw 'Ambiente virtual Python nao encontrado (.venv ou venv).'
}
$pythonExe = Join-Path $venvRoot 'Scripts\python.exe'

foreach ($path in @($logs, $runtimeRoot, $runtimeBin)) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
foreach ($required in @($pythonExe, $requirements, $entryPoint)) {
    if (-not (Test-Path $required)) {
        throw "Ficheiro necessario nao encontrado: $required"
    }
}

& $pythonExe -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao instalar as dependencias exclusivas do MCP.'
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

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -ne 'Stopped') {
        Stop-Service -Name $ServiceName -Force
        $existing.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }
    Invoke-Nssm remove $ServiceName confirm
}

Invoke-Nssm install $ServiceName $pythonExe $entryPoint
Invoke-Nssm set $ServiceName AppDirectory $root
Invoke-Nssm set $ServiceName DisplayName $DisplayName
Invoke-Nssm set $ServiceName Description 'Conector MCP isolado para os tickets GR360.'
Invoke-Nssm set $ServiceName Start SERVICE_AUTO_START
Invoke-Nssm set $ServiceName AppExit Default Restart
Invoke-Nssm set $ServiceName AppRestartDelay 5000
Invoke-Nssm set $ServiceName AppEnvironmentExtra `
    "GR360_TICKET_MCP_LISTEN_HOST=127.0.0.1" `
    "GR360_TICKET_MCP_PORT=$Port" `
    "GR360_TICKET_MCP_API_URL=$ApiBaseUrl" `
    "GR360_TICKET_MCP_PUBLIC_HOST=$PublicHost"
Invoke-Nssm set $ServiceName AppStdout (Join-Path $logs 'gr360-ticket-mcp-service.out.log')
Invoke-Nssm set $ServiceName AppStderr (Join-Path $logs 'gr360-ticket-mcp-service.err.log')
Invoke-Nssm set $ServiceName AppRotateFiles 1
Invoke-Nssm set $ServiceName AppRotateOnline 1
Invoke-Nssm set $ServiceName AppRotateBytes 10485760

Start-Service -Name $ServiceName
(Get-Service -Name $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))

$deadline = (Get-Date).AddSeconds(30)
do {
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        break
    }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

if (-not $listening) {
    throw "O servico arrancou, mas a porta local $Port nao ficou a escutar."
}

Write-Host "$DisplayName instalado, Automatic e Running em 127.0.0.1:$Port."
Write-Host 'Os servicos GR360 Application e GR360 Nginx nao foram alterados.'
