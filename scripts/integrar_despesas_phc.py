#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import uuid
import urllib.request
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyodbc
from sqlalchemy import text

from app import app
from models import db
from services.phc_user_import_service import _phc_conn_str


CONVERSION_RATE = Decimal("200.482")
ZERO_DATE = datetime(1900, 1, 1)
DEFAULT_PUBLIC_BASE_URL = "https://app.gr360flooringsystems.com"


def new_stamp() -> str:
    return uuid.uuid4().hex[:25]


def clean(value: Any, max_len: int | None = None) -> str:
    text_value = str(value or "").strip()
    return text_value[:max_len] if max_len else text_value


def as_decimal(value: Any, places: str = "0.000000") -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def phc_value(value: Any) -> Decimal:
    return (Decimal(str(value or 0)) * CONVERSION_RATE).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


def table_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(
        """
        SELECT LOWER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
        """,
        table_name,
    )
    return {str(row[0] or "").strip().lower() for row in cursor.fetchall()}


def insert_dynamic(cursor, table_name: str, values: dict[str, Any]) -> dict[str, Any]:
    columns = table_columns(cursor, table_name)
    filtered = {key: value for key, value in values.items() if key.lower() in columns}
    if not filtered:
        raise RuntimeError(f"Sem colunas válidas para inserir em {table_name}.")
    cursor.execute(
        f"INSERT INTO dbo.{table_name} ({', '.join(filtered)}) VALUES ({', '.join(['?'] * len(filtered))})",
        list(filtered.values()),
    )
    return filtered


def ensure_local_tracking_schema() -> None:
    db.session.execute(
        text(
            """
            IF COL_LENGTH('dbo.COLAB_DESPESA_CAB', 'PHC_STATUS') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_CAB ADD PHC_STATUS varchar(20) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CAB_PHC_STATUS DEFAULT '';
            IF COL_LENGTH('dbo.COLAB_DESPESA_CAB', 'PHC_DSSTAMP') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_CAB ADD PHC_DSSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CAB_PHC_DSSTAMP DEFAULT '';
            IF COL_LENGTH('dbo.COLAB_DESPESA_CAB', 'PHC_DTENVIO') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_CAB ADD PHC_DTENVIO datetime NULL;
            IF COL_LENGTH('dbo.COLAB_DESPESA_CAB', 'PHC_ERRO') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_CAB ADD PHC_ERRO nvarchar(500) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CAB_PHC_ERRO DEFAULT N'';

            IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_STATUS') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_STATUS varchar(20) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_STATUS DEFAULT '';
            IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_DLSTAMP') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_DLSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_DLSTAMP DEFAULT '';
            IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_ANEXOSSTAMP') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_ANEXOSSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_ANX DEFAULT '';
            IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_DTENVIO') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_DTENVIO datetime NULL;
            IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_ERRO') IS NULL
                ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_ERRO nvarchar(500) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_ERRO DEFAULT N'';
            """
        )
    )
    db.session.commit()


