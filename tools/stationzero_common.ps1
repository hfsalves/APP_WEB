[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:StationZeroRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$script:StationZeroLogs = Join-Path $script:StationZeroRoot 'logs'
$script:StationZeroRun = Join-Path $script:StationZeroLogs 'run'
$script:StationZeroRootLower = $script:StationZeroRoot.ToLowerInvariant()
$script:StationZeroConfig = @{
    PythonExe   = Join-Path $script:StationZeroRoot '.venv\Scripts\python.exe'
    WaitressExe = Join-Path $script:StationZeroRoot '.venv\Scripts\waitress-serve.exe'
    Requirements = Join-Path $script:StationZeroRoot 'requirements.txt'
    NginxExe    = 'C:\nginx\nginx.exe'
    NginxLogs   = 'C:\nginx\logs'
    GitBranch   = 'origin/master'
    DevPort     = 5000
    ProdLikePort = 8000
    ServerPort  = 8000
}

function Ensure-StationZeroDirectories {
    foreach ($path in @($script:StationZeroLogs, $script:StationZeroRun)) {
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
}

function Get-StationZeroLogPath {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('control', 'status', 'update')]
        [string]$Kind
    )

    Ensure-StationZeroDirectories
    switch ($Kind) {
        'control' { return (Join-Path $script:StationZeroLogs 'stationzero-control.log') }
        'status'  { return (Join-Path $script:StationZeroLogs 'stationzero-status.log') }
        'update'  { return (Join-Path $script:StationZeroLogs 'stationzero-update.log') }
    }
}

function ConvertTo-StationZeroSafeString {
    param($Value)

    if ($null -eq $Value) {
        return ''
    }

    return [string]$Value
}

function Write-StationZeroLog {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet('control', 'status', 'update')][string]$Kind = 'control'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path (Get-StationZeroLogPath -Kind $Kind) -Value "[$timestamp] $Message"
}

function Normalize-StationZeroMode {
    param([string]$Mode)

    $value = ((ConvertTo-StationZeroSafeString $Mode) -replace '\s+', '').Trim().ToLowerInvariant()
    switch ($value) {
        'auto'     { return 'Auto' }
        'local'    { return 'Dev' }
        'dev'      { return 'Dev' }
        'prodlike' { return 'ProdLike' }
        'server'   { return 'Server' }
        default    { throw "Modo invalido: $Mode" }
    }
}

function Resolve-StationZeroMode {
    param(
        [string]$Mode = 'Auto',
        [switch]$ForStatus
    )

    if ($env:STATIONZERO_START_MODE) {
        $forced = Normalize-StationZeroMode -Mode $env:STATIONZERO_START_MODE
        if ($forced -ne 'Auto') {
            return $forced
        }
    }

    $normalized = Normalize-StationZeroMode -Mode $Mode
    if ($normalized -ne 'Auto') {
        return $normalized
    }

    if (Test-Path $script:StationZeroConfig.NginxExe) {
        return 'Server'
    }

    if ($ForStatus) {
        $dev = Get-StationZeroModeConfig -Mode 'Dev'
        $prod = Get-StationZeroModeConfig -Mode 'ProdLike'
        if (@(Get-StationZeroModeProcesses -Config $dev).Count -gt 0 -or (Test-StationZeroPortListening -Port $dev.Port)) {
            return 'Dev'
        }
        if (@(Get-StationZeroModeProcesses -Config $prod).Count -gt 0 -or (Test-StationZeroPortListening -Port $prod.Port)) {
            return 'ProdLike'
        }
    }

    return 'Dev'
}

