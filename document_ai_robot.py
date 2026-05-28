#!/usr/bin/env python3
"""Robot externo para importar documentos das origens configuradas."""

from __future__ import annotations

import argparse
import logging
import os
import platform
import subprocess
import sys
import time
from urllib.parse import quote


LOCAL_ENV_FILE = "document_ai_robot.local.env"


def _strip_env_value(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_local_env_file() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOCAL_ENV_FILE)
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = _strip_env_value(value)
            if key and value and key not in os.environ:
                os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa documentos das origens DOC_SOURCE para o Document AI inbox.")
    parser.add_argument("--loop", action="store_true", help="Corre continuamente.")
    parser.add_argument("--interval", type=int, default=300, help="Intervalo em segundos quando usado com --loop.")
    parser.add_argument("--limit", type=int, default=50, help="Máximo de ficheiros processados por origem em cada ciclo.")
    parser.add_argument("--min-year", type=int, default=int(os.environ.get("DOCUMENT_AI_MIN_YEAR", "2026") or 2026), help="Ano mínimo dos documentos a importar.")
    parser.add_argument("--source-id", default="", help="Processa apenas uma origem específica.")
    parser.add_argument("--user", default="document_ai_robot", help="Valor de auditoria para USERCRIACAO/USERALTERACAO.")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"), help="Nível de log.")
    parser.add_argument("--db-server", default=os.environ.get("DOCUMENT_AI_DB_SERVER", "10.0.1.12"), help="Servidor SQL usado pelo robot.")
    parser.add_argument("--db-port", default=os.environ.get("DOCUMENT_AI_DB_PORT", ""), help="Porta SQL usada pelo robot.")
    parser.add_argument("--db-name", default=os.environ.get("DOCUMENT_AI_DB_NAME", "GR360_CORE"), help="Base de dados usada pelo robot.")
    parser.add_argument("--db-user", default=os.environ.get("DOCUMENT_AI_DB_USER", "sa"), help="Utilizador SQL usado pelo robot.")
    parser.add_argument("--db-password", default=os.environ.get("DOCUMENT_AI_DB_PASSWORD", "H$ols2020"), help="Password SQL usada pelo robot.")
    parser.add_argument("--smb-host", default=os.environ.get("DOCUMENT_AI_SMB_HOST", "10.0.1.11"), help="Servidor SMB das origens documentais.")
    parser.add_argument("--smb-share", default=os.environ.get("DOCUMENT_AI_SMB_SHARE", "ged"), help="Share SMB das origens documentais.")
    parser.add_argument("--smb-mount", default=os.environ.get("DOCUMENT_AI_SMB_MOUNT", "/Volumes/ged"), help="Ponto de montagem local do share SMB.")
    parser.add_argument("--smb-user", default=os.environ.get("DOCUMENT_AI_SMB_USER", ""), help="Utilizador SMB opcional para montar no macOS.")
    parser.add_argument("--smb-password", default=os.environ.get("DOCUMENT_AI_SMB_PASSWORD", ""), help="Password SMB opcional para montar no macOS.")
    parser.add_argument("--smb-domain", default=os.environ.get("DOCUMENT_AI_SMB_DOMAIN", ""), help="Domínio SMB opcional.")
    parser.add_argument("--no-smb-mount", action="store_true", help="Não tenta montar o share SMB no macOS.")
    parser.add_argument(
        "--respect-database-url",
        action="store_true",
        help="Não remove DATABASE_URL/DATABASE_URL_PROD do ambiente antes de importar a app.",
    )
    return parser


def reexec_with_project_venv(argv: list[str] | None = None) -> None:
    if os.environ.get("DOCUMENT_AI_ROBOT_NO_VENV") == "1":
        return
    root_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root_dir, "venv", "bin", "python"),
        os.path.join(root_dir, "venv", "Scripts", "python.exe"),
    ]
    current_python = os.path.realpath(sys.executable)
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        venv_python = os.path.realpath(candidate)
        if current_python == venv_python:
            return
        os.execv(candidate, [candidate, os.path.abspath(__file__), *(argv or sys.argv[1:])])


def run_once(args: argparse.Namespace) -> dict:
    configure_robot_database(args)
    os.environ["DOCUMENT_AI_MIN_YEAR"] = str(max(1900, int(args.min_year or 2026)))
    logging.info("A preparar caminhos das origens documentais.")
    configure_document_source_paths(args)
    logging.info("A importar aplicação Flask.")
    from app import app
    from services.document_ai_service import scan_document_sources
    logging.info("Aplicação Flask importada. A iniciar leitura das origens.")

    with app.app_context():
        result = scan_document_sources(
            source_id=args.source_id,
            limit_per_source=args.limit,
            requested_by=args.user,
        )
    logging.info("Leitura das origens concluída.")
    return result


