[CmdletBinding()]
param(
    [string]$NginxRoot = 'C:\nginx',
    [string]$ConfigPath = 'C:\nginx\conf\nginx.conf'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Executa este instalador numa PowerShell aberta como administrador.'
}

$nginxExe = Join-Path $NginxRoot 'nginx.exe'
$snippetPath = Join-Path $PSScriptRoot 'nginx_gr360_ticket_mcp_location.conf'
foreach ($required in @($nginxExe, $ConfigPath, $snippetPath)) {
    if (-not (Test-Path $required)) {
        throw "Ficheiro necessario nao encontrado: $required"
    }
}

$content = [System.IO.File]::ReadAllText($ConfigPath)
if ($content -match 'location\s+/mcp/gr360-tickets/') {
    Write-Host 'A rota Nginx do GR360 Tickets MCP ja esta configurada.'
    exit 0
}

if ($content -notmatch 'server_name\s+app\.gr360flooringsystems\.com\s*;') {
    throw 'Bloco server de app.gr360flooringsystems.com nao encontrado. Nenhuma alteracao efetuada.'
}

$locationPattern = '(?m)^(?<indent>\s*)location\s+/\s*\{'
$locationMatch = [regex]::Match($content, $locationPattern)
if (-not $locationMatch.Success) {
    throw 'Bloco location / nao encontrado. Nenhuma alteracao efetuada.'
}

$indent = $locationMatch.Groups['indent'].Value
$snippetLines = [System.IO.File]::ReadAllLines($snippetPath) | Where-Object {
    -not $_.TrimStart().StartsWith('# Inserir dentro')
}
$indentedSnippet = ($snippetLines | ForEach-Object {
    if ($_.Length -gt 0) { "$indent$_" } else { '' }
}) -join [Environment]::NewLine

$updated = $content.Insert(
    $locationMatch.Index,
    $indentedSnippet + [Environment]::NewLine + [Environment]::NewLine
)
$backupPath = "$ConfigPath.$(Get-Date -Format 'yyyyMMdd-HHmmss').bak"
Copy-Item $ConfigPath $backupPath -Force

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($ConfigPath, $updated, $utf8NoBom)

function Restart-Gr360Nginx {
    $service = Get-Service -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -eq 'GR360 Nginx' -or $_.DisplayName -eq 'GR360 Nginx'
    } | Select-Object -First 1

    if ($service) {
        Restart-Service -Name $service.Name -Force -ErrorAction Stop
        (Get-Service -Name $service.Name).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
        return
    }

    & $nginxExe -s reload
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel recarregar o Nginx e o servico GR360 Nginx nao foi encontrado.'
    }
}

Push-Location $NginxRoot
try {
    & $nginxExe -t
    if ($LASTEXITCODE -ne 0) {
        throw 'Validacao Nginx falhou.'
    }

    Restart-Gr360Nginx
} catch {
    $failure = $_.Exception.Message
    Copy-Item $backupPath $ConfigPath -Force
    try {
        Restart-Gr360Nginx
    } catch {
        throw "$failure Configuracao original reposta de $backupPath, mas o reinicio do Nginx tambem falhou: $($_.Exception.Message)"
    }
    throw "$failure Configuracao original reposta de $backupPath."
} finally {
    Pop-Location
}

Write-Host 'Rota /mcp/gr360-tickets/ instalada e servico GR360 Nginx reiniciado com sucesso.'
Write-Host "Backup: $backupPath"