function Get-StationZeroModeConfig {
    param([Parameter(Mandatory = $true)][string]$Mode)

    $resolved = Normalize-StationZeroMode -Mode $Mode
    switch ($resolved) {
        'Dev' {
            return @{
                Name = 'dev'
                Mode = 'Dev'
                Host = '127.0.0.1'
                Port = $script:StationZeroConfig.DevPort
                PidFile = Join-Path $script:StationZeroRun 'stationzero-dev.pid'
                StdOutLog = Join-Path $script:StationZeroLogs 'stationzero-dev.out.log'
                StdErrLog = Join-Path $script:StationZeroLogs 'stationzero-dev.err.log'
                CommandKind = 'flask'
            }
        }
        'ProdLike' {
            return @{
                Name = 'prodlike'
                Mode = 'ProdLike'
                Host = '127.0.0.1'
                Port = $script:StationZeroConfig.ProdLikePort
                PidFile = Join-Path $script:StationZeroRun 'stationzero-prodlike.pid'
                StdOutLog = Join-Path $script:StationZeroLogs 'stationzero-prodlike.out.log'
                StdErrLog = Join-Path $script:StationZeroLogs 'stationzero-prodlike.err.log'
                CommandKind = 'waitress'
            }
        }
        'Server' {
            return @{
                Name = 'server'
                Mode = 'Server'
                Host = '0.0.0.0'
                Port = $script:StationZeroConfig.ServerPort
                PidFile = Join-Path $script:StationZeroRun 'stationzero-server.pid'
                StdOutLog = Join-Path $script:StationZeroLogs 'stationzero-server.out.log'
                StdErrLog = Join-Path $script:StationZeroLogs 'stationzero-server.err.log'
                CommandKind = 'waitress'
            }
        }
        default {
            throw "Modo sem configuracao: $Mode"
        }
    }
}

function Assert-StationZeroFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "$Label nao encontrado: $Path"
    }
}

function Get-StationZeroCommandSpec {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    switch ($Config.CommandKind) {
        'flask' {
            Assert-StationZeroFile -Path $script:StationZeroConfig.PythonExe -Label 'Python do ambiente virtual'
            return @{
                FilePath = $script:StationZeroConfig.PythonExe
                Arguments = @('-m', 'flask', '--app', 'app.py', 'run', '--debug', "--host=$($Config.Host)", "--port=$($Config.Port)")
            }
        }
        'waitress' {
            Assert-StationZeroFile -Path $script:StationZeroConfig.WaitressExe -Label 'Waitress'
            return @{
                FilePath = $script:StationZeroConfig.WaitressExe
                Arguments = @("--host=$($Config.Host)", "--port=$($Config.Port)", 'app:app')
            }
        }
        default {
            throw "Tipo de comando invalido: $($Config.CommandKind)"
        }
    }
}

function Get-StationZeroProcessInventory {
    Get-CimInstance Win32_Process | ForEach-Object {
        [pscustomobject]@{
            ProcessId = [int]$_.ProcessId
            Name = [string]$_.Name
            CommandLine = ConvertTo-StationZeroSafeString $_.CommandLine
            ExecutablePath = ConvertTo-StationZeroSafeString $_.ExecutablePath
        }
    }
}

function Test-StationZeroRootMatch {
    param([Parameter(Mandatory = $true)]$Process)

    $commandLine = ConvertTo-StationZeroSafeString $Process.CommandLine
    $executable = ConvertTo-StationZeroSafeString $Process.ExecutablePath
    return $commandLine.ToLowerInvariant().Contains($script:StationZeroRootLower) -or
        $executable.ToLowerInvariant().Contains($script:StationZeroRootLower)
}

function Test-StationZeroModeSignature {
    param(
        [Parameter(Mandatory = $true)]$Process,
        [Parameter(Mandatory = $true)][hashtable]$Config
    )

    $cmd = (ConvertTo-StationZeroSafeString $Process.CommandLine).ToLowerInvariant()
    if (-not $cmd) {
        return $false
    }

    switch ($Config.Mode) {
        'Dev' {
            return $cmd.Contains('-m flask') -and
                $cmd.Contains('--app app.py') -and
                $cmd.Contains("--port=$($Config.Port)")
        }
        'ProdLike' {
            return ($cmd.Contains('waitress-serve') -or $cmd.Contains('app:app')) -and
                $cmd.Contains('--host=127.0.0.1') -and
                $cmd.Contains("--port=$($Config.Port)")
        }
        'Server' {
            return ($cmd.Contains('waitress-serve') -or $cmd.Contains('app:app')) -and
                ($cmd.Contains('--host=0.0.0.0') -or $cmd.Contains('--listen=0.0.0.0')) -and
                $cmd.Contains("--port=$($Config.Port)")
        }
        default {
            return $false
        }
    }
}

function Test-StationZeroModeProcess {
    param(
        [Parameter(Mandatory = $true)]$Process,
        [Parameter(Mandatory = $true)][hashtable]$Config
    )

    if (-not (Test-StationZeroRootMatch -Process $Process)) {
        return $false
    }

    return (Test-StationZeroModeSignature -Process $Process -Config $Config)
}

function Get-StationZeroPortListeners {
    param([int]$Port)

    try {
        return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop)
    } catch {
        return @()
    }
}

function Test-StationZeroPortListening {
    param([int]$Port)
    return (Get-StationZeroPortListeners -Port $Port).Count -gt 0
}

