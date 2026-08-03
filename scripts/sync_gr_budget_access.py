#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_DB_TARGET", "client")
os.environ.setdefault("DB_LOCAL_DEFAULT_TARGET", "client")

import pyodbc
from sqlalchemy import text

from app import app
from models import db
from modules.gr_budgets.service import CLIENT_BUDGET_SERIES, _series_name_key
from services.phc_user_import_service import _active_fe_sources, _phc_conn_str


ACCESS_TABLE = "GR_ORCAMENTOS"
INITIALS_COLUMNS = ("inis", "iniciais", "userinis", "usrinis")


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _source_columns(cursor, table_name: str) -> set[str]:
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


def _source_budget_authors(source: dict) -> tuple[list[dict], list[dict]]:
    database_name = str(source.get("PHC_DB") or "").strip()
    warnings: list[dict] = []
    if not database_name:
        return [], warnings

    try:
        with pyodbc.connect(
            _phc_conn_str(database_name, source.get("PHC_SERVER") or ""),
            timeout=10,
        ) as conn:
            cursor = conn.cursor()
            user_columns = _source_columns(cursor, "US")
            initials_column = next(
                (column for column in INITIALS_COLUMNS if column in user_columns),
                "",
            )
            if not initials_column:
                warnings.append({"database": database_name, "warning": "A US não tem campo de iniciais."})
                return [], warnings

            cursor.execute("SELECT NDOS, NMDOS FROM dbo.TS WHERE ISNULL(NDOS, 0) > 0")
            ndos = sorted({
                int(row[0] or 0)
                for row in cursor.fetchall()
                if _series_name_key(row[1]) in CLIENT_BUDGET_SERIES
            })
            if not ndos:
                return [], warnings

            placeholders = ", ".join("?" for _ in ndos)
            cursor.execute(
                f"""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(CONVERT(varchar(50), B.OUSRINIS), '')))) AS INICIAIS,
                    COUNT(*) AS DOCUMENTOS
                  FROM dbo.BO B
                 WHERE B.NDOS IN ({placeholders})
                   AND LTRIM(RTRIM(ISNULL(CONVERT(varchar(50), B.OUSRINIS), ''))) <> ''
                 GROUP BY UPPER(LTRIM(RTRIM(ISNULL(CONVERT(varchar(50), B.OUSRINIS), ''))))
                """,
                ndos,
            )
            counts = {
                str(row[0] or "").strip().upper(): int(row[1] or 0)
                for row in cursor.fetchall()
            }

            cursor.execute(
                f"""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(CONVERT(varchar(50), {initials_column}), '')))) AS INICIAIS,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(60), USERCODE), ''))) AS LOGIN
                  FROM dbo.US
                 WHERE ISNULL(INACTIVO, 0) = 0
                   AND LTRIM(RTRIM(ISNULL(CONVERT(varchar(50), {initials_column}), ''))) <> ''
                   AND LTRIM(RTRIM(ISNULL(CONVERT(varchar(60), USERCODE), ''))) <> ''
                 ORDER BY LTRIM(RTRIM(ISNULL(CONVERT(varchar(60), USERCODE), '')))
                """
            )
            users_by_initials: dict[str, str] = {}
            for row in cursor.fetchall():
                initials = str(row[0] or "").strip().upper()
                users_by_initials.setdefault(initials, str(row[1] or "").strip())

            rows = []
            for initials, document_count in counts.items():
                login = users_by_initials.get(initials, "")
                if not login:
                    warnings.append({
                        "database": database_name,
                        "initials": initials,
                        "documents": document_count,
                        "warning": "Sem utilizador PHC ativo associado às iniciais.",
                    })
                    continue
                rows.append({
                    "database": database_name,
                    "initials": initials,
                    "login": login,
                    "documents": document_count,
                })
            return rows, warnings
    except Exception as exc:
        return [], [{"database": database_name, "warning": str(exc)}]


def _eligible_app_users() -> tuple[list[dict], list[dict]]:
    app_users = {
        str(row.get("LOGIN") or "").strip().upper(): dict(row)
        for row in db.session.execute(
            text(
                """
                SELECT USSTAMP, LOGIN, NOME
                  FROM dbo.US
                 WHERE ISNULL(INATIVO, 0) = 0
                   AND ISNULL(IS_ACTIVE, 1) = 1
                   AND LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
                """
            )
        ).mappings().all()
    }

    eligible: dict[str, dict] = {}
    warnings: list[dict] = []
    for source in _active_fe_sources():
        authors, source_warnings = _source_budget_authors(source)
        warnings.extend(source_warnings)
        for author in authors:
            login_key = str(author.get("login") or "").strip().upper()
            app_user = app_users.get(login_key)
            if not app_user:
                warnings.append({
                    **author,
                    "warning": "O utilizador PHC não existe ou não está ativo na GR360.",
                })
                continue
            item = eligible.setdefault(login_key, {
                "login": str(app_user.get("LOGIN") or "").strip(),
                "name": str(app_user.get("NOME") or "").strip(),
                "usstamp": str(app_user.get("USSTAMP") or "").strip(),
                "documents": 0,
                "companies": set(),
            })
            item["documents"] += int(author.get("documents") or 0)
            item["companies"].add(str(author.get("database") or "").strip())

    return sorted(eligible.values(), key=lambda row: row["login"].casefold()), warnings


def _grant_access(users: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for user in users:
        result = db.session.execute(
            text(
                """
                UPDATE dbo.ACESSOS
                   SET CONSULTAR = 1,
                       INSERIR = 1,
                       EDITAR = 1,
                       ELIMINAR = 0,
                       USSTAMP = :usstamp,
                       FEID = NULL
                 WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
                   AND UPPER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = :login
                """
            ),
            {
                "usstamp": user["usstamp"],
                "table_name": ACCESS_TABLE,
                "login": user["login"].upper(),
            },
        )
        affected = max(0, int(result.rowcount or 0))
        if affected:
            updated += affected
            continue

        db.session.execute(
            text(
                """
                INSERT INTO dbo.ACESSOS
                (
                    ACESSOSSTAMP, UTILIZADOR, TABELA,
                    CONSULTAR, INSERIR, EDITAR, ELIMINAR,
                    USSTAMP, FEID
                )
                VALUES
                (
                    :stamp, :login, :table_name,
                    1, 1, 1, 0,
                    :usstamp, NULL
                )
                """
            ),
            {
                "stamp": _new_stamp(),
                "login": user["login"],
                "table_name": ACCESS_TABLE,
                "usstamp": user["usstamp"],
            },
        )
        inserted += 1
    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza o acesso aos Orçamentos a partir dos autores BO.OUSRINIS do PHC.",
    )
    parser.add_argument("--apply", action="store_true", help="Grava as permissões; sem esta opção apenas analisa.")
    args = parser.parse_args()

    with app.app_context():
        database_name = str(db.session.execute(text("SELECT DB_NAME()")).scalar() or "")
        if database_name.upper() != "GR360_CORE":
            raise RuntimeError(f"Base central inesperada: {database_name}")

        users, warnings = _eligible_app_users()
        inserted = updated = 0
        if args.apply:
            try:
                inserted, updated = _grant_access(users)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        payload = {
            "applied": bool(args.apply),
            "eligible_count": len(users),
            "inserted": inserted,
            "updated": updated,
            "users": [
                {
                    **user,
                    "companies": sorted(user["companies"]),
                }
                for user in users
            ],
            "warnings": warnings,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