def configure_robot_database(args: argparse.Namespace) -> None:
    if not args.respect_database_url:
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("DATABASE_URL_PROD", None)
    os.environ["DB_PROD_SERVER"] = str(args.db_server or "10.0.1.12").strip()
    os.environ["DB_PROD_PORT"] = str(args.db_port or "").strip()
    os.environ["DB_PROD_NAME"] = str(args.db_name or "GR360_CORE").strip()
    os.environ["DB_PROD_USER"] = str(args.db_user or "sa").strip()
    os.environ["DB_PROD_PASSWORD"] = str(args.db_password or "").strip()
    os.environ["DB_PROD_FALLBACK_SERVER"] = os.environ["DB_PROD_SERVER"]
    os.environ["DB_PROD_FALLBACK_PORT"] = os.environ["DB_PROD_PORT"]
    os.environ["DB_CLIENT_SERVER"] = os.environ["DB_PROD_SERVER"]
    os.environ["DB_CLIENT_PORT"] = os.environ["DB_PROD_PORT"]
    os.environ["DB_CLIENT_NAME"] = os.environ["DB_PROD_NAME"]
    os.environ["DB_CLIENT_USER"] = os.environ["DB_PROD_USER"]
    os.environ["DB_CLIENT_PASSWORD"] = os.environ["DB_PROD_PASSWORD"]
    os.environ["APP_DB_TARGET"] = "client"
    os.environ.setdefault("DB_SKIP_STARTUP_CONNECT_TEST", "1")


def _append_path_mapping(source_prefix: str, local_prefix: str) -> None:
    source_prefix = str(source_prefix or "").strip()
    local_prefix = str(local_prefix or "").strip()
    if not source_prefix or not local_prefix:
        return
    new_mapping = f"{source_prefix}={local_prefix}"
    current = str(os.environ.get("DOCUMENT_AI_PATH_MAPS") or "").strip()
    mappings = []
    normalized_source = source_prefix.replace("\\", "/").rstrip("/").lower()
    for item in current.split(";"):
        item = item.strip()
        if not item:
            continue
        existing_source = item.split("=", 1)[0].replace("\\", "/").rstrip("/").lower()
        if existing_source != normalized_source:
            mappings.append(item)
    if new_mapping not in mappings:
        mappings.append(new_mapping)
    os.environ["DOCUMENT_AI_PATH_MAPS"] = ";".join(mappings)


def _ensure_macos_smb_mount(args: argparse.Namespace) -> str:
    mount_path = str(args.smb_mount or "").strip()
    if args.no_smb_mount or platform.system() != "Darwin":
        return mount_path
    host = str(args.smb_host or "").strip()
    share = str(args.smb_share or "").strip().strip("/")
    if not mount_path or not host or not share:
        return mount_path
    if os.path.ismount(mount_path):
        return mount_path
    user = str(args.smb_user or "").strip()
    password = str(args.smb_password or "")
    if not user or not password:
        logging.info("Share SMB não montado automaticamente; defina DOCUMENT_AI_SMB_USER/PASSWORD ou monte %s manualmente.", mount_path)
        return mount_path
    try:
        os.makedirs(mount_path, exist_ok=True)
    except PermissionError:
        fallback_mount = os.path.join(os.path.expanduser("~"), "Volumes", share)
        logging.info("Sem permissão para criar %s; vou usar %s.", mount_path, fallback_mount)
        mount_path = fallback_mount
        os.makedirs(mount_path, exist_ok=True)
    if os.path.ismount(mount_path):
        return mount_path
    domain = str(args.smb_domain or "").strip()
    user_part = quote(user, safe="")
    if domain:
        user_part = f"{quote(domain, safe='')};{user_part}"
    smb_url = f"//{user_part}:{quote(password, safe='')}@{host}/{quote(share, safe='/')}"
    try:
        subprocess.run(
            ["mount_smbfs", smb_url, mount_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        logging.info("Share SMB montado em %s.", mount_path)
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or "").strip()
        logging.warning("Não foi possível montar o share SMB em %s. %s", mount_path, message)
    return mount_path


def configure_document_source_paths(args: argparse.Namespace) -> None:
    host = str(args.smb_host or "10.0.1.11").strip()
    share = str(args.smb_share or "ged").strip().strip("\\/")
    mount_path = str(args.smb_mount or "/Volumes/ged").strip()
    mount_path = _ensure_macos_smb_mount(args) or mount_path
    if host and share and mount_path:
        _append_path_mapping(f"\\\\{host}\\{share}", mount_path)


def log_result(result: dict) -> None:
    logging.info(
        "Document AI robot: %s origem(ns), %s encontrado(s), %s importado(s), %s duplicado(s), %s erro(s).",
        result.get("sources", 0),
        result.get("found", 0),
        result.get("imported", 0),
        result.get("skipped", 0),
        result.get("errors", 0),
    )
    for item in result.get("results") or []:
        message = item.get("message") or ""
        logging.info(
            "Origem %s: %s importado(s), %s duplicado(s), %s erro(s). %s",
            item.get("source_name") or item.get("source_id") or "",
            item.get("imported", 0),
            item.get("skipped", 0),
            item.get("errors", 0),
            message,
        )


def main(argv: list[str] | None = None) -> int:
    reexec_with_project_venv(argv)
    load_local_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info("Document AI robot configurado para SQL Server %s / %s.", args.db_server, args.db_name)

    if not args.loop:
        log_result(run_once(args))
        return 0

    interval = max(10, int(args.interval or 300))
    logging.info("Document AI robot iniciado em modo contínuo, intervalo=%ss.", interval)
    while True:
        try:
            log_result(run_once(args))
        except KeyboardInterrupt:
            logging.info("Document AI robot interrompido.")
            return 0
        except Exception:
            logging.exception("Erro no ciclo do Document AI robot.")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