function Get-StationZeroPortOwnerProcess {
    param([int]$Port)

    $listener = Get-StationZeroPortListeners -Port $Port | Select-Object -First 1
    if (-not $listener) {
        return $null
    }

    $processId = [int]$listener.OwningProcess
    return Get-StationZeroProcessInventory | Where-Object { $_.ProcessId -eq $processId } | Select-Object -First 1
}

function Get-StationZeroModeProcesses {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    $matches = @(Get-StationZeroProcessInventory | Where-Object { Test-StationZeroModeProcess -Process $_ -Config $Config })
    $portOwner = Get-StationZeroPortOwnerProcess -Port $Config.Port
    if ($portOwner -and ((Test-StationZeroRootMatch -Process $portOwner) -or (Test-StationZeroModeSignature -Process $portOwner -Config $Config))) {
        if (-not ($matches | Where-Object { $_.ProcessId -eq $portOwner.ProcessId })) {
            $matches += $portOwner
        }
    }

    return @($matches | Sort-Object ProcessId -Unique)
}

function Save-StationZeroPidFile {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [Parameter(Mandatory = $true)]$Processes
    )

    $payload = [ordered]@{
        mode = $Config.Mode
        host = $Config.Host
        port = $Config.Port
        process_ids = @($Processes | ForEach-Object { [int]$_.ProcessId })
        updated_at = (Get-Date).ToString('s')
    } | ConvertTo-Json -Depth 4

    Set-Content -Path $Config.PidFile -Value $payload -Encoding UTF8
}

function Clear-StationZeroPidFile {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    if (Test-Path $Config.PidFile) {
        Remove-Item $Config.PidFile -Force
    }
}

function Wait-StationZeroPortState {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][bool]$ShouldListen,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $listening = Test-StationZeroPortListening -Port $Port
        if ($listening -eq $ShouldListen) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    return $false
}

function Get-StationZeroNginxProcess {
    if (-not (Test-Path $script:StationZeroConfig.NginxExe)) {
        return $null
    }

    return Get-StationZeroProcessInventory | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.ToLowerInvariant() -eq $script:StationZeroConfig.NginxExe.ToLowerInvariant()
    } | Select-Object -First 1
}

function Start-StationZeroNginxIfNeeded {
    param([switch]$NoNginx)

    if ($NoNginx) { return }
    if (-not (Test-Path $script:StationZeroConfig.NginxExe)) { return }

    $nginx = Get-StationZeroNginxProcess
    if ($nginx) {
        Write-StationZeroLog -Kind control -Message "Nginx ja ativo (PID $($nginx.ProcessId))."
        return
    }

    $nginxStdOut = Join-Path $script:StationZeroLogs 'nginx-bootstrap.out.log'
    $nginxStdErr = Join-Path $script:StationZeroLogs 'nginx-bootstrap.err.log'
    Start-Process -FilePath $script:StationZeroConfig.NginxExe `
        -WorkingDirectory (Split-Path -Parent $script:StationZeroConfig.NginxExe) `
        -RedirectStandardOutput $nginxStdOut `
        -RedirectStandardError $nginxStdErr | Out-Null
    Write-StationZeroLog -Kind control -Message "Nginx iniciado."
}

function Invoke-StationZeroLoggedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$LogFile
    )

    $commandText = "$Executable $($Arguments -join ' ')"
    Add-Content -Path $LogFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $commandText"

    Ensure-StationZeroDirectories
    $stdoutFile = Join-Path $script:StationZeroRun ("cmd-" + [guid]::NewGuid().ToString('N') + ".out.log")
    $stderrFile = Join-Path $script:StationZeroRun ("cmd-" + [guid]::NewGuid().ToString('N') + ".err.log")

    try {
        $proc = Start-Process -FilePath $Executable `
            -ArgumentList $Arguments `
            -WorkingDirectory $script:StationZeroRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutFile `
            -RedirectStandardError $stderrFile `
            -Wait `
            -PassThru

        if (Test-Path $stdoutFile) {
            Get-Content $stdoutFile | Out-File -FilePath $LogFile -Append -Encoding utf8
        }
        if (Test-Path $stderrFile) {
            Get-Content $stderrFile | Out-File -FilePath $LogFile -Append -Encoding utf8
        }

        return [int]$proc.ExitCode
    } finally {
        if (Test-Path $stdoutFile) { Remove-Item $stdoutFile -Force -ErrorAction SilentlyContinue }
        if (Test-Path $stderrFile) { Remove-Item $stderrFile -Force -ErrorAction SilentlyContinue }
    }
}