def load_pending_headers(login: str = "", header_stamp: str = "", limit: int = 20) -> list[dict[str, Any]]:
    params = {"limit": int(limit or 20), "login": clean(login).lower(), "header_stamp": clean(header_stamp)}
    where = [
        "ISNULL(H.PHC_DSSTAMP, '') = ''",
        "EXISTS (SELECT 1 FROM dbo.COLAB_DESPESA_LINHA L WHERE L.DESPCABSTAMP = H.DESPCABSTAMP AND ISNULL(L.ANULADA, 0) = 0 AND L.ESTADO = 'FECHADO' AND ISNULL(L.PHC_DLSTAMP, '') = '')",
    ]
    if params["login"]:
        where.append("LOWER(LTRIM(RTRIM(ISNULL(H.LOGIN, '')))) = :login")
    if params["header_stamp"]:
        where.append("H.DESPCABSTAMP = :header_stamp")

    rows = db.session.execute(
        text(
            f"""
            SELECT TOP (:limit) H.*
            FROM dbo.COLAB_DESPESA_CAB H
            WHERE {' AND '.join(where)}
            ORDER BY H.DTCRI
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def load_pending_lines(header_stamp: str) -> list[dict[str, Any]]:
    rows = db.session.execute(
        text(
            """
            SELECT *
            FROM dbo.COLAB_DESPESA_LINHA
            WHERE DESPCABSTAMP = :stamp
              AND ISNULL(ANULADA, 0) = 0
              AND ESTADO = 'FECHADO'
              AND ISNULL(PHC_DLSTAMP, '') = ''
            ORDER BY ORDEM, DTCRI
            """
        ),
        {"stamp": header_stamp},
    ).mappings().all()
    return [dict(row) for row in rows]


def local_file_path(caminho: str) -> Path:
    clean_path = clean(caminho)
    if clean_path.startswith("/"):
        clean_path = clean_path[1:]
    return ROOT / clean_path


def read_attachment(line: dict[str, Any], public_base_url: str) -> dict[str, Any]:
    original = clean(line.get("FICHEIRO_ORIGINAL"), 255) or clean(line.get("FICHEIRO"), 255) or "anexo"
    caminho = clean(line.get("CAMINHO"))
    local_path = local_file_path(caminho)
    if local_path.exists():
        data = local_path.read_bytes()
        source = str(local_path)
    else:
        if not caminho:
            raise RuntimeError(f"Linha {line.get('DESPLINHASTAMP')} sem caminho de anexo.")
        url = public_base_url.rstrip("/") + caminho if caminho.startswith("/") else caminho
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "APP_WEB PHC expense integration"}),
            timeout=45,
        ) as response:
            data = response.read()
        source = url

    expected_size = int(line.get("TAMANHO") or 0)
    if expected_size and len(data) != expected_size:
        raise RuntimeError(
            f"Tamanho do anexo diferente na linha {line.get('DESPLINHASTAMP')}: {len(data)} vs {expected_size}"
        )
    return {"bytes": data, "original": original, "source": source}


def mark_header_error(header_stamp: str, error: Exception) -> None:
    db.session.execute(
        text(
            """
            UPDATE dbo.COLAB_DESPESA_CAB
               SET PHC_STATUS = 'ERRO',
                   PHC_ERRO = :erro,
                   DTALT = GETDATE(),
                   USERALTERACAO = 'phc_integration'
             WHERE DESPCABSTAMP = :stamp
            """
        ),
        {"stamp": header_stamp, "erro": clean(error, 500)},
    )
    db.session.commit()


def integrate_header(header: dict[str, Any], *, execute: bool, public_base_url: str) -> dict[str, Any]:
    header_stamp = clean(header.get("DESPCABSTAMP"))
    lines = load_pending_lines(header_stamp)
    if not lines:
        return {"header": header_stamp, "status": "skipped", "reason": "sem linhas fechadas pendentes"}

    phc_db = clean(header.get("PHC_DB"))
    phc_server = clean(header.get("PHC_SERVER"))
    if not phc_db:
        raise RuntimeError(f"Cabeçalho {header_stamp} sem PHC_DB.")

    attachments = {line["DESPLINHASTAMP"]: read_attachment(line, public_base_url) for line in lines}
    total_evalor = sum((Decimal(str(line.get("VALOR") or 0)) for line in lines), Decimal("0")).quantize(
        Decimal("0.000000")
    )
    total_valor = phc_value(total_evalor)

    if not execute:
        return {
            "header": header_stamp,
            "status": "dry-run",
            "phc_db": phc_db,
            "login": clean(header.get("LOGIN")),
            "peno": int(header.get("PENO") or 0),
            "linhas": len(lines),
            "total_evalor": str(total_evalor),
            "anexos": [{"linha": key, "bytes": len(value["bytes"]), "source": value["source"]} for key, value in attachments.items()],
        }

    dsstamp = new_stamp()
    now = datetime.now()
    today = date.today()
    hour = now.strftime("%H:%M:%S")
    user_inis = clean(header.get("PENOME") or header.get("LOGIN") or "APP", 30)
    peno = int(header.get("PENO") or 0)

    result_lines: list[dict[str, str]] = []
    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT no, nome, ccusto, fref, area FROM dbo.PE WHERE no = ?", peno)
            pe = cursor.fetchone()
            if not pe:
                raise RuntimeError(f"Colaborador PE.NO={peno} não existe em {phc_db}.")
            _, pe_nome, pe_ccusto, pe_fref, pe_area = pe
            ccusto = clean(pe_ccusto, 20)

            insert_dynamic(
                cursor,
                "DS",
                {
                    "dsstamp": dsstamp,
                    "no": peno,
                    "nome": clean(pe_nome or header.get("PENOME"), 55),
                    "data": lines[0].get("DATA_DESPESA") or today,
                    "descricao": "",
                    "aprovado": 0,
                    "area": clean(pe_area, 20),
                    "valor": total_valor,
                    "evalor": total_evalor,
                    "orivalor": total_valor,
                    "eorivalor": total_evalor,
                    "ousrinis": user_inis,
                    "ousrdata": today,
                    "ousrhora": hour,
                    "usrinis": user_inis,
                    "usrdata": today,
                    "usrhora": hour,
                    "marcada": 0,
                    "intid": "",
                    "ccusto": ccusto,
                    "fref": clean(pe_fref, 20),
                    "strqrcode": "",
                    "u_final": 0,
                    "u_enviado": 0,
                    "u_pendente": 0,
                    "u_obs": "Criado pela aplicação GR360.",
                    "arquivadodigital": 0,
                },
            )

            for idx, line in enumerate(lines, start=1):
                tipo = clean(line.get("TIPO"), 30).upper()
                cursor.execute("SELECT TOP 1 tdsstamp, descricao FROM dbo.TDS WHERE UPPER(LTRIM(RTRIM(descricao))) = ?", tipo)
                tds = cursor.fetchone()
                if not tds:
                    raise RuntimeError(f"Tipo de despesa não encontrado em TDS: {tipo}")
                tdsstamp = clean(tds[0], 25)
                tdsdesc = clean(tds[1], 30)
                dlstamp = new_stamp()
                anexosstamp = new_stamp()
                attachment = attachments[line["DESPLINHASTAMP"]]
                original = attachment["original"]
                fname, ext = os.path.splitext(original)
                fname = clean(fname or original, 150)
                fext = clean(ext.lstrip(".").lower(), 30)
                tipo_anexo = 1 if fext in {"jpg", "jpeg", "png", "webp", "heic", "heif"} else 2
                line_evalor = as_decimal(line.get("VALOR"))
                line_valor = phc_value(line_evalor)

                insert_dynamic(
                    cursor,
                    "ANEXOS",
                    {
                        "anexosstamp": anexosstamp,
                        "oritable": "DS",
                        "tabnm": "Ficheiro de Despesas, Cabeçalhos",
                        "resumo": fname,
                        "grupo": "",
                        "recstamp": dsstamp,
                        "uniqueid": "",
                        "descricao": original,
                        "bdados": pyodbc.Binary(attachment["bytes"]),
                        "fullname": original,
                        "fname": fname,
                        "fext": fext,
                        "flen": len(attachment["bytes"]),
                        "tipo": tipo_anexo,
                        "passw": "",
                        "origem": "Ficheiro de Despesas, Cabeçalhos",
                        "keylook": "",
                        "tpdos": 0,
                        "tpdoc": 0,
                        "ausrinis": user_inis,
                        "ausrdata": today,
                        "ausrhora": hour,
                        "eusrinis": "",
                        "eusrdata": ZERO_DATE,
                        "eusrhora": "",
                        "ousrinis": user_inis,
                        "ousrdata": today,
                        "ousrhora": hour,
                        "usrinis": user_inis,
                        "usrdata": today,
                        "usrhora": hour,
                        "marcada": 0,
                        "zipado": 0,
                        "bdadosstamp": "",
                        "invisivel": 0,
                        "checkout": 0,
                        "cuserno": 0,
                        "cusername": "",
                        "usnoopen": 0,
                        "usnaopen": "",
                        "isemail": 0,
                        "emailid": "",
                        "emaildata": ZERO_DATE,
                        "startwkf": 0,
                        "wtwstamp": "",
                        "emailsubj": "",
                        "privado": 0,
                        "nivel": 0,
                        "lsgq": 0,
                        "u_enviado": 0,
                        "u_jaobra": 0,
                        "fiscrel": 0,
                        "original": 0,
                        "filestorageid": "",
                        "marcadoenviar": 0,
                        "ziparquivodigital": 0,
                    },
                )

                insert_dynamic(
                    cursor,
                    "DL",
                    {
                        "dlstamp": dlstamp,
                        "no": 0,
                        "data": line.get("DATA_DESPESA") or today,
                        "tdsstamp": tdsstamp,
                        "tdsdesc": tdsdesc,
                        "dsstamp": dsstamp,
                        "obs": clean(line.get("OBS"), 100),
                        "documento": "",
                        "process": 0,
                        "procdata": ZERO_DATE,
                        "lordem": idx * 10000,
                        "valor": line_valor,
                        "evalor": line_evalor,
                        "orivalor": line_valor,
                        "eorivalor": line_evalor,
                        "ousrinis": user_inis,
                        "ousrdata": today,
                        "ousrhora": hour,
                        "usrinis": user_inis,
                        "usrdata": today,
                        "usrhora": hour,
                        "marcada": 0,
                        "tdstxiva": 0,
                        "iva": 0,
                        "eiva": 0,
                        "oriiva": 0,
                        "eoriiva": 0,
                        "ccusto": ccusto,
                        "ncusto": "",
                        "u_evalor": line_evalor,
                        "u_carcred": 0,
                        "u_matri": clean(line.get("VIATURA"), 20),
                        "u_kms": as_decimal(line.get("KMS"), "0.00"),
                        "u_empresa": phc_db,
                        "u_anexoss": anexosstamp,
                        "u_ref": "",
                        "u_design": "",
                        "u_qtt": 1,
                        "u_unidade": "",
                        "u_matricul": clean(line.get("VIATURA"), 25),
                    },
                )
                result_lines.append(
                    {
                        "local": line["DESPLINHASTAMP"],
                        "dlstamp": dlstamp,
                        "anexosstamp": anexosstamp,
                        "tipo": tdsdesc,
                        "evalor": str(line_evalor),
                    }
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    for line_result in result_lines:
        db.session.execute(
            text(
                """
                UPDATE dbo.COLAB_DESPESA_LINHA
                   SET PHC_STATUS = 'ENVIADO',
                       PHC_DLSTAMP = :dlstamp,
                       PHC_ANEXOSSTAMP = :anexosstamp,
                       PHC_DTENVIO = GETDATE(),
                       PHC_ERRO = N'',
                       DTALT = GETDATE(),
                       USERALTERACAO = 'phc_integration'
                 WHERE DESPLINHASTAMP = :local_stamp
                """
            ),
            line_result,
        )
    db.session.execute(
        text(
            """
            UPDATE dbo.COLAB_DESPESA_CAB
               SET ESTADO = 'ENVIADO_PHC',
                   PHC_STATUS = 'ENVIADO',
                   PHC_DSSTAMP = :dsstamp,
                   PHC_DTENVIO = GETDATE(),
                   PHC_ERRO = N'',
                   DTALT = GETDATE(),
                   USERALTERACAO = 'phc_integration'
             WHERE DESPCABSTAMP = :header_stamp
            """
        ),
        {"dsstamp": dsstamp, "header_stamp": header_stamp},
    )
    db.session.commit()
    return {"header": header_stamp, "status": "sent", "phc_db": phc_db, "dsstamp": dsstamp, "lines": result_lines}


def main() -> int:
    parser = argparse.ArgumentParser(description="Integra despesas fechadas da aplicação no PHC (DS/DL/ANEXOS).")
    parser.add_argument("--execute", action="store_true", help="Escreve no PHC. Sem esta flag corre em dry-run.")
    parser.add_argument("--login", default="", help="Filtra por login local, por exemplo acruz.")
    parser.add_argument("--header", default="", help="Filtra por DESPCABSTAMP específico.")
    parser.add_argument("--limit", type=int, default=20, help="Número máximo de cabeçalhos a processar.")
    parser.add_argument("--public-base-url", default=DEFAULT_PUBLIC_BASE_URL, help="Base URL para obter anexos se o ficheiro local não existir.")
    args = parser.parse_args()

    with app.app_context():
        local_db = db.session.execute(text("SELECT DB_NAME()")).scalar()
        if str(local_db).upper() != "GR360_CORE":
            raise RuntimeError(f"Base local inesperada: {local_db}. A integração só deve correr em GR360_CORE.")
        ensure_local_tracking_schema()
        headers = load_pending_headers(login=args.login, header_stamp=args.header, limit=args.limit)
        print(f"mode={'EXECUTE' if args.execute else 'DRY_RUN'} db={local_db} pending_headers={len(headers)}")
        for header in headers:
            try:
                print(integrate_header(header, execute=args.execute, public_base_url=args.public_base_url))
            except Exception as exc:
                if args.execute:
                    mark_header_error(clean(header.get("DESPCABSTAMP")), exc)
                print({"header": clean(header.get("DESPCABSTAMP")), "status": "error", "error": str(exc)})
                if args.header:
                    raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
