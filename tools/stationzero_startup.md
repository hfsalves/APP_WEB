# StationZero startup

## Scripts disponiveis

- `tools/start_stationzero.ps1`
- `tools/stop_stationzero.ps1`
- `tools/restart_stationzero.ps1`
- `tools/status_stationzero.ps1`

Wrappers:

- `tools/start_stationzero.bat`
- `tools/restart_stationzero.bat`
- `tools/restart_stationzero_local.bat`

## Modos

- `Dev`
  - usa `flask run --debug`
  - host `127.0.0.1`
  - porta `5000`
  - apenas para desenvolvimento manual com hot reload

- `ProdLike`
  - usa `waitress-serve`
  - host `127.0.0.1`
  - porta `8000`
  - serve para testar localmente de forma mais proxima de producao

- `Server`
  - usa `waitress-serve`
  - host `0.0.0.0`
  - porta `8000`
  - arranca `nginx` se necessario
  - faz update de codigo antes de arrancar/reiniciar, salvo `-NoUpdate`

- `Auto`
  - se existir `C:\nginx\nginx.exe`, assume `Server`
  - caso contrario, assume `Dev`

Compatibilidade:

- `Local` e tratado como alias de `Dev`

Pode forcar por variavel de ambiente:

- `STATIONZERO_START_MODE=Dev`
- `STATIONZERO_START_MODE=ProdLike`
- `STATIONZERO_START_MODE=Server`

## Comandos reais

### Local - dev

Arrancar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\start_stationzero.ps1 -Mode Dev`

Parar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\stop_stationzero.ps1 -Mode Dev`

Reiniciar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\restart_stationzero.ps1 -Mode Dev`

Estado:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\status_stationzero.ps1 -Mode Dev`

Atalho de duplo clique:

- `C:\APP_WEB\tools\restart_stationzero_local.bat`

Esse ficheiro reinicia a app local em `Dev`.

### Local - prodlike

Arrancar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\start_stationzero.ps1 -Mode ProdLike`

Parar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\stop_stationzero.ps1 -Mode ProdLike`

Reiniciar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\restart_stationzero.ps1 -Mode ProdLike`

Estado:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\status_stationzero.ps1 -Mode ProdLike`

### Servidor Windows

Arrancar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\start_stationzero.ps1 -Mode Server`

Arrancar e forcar update de dependencias:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\start_stationzero.ps1 -Mode Server -InstallRequirements`

Parar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\stop_stationzero.ps1 -Mode Server`

Reiniciar:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\restart_stationzero.ps1 -Mode Server`

Reiniciar com update de dependencias:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\restart_stationzero.ps1 -Mode Server -InstallRequirements`

Estado:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\status_stationzero.ps1 -Mode Server`

## Update automatico do servidor

No modo `Server`, o arranque e o restart fazem esta sequencia:

1. `git fetch origin`
2. `git reset --hard origin/master`
3. opcionalmente `pip install -r requirements.txt` quando usado `-InstallRequirements`

Regras implementadas:

- o update so acontece em modo `Server`
- se o update falhar, o arranque e abortado
- no `restart`, o update corre antes do `stop`
- se o update falhar no `restart`, a instancia atual nao e parada

## Regras de seguranca dos scripts

- `start` nao cria duplicados da mesma app/modo
- se a porta esperada ja estiver ocupada:
  - se for pela propria app, faz no-op
  - se for por outro processo, aborta e mostra o PID
- `stop` mata apenas processos StationZero identificados por:
  - executavel dentro de `C:\APP_WEB`
  - command line do `flask` ou `waitress` com o modo/porta respetivos
- `restart` faz `stop`, espera curta, `start`, e valida que a porta ficou a escutar
- `nginx` so arranca se ainda nao estiver ativo

## Logs

Pasta principal:

- `C:\APP_WEB\logs`

Logs criados:

- controlo: `C:\APP_WEB\logs\stationzero-control.log`
- estado: `C:\APP_WEB\logs\stationzero-status.log`
- update: `C:\APP_WEB\logs\stationzero-update.log`
- app dev stdout: `C:\APP_WEB\logs\stationzero-dev.out.log`
- app dev stderr: `C:\APP_WEB\logs\stationzero-dev.err.log`
- app prodlike stdout: `C:\APP_WEB\logs\stationzero-prodlike.out.log`
- app prodlike stderr: `C:\APP_WEB\logs\stationzero-prodlike.err.log`
- app server stdout: `C:\APP_WEB\logs\stationzero-server.out.log`
- app server stderr: `C:\APP_WEB\logs\stationzero-server.err.log`

PID/state:

- `C:\APP_WEB\logs\run\`

Nginx:

- logs nativos em `C:\nginx\logs`

## Arranque automatico no boot

Instalar tarefa agendada:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\install_stationzero_startup_task.ps1 -Mode Server`

Instalar com update de dependencias:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\install_stationzero_startup_task.ps1 -Mode Server -InstallRequirements`

Remover tarefa:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\remove_stationzero_startup_task.ps1`

Testar manualmente o mesmo arranque da tarefa:

- `powershell -ExecutionPolicy Bypass -File C:\APP_WEB\tools\start_stationzero.ps1 -Mode Server`

## Notas

- `flask run` fica apenas para desenvolvimento manual
- `Waitress` e o modo serio para servidor
- para testes locais mais proximos de producao, usar `ProdLike`