function Invoke-StationZeroServerUpdate {
    param([switch]$InstallRequirements)

    $logFile = Get-StationZeroLogPath -Kind update
    $git = (Get-Command git.exe -ErrorAction Stop).Source
    Write-StationZeroLog -Kind update -Message 'Inicio de update do codigo.'

    Push-Location $script:StationZeroRoot
    try {
        $fetchCode = Invoke-StationZeroLoggedCommand -Executable $git -Arguments @('fetch', 'origin') -LogFile $logFile
        if ($fetchCode -ne 0) {
            Write-StationZeroLog -Kind update -Message "Falha em git fetch origin (exit $fetchCode)."
            return $false
        }

        $resetCode = Invoke-StationZeroLoggedCommand -Executable $git -Arguments @('reset', '--hard', $script:StationZeroConfig.GitBranch) -LogFile $logFile
        if ($resetCode -ne 0) {
            Write-StationZeroLog -Kind update -Message "Falha em git reset --hard $($script:StationZeroConfig.GitBranch) (exit $resetCode)."
            return $false
        }

        if ($InstallRequirements) {
            Assert-StationZeroFile -Path $script:StationZeroConfig.PythonExe -Label 'Python do ambiente virtual'
            $pipCode = Invoke-StationZeroLoggedCommand -Executable $script:StationZeroConfig.PythonExe -Arguments @('-m', 'pip', 'install', '-r', $script:StationZeroConfig.Requirements) -LogFile $logFile
            if ($pipCode -ne 0) {
                Write-StationZeroLog -Kind update -Message "Falha em pip install -r requirements.txt (exit $pipCode)."
                return $false
            }
        }

        Write-StationZeroLog -Kind update -Message 'Update do codigo concluido com sucesso.'
        return $true
    } finally {
        Pop-Location
    }
}

function Start-StationZeroMode {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [switch]$Foreground,
        [switch]$NoNginx
    )

    Ensure-StationZeroDirectories

    $existing = @(Get-StationZeroModeProcesses -Config $Config)
    if ($existing.Count -gt 0 -and (Test-StationZeroPortListening -Port $Config.Port)) {
        Save-StationZeroPidFile -Config $Config -Processes $existing
        Write-StationZeroLog -Kind control -Message "$($Config.Mode) ja ativo na porta $($Config.Port) (PID(s): $((@($existing.ProcessId) -join ', ')))."
        return @{
            Started = $false
            AlreadyRunning = $true
            Processes = $existing
        }
    }

    $portOwner = Get-StationZeroPortOwnerProcess -Port $Config.Port
    if ($portOwner -and -not ((Test-StationZeroRootMatch -Process $portOwner) -or (Test-StationZeroModeSignature -Process $portOwner -Config $Config))) {
        $msg = "Porta $($Config.Port) ocupada por processo nao relacionado: PID $($portOwner.ProcessId) [$($portOwner.Name)]."
        Write-StationZeroLog -Kind control -Message $msg
        throw $msg
    }

    if ($Config.Mode -eq 'Server') {
        Start-StationZeroNginxIfNeeded -NoNginx:$NoNginx
    }

    $command = Get-StationZeroCommandSpec -Config $Config
    Write-StationZeroLog -Kind control -Message "Arranque $($Config.Mode): $($command.FilePath) $($command.Arguments -join ' ')"

    if ($Foreground) {
        Push-Location $script:StationZeroRoot
        try {
            & $command.FilePath @($command.Arguments)
        } finally {
            Pop-Location
        }
        return @{
            Started = $true
            AlreadyRunning = $false
            Processes = @()
        }
    }

    $process = Start-Process -FilePath $command.FilePath `
        -ArgumentList $command.Arguments `
        -WorkingDirectory $script:StationZeroRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $Config.StdOutLog `
        -RedirectStandardError $Config.StdErrLog `
        -PassThru

    $ready = Wait-StationZeroPortState -Port $Config.Port -ShouldListen $true -TimeoutSeconds 20
    $processes = @(Get-StationZeroModeProcesses -Config $Config)
    if ($processes.Count -gt 0) {
        Save-StationZeroPidFile -Config $Config -Processes $processes
    }

    if (-not $ready) {
        Write-StationZeroLog -Kind control -Message "Falha no arranque $($Config.Mode): porta $($Config.Port) nao ficou a escutar."
        throw "A app nao ficou a escutar na porta $($Config.Port). Ver logs: $($Config.StdErrLog)"
    }

    Write-StationZeroLog -Kind control -Message "$($Config.Mode) iniciado com sucesso na porta $($Config.Port). PID principal: $($process.Id)."
    return @{
        Started = $true
        AlreadyRunning = $false
        Processes = $processes
    }
}

