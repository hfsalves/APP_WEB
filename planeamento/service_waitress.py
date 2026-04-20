import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os
import datetime
import sys
import traceback

# Caminhos absolutos
PYTHON_EXE = r"C:\planeamento\venv\Scripts\python.exe"
SCRIPT_PATH = r"C:\planeamento\run.py"
LOG_PATH = r"C:\planeamento\service_log.txt"
BOOT_LOG_PATH = r"C:\planeamento\service_boot.txt"

def log(msg):
    """Escreve mensagem no log principal"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass  # Evita falhas se não conseguir escrever

def boot_log(msg):
    """Escreve mensagem no log de arranque"""
    try:
        with open(BOOT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


class FlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = "FlaskWaitressService"
    _svc_display_name_ = "Flask Waitress Web Server"
    _svc_description_ = "Serviço que inicia automaticamente o servidor Waitress para o Flask."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        log("Pedido de paragem recebido.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
            log("Processo terminado.")
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        boot_log("A iniciar serviço (SvcDoRun)...")
        try:
            os.chdir(os.path.dirname(SCRIPT_PATH))
            env = os.environ.copy()

            log(f"Executável: {PYTHON_EXE}")
            log(f"Script: {SCRIPT_PATH}")

            self.process = subprocess.Popen([PYTHON_EXE, SCRIPT_PATH], env=env)
            log("Waitress iniciado com sucesso.")
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        except Exception as e:
            boot_log("Erro em SvcDoRun:")
            boot_log(traceback.format_exc())
            log(f"Erro: {e}")
            raise


if __name__ == '__main__':
    boot_log("------ Execução direta iniciada ------")
    try:
        if len(sys.argv) == 1:
            # Executar manualmente fora do serviço
            boot_log("Modo standalone (fora do serviço)")
            os.chdir(os.path.dirname(SCRIPT_PATH))
            subprocess.Popen([PYTHON_EXE, SCRIPT_PATH], env=os.environ.copy())
            boot_log("Run.py executado manualmente.")
        else:
            # Executar como serviço Windows
            boot_log("Modo serviço - HandleCommandLine iniciado")
            win32serviceutil.HandleCommandLine(FlaskService)
    except Exception:
        boot_log("Erro no bloco principal:")
        boot_log(traceback.format_exc())