function Stop-StationZeroMode {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [switch]$IncludeNginx
    )

    Ensure-StationZeroDirectories

    $processes = @(Get-StationZeroModeProcesses -Config $Config)
    if ($processes.Count -eq 0) {
        if ($IncludeNginx -and $Config.Mode -eq 'Server') {
            $nginx = Get-StationZeroNginxProcess
            if ($nginx) {
                Stop-Process -Id $nginx.ProcessId -Force -ErrorAction SilentlyContinue
                Write-StationZeroLog -Kind control -Message "Nginx parado (PID $($nginx.ProcessId))."
            }
        }
        Clear-StationZeroPidFile -Config $Config
        Write-StationZeroLog -Kind control -Message "Nenhum processo ativo para $($Config.Mode)."
        return @{
            Stopped = $false
            Processes = @()
        }
    }

    foreach ($proc in $processes) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-StationZeroLog -Kind control -Message "Processo parado: PID $($proc.ProcessId) [$($proc.Name)] para modo $($Config.Mode)."
        } catch {
            Write-StationZeroLog -Kind control -Message "Falha ao parar PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }

    if (-not (Wait-StationZeroPortState -Port $Config.Port -ShouldListen $false -TimeoutSeconds 15)) {
        Write-StationZeroLog -Kind control -Message "Porta $($Config.Port) continuou em escuta apos stop do modo $($Config.Mode)."
        throw "A porta $($Config.Port) continuou ocupada apos stop."
    }

    if ($IncludeNginx -and $Config.Mode -eq 'Server') {
        $nginx = Get-StationZeroNginxProcess
        if ($nginx) {
            Stop-Process -Id $nginx.ProcessId -Force -ErrorAction SilentlyContinue
            Write-StationZeroLog -Kind control -Message "Nginx parado (PID $($nginx.ProcessId))."
        }
    }

    Clear-StationZeroPidFile -Config $Config
    return @{
        Stopped = $true
        Processes = $processes
    }
}

function Get-StationZeroStatus {
    param([string]$Mode = 'Auto')

    Ensure-StationZeroDirectories

    $modes = @()
    if ((Normalize-StationZeroMode -Mode $Mode) -eq 'Auto') {
        $modes = @('Dev', 'ProdLike', 'Server')
    } else {
        $modes = @((Resolve-StationZeroMode -Mode $Mode -ForStatus))
    }

    $rows = foreach ($modeName in $modes) {
        $config = Get-StationZeroModeConfig -Mode $modeName
        $procs = @(Get-StationZeroModeProcesses -Config $config)
        $owner = Get-StationZeroPortOwnerProcess -Port $config.Port
        [pscustomobject]@{
            Mode = $config.Mode
            Host = $config.Host
            Port = $config.Port
            Running = ($procs.Count -gt 0 -or (Test-StationZeroPortListening -Port $config.Port))
            ProcessIds = if ($procs.Count) { (@($procs.ProcessId) -join ', ') } else { '' }
            PortOwner = if ($owner) { "$($owner.ProcessId) [$($owner.Name)]" } else { '' }
            StdOutLog = $config.StdOutLog
            StdErrLog = $config.StdErrLog
        }
    }

    $nginxProc = Get-StationZeroNginxProcess
    $statusMessage = ($rows | ForEach-Object { "$($_.Mode): running=$($_.Running) port=$($_.Port) pid=$($_.ProcessIds)" }) -join ' | '
    if ($nginxProc) {
        $statusMessage += " | nginx: PID $($nginxProc.ProcessId)"
    } else {
        $statusMessage += " | nginx: inactive"
    }
    Write-StationZeroLog -Kind status -Message $statusMessage

    return [pscustomobject]@{
        AppModes = $rows
        NginxRunning = [bool]$nginxProc
        NginxProcessId = if ($nginxProc) { $nginxProc.ProcessId } else { $null }
        NginxLogs = $script:StationZeroConfig.NginxLogs
        ControlLog = Get-StationZeroLogPath -Kind control
        StatusLog = Get-StationZeroLogPath -Kind status
        UpdateLog = Get-StationZeroLogPath -Kind update
    }
}
