from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import re
import uuid

import pyodbc
from flask import current_app
from sqlalchemy import text

from models import db


def _conn_part(conn_str: str, key: str) -> str:
    match = re.search(rf"(?:^|;){re.escape(key)}=([^;]*)", conn_str or "", flags=re.IGNORECASE)
    return str(match.group(1) or "").strip() if match else ""


def _replace_conn_part(conn_str: str, key: str, value: str) -> str:
    clean_value = str(value or "").strip()
    if re.search(rf"(?:^|;){re.escape(key)}=", conn_str or "", flags=re.IGNORECASE):
        return re.sub(
            rf"((?:^|;){re.escape(key)}=)[^;]*",
            rf"\g<1>{clean_value}",
            conn_str,
            count=1,
            flags=re.IGNORECASE,
        )
    return conn_str.rstrip(";") + f";{key}={clean_value};"


def _client_conn_str() -> str:
    conn_map = current_app.config.get("DB_CONN_STRS") or {}
    client_conn = str(conn_map.get("client") or conn_map.get("default") or "").strip()
    if not client_conn:
        raise RuntimeError("Ligacao client/GR360_CORE nao configurada.")
    return client_conn


def _phc_conn_str(database_name: str, server_name: str = "") -> str:
    conn_str = _replace_conn_part(_client_conn_str(), "DATABASE", database_name)
    server = str(server_name or "").strip()
    if server:
        current_server = _conn_part(conn_str, "SERVER")
        port = ""
        if "," in current_server and "," not in server:
            port = current_server.split(",", 1)[1].strip()
        server_value = f"{server},{port}" if port else server
        conn_str = _replace_conn_part(conn_str, "SERVER", server_value)
    return conn_str


def _active_fe_sources() -> list[dict]:
    rows = db.session.execute(text("""
        SELECT
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(PHC_DB, ''))) AS PHC_DB,
            LTRIM(RTRIM(ISNULL(PHC_SERVER, ''))) AS PHC_SERVER
        FROM dbo.FE
        WHERE ISNULL(ATIVA, 1) = 1
          AND LTRIM(RTRIM(ISNULL(PHC_DB, ''))) <> ''
        ORDER BY ISNULL(NOME, ''), ISNULL(FEID, 0)
    """)).mappings().all()
    return [dict(row) for row in rows]


def _source_us_columns(cursor) -> set[str]:
    cursor.execute("""
        SELECT LOWER(COLUMN_NAME) AS COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'US'
    """)
    return {str(row[0] or "").strip().lower() for row in cursor.fetchall()}


def _read_source_users(source: dict) -> tuple[list[dict], str]:
    database_name = str(source.get("PHC_DB") or "").strip()
    if not database_name:
        return [], ""
    conn_str = _phc_conn_str(database_name, source.get("PHC_SERVER") or "")
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            columns = _source_us_columns(cursor)
            required = {"username", "usercode", "email", "aextpw", "inactivo"}
            missing = sorted(required - columns)
            if missing:
                return [], f"{database_name}: campos em falta na US: {', '.join(missing)}"
            cursor.execute("""
                SELECT
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), username), ''))) AS username,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), usercode), ''))) AS usercode,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), email), ''))) AS email,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), aextpw), ''))) AS aextpw
                FROM dbo.US
                WHERE ISNULL(inactivo, 0) = 0
                  AND LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), usercode), ''))) <> ''
                ORDER BY LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), username), ''))), LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), usercode), '')))
            """)
            rows = []
            for row in cursor.fetchall():
                rows.append({
                    "nome": str(row.username or "").strip(),
                    "login": str(row.usercode or "").strip(),
                    "email": str(row.email or "").strip(),
                    "password": str(row.aextpw or "").strip(),
                })
            return rows, ""
    except Exception as exc:
        return [], f"{database_name}: {exc}"


def _inactivate_source_user(source: dict, login: str) -> tuple[int, str]:
    database_name = str(source.get("PHC_DB") or "").strip()
    clean_login = str(login or "").strip()
    if not database_name or not clean_login:
        return 0, ""
    conn_str = _phc_conn_str(database_name, source.get("PHC_SERVER") or "")
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            columns = _source_us_columns(cursor)
            missing = sorted({"usercode", "inactivo"} - columns)
            if missing:
                return 0, f"{database_name}: campos em falta na US: {', '.join(missing)}"
            cursor.execute("""
                UPDATE dbo.US
                   SET inactivo = 1
                 WHERE LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), usercode), ''))) = ?
                   AND ISNULL(inactivo, 0) = 0
            """, clean_login)
            affected = int(cursor.rowcount or 0)
            conn.commit()
            return affected, ""
    except Exception as exc:
        return 0, f"{database_name}: {exc}"


def _local_users_by_login() -> dict[str, dict]:
    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS USSTAMP,
            LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(EMAIL, ''))) AS EMAIL
        FROM dbo.US
        WHERE LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
    """)).mappings().all()
    return {str(row.get("LOGIN") or "").strip().upper(): dict(row) for row in rows}


def _local_users_by_email() -> dict[str, dict]:
    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS USSTAMP,
            LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(EMAIL, ''))) AS EMAIL
        FROM dbo.US
        WHERE LTRIM(RTRIM(ISNULL(EMAIL, ''))) <> ''
    """)).mappings().all()
    return {str(row.get("EMAIL") or "").strip().upper(): dict(row) for row in rows}


def _aggregate_source_users() -> tuple[list[dict], list[str], list[dict]]:
    warnings: list[str] = []
    sources = _active_fe_sources()
    by_login: OrderedDict[str, dict] = OrderedDict()
    for source in sources:
        rows, warning = _read_source_users(source)
        if warning:
            warnings.append(warning)
        for row in rows:
            login = str(row.get("login") or "").strip()
            if not login:
                continue
            key = login.upper()
            item = by_login.get(key)
            if not item:
                item = {
                    "key": key,
                    "nome": row.get("nome") or login,
                    "email": row.get("email") or "",
                    "login": login,
                    "password": row.get("password") or "",
                    "empresas": [],
                    "feids": [],
                    "exists_local": False,
                    "local_usstamp": "",
                }
                by_login[key] = item
            if not item.get("nome") and row.get("nome"):
                item["nome"] = row.get("nome")
            if not item.get("email") and row.get("email"):
                item["email"] = row.get("email")
            if not item.get("password") and row.get("password"):
                item["password"] = row.get("password")
            feid = int(source.get("FEID") or 0)
            if feid and feid not in item["feids"]:
                item["feids"].append(feid)
                item["empresas"].append({
                    "feid": feid,
                    "nome": source.get("NOME") or str(feid),
                    "phc_db": source.get("PHC_DB") or "",
                })

    local_users = _local_users_by_login()
    local_emails = _local_users_by_email()
    result = []
    for item in by_login.values():
        local = local_users.get(str(item.get("login") or "").strip().upper())
        if local:
            continue
        item["can_import"] = True
        item["status"] = "Novo"
        email_key = str(item.get("email") or "").strip().upper()
        if not email_key:
            item["can_import"] = False
            item["status"] = "Sem email"
        else:
            email_user = local_emails.get(email_key)
            if email_user and str(email_user.get("LOGIN") or "").strip().upper() != str(item.get("login") or "").strip().upper():
                item["can_import"] = False
                item["status"] = f"Email usado por {email_user.get('LOGIN') or '-'}"
        result.append(item)
    result.sort(key=lambda row: (str(row.get("nome") or "").upper(), str(row.get("login") or "").upper()))
    return result, warnings, sources


def scan_phc_users_for_import() -> dict:
    rows, warnings, sources = _aggregate_source_users()
    return {
        "ok": True,
        "rows": rows,
        "warnings": warnings,
        "sources": sources,
    }


def _find_local_user_by_login(login: str) -> dict | None:
    row = db.session.execute(text("""
        SELECT TOP 1
            USSTAMP,
            ISNULL(LOGIN, '') AS LOGIN
        FROM dbo.US
        WHERE UPPER(LTRIM(RTRIM(ISNULL(LOGIN, '')))) = :login
    """), {"login": str(login or "").strip().upper()}).mappings().first()
    return dict(row) if row else None


def _email_conflict(email: str, usstamp: str = "") -> dict | None:
    clean_email = str(email or "").strip()
    if not clean_email:
        return None
    row = db.session.execute(text("""
        SELECT TOP 1 USSTAMP, ISNULL(LOGIN, '') AS LOGIN
        FROM dbo.US
        WHERE UPPER(LTRIM(RTRIM(ISNULL(EMAIL, '')))) = :email
          AND (:usstamp = '' OR USSTAMP <> :usstamp)
    """), {
        "email": clean_email.upper(),
        "usstamp": str(usstamp or "").strip(),
    }).mappings().first()
    return dict(row) if row else None


def _insert_or_update_user(row: dict) -> tuple[str, bool]:
    login = str(row.get("login") or "").strip()
    if not login:
        raise ValueError("Login em falta.")
    nome = str(row.get("nome") or login).strip()[:60]
    email = str(row.get("email") or "").strip()[:120]
    password = str(row.get("password") or "").strip()[:128]
    if not email:
        raise ValueError("Email em falta no PHC.")
    local = _find_local_user_by_login(login)
    if local:
        usstamp = str(local.get("USSTAMP") or "").strip()
        conflict = _email_conflict(email, usstamp)
        if conflict:
            raise ValueError(f"O email {email} ja existe no utilizador {conflict.get('LOGIN')}.")
        db.session.execute(text("""
            UPDATE dbo.US
               SET NOME = :nome,
                   EMAIL = :email,
                   PASSWORD = :password
             WHERE USSTAMP = :usstamp
        """), {
            "nome": nome,
            "email": email,
            "password": password,
            "usstamp": usstamp,
        })
        return usstamp, False

    conflict = _email_conflict(email, "")
    if conflict:
        raise ValueError(f"O email {email} ja existe no utilizador {conflict.get('LOGIN')}.")
    usstamp = uuid.uuid4().hex.upper()[:25]
    db.session.execute(text("""
        INSERT INTO dbo.US
        (
            USSTAMP, NOME, LOGIN, PASSWORD, EMAIL,
            ADMIN, TECNICO, COR, DEV, HOME, MNADMIN, LPADMIN, INATIVO,
            FOTO, TELEFONE, LSADMIN, ESCALA, TESOURARIA, TEMPOS, VIEWMODE,
            PASSWORD_MIGRADA, PASSWORD_RESET_REQUIRED, FAILED_LOGIN_COUNT,
            IS_ACTIVE, PENO, PENOME, MOTORISTA
        )
        VALUES
        (
            :USSTAMP, :NOME, :LOGIN, :PASSWORD, :EMAIL,
            0, '', '', 0, '', 0, 0, 0,
            '', '', 0, '', 0, 0, 'LIGHT MODE',
            0, 0, 0,
            1, 0, '', ''
        )
    """), {
        "USSTAMP": usstamp,
        "NOME": nome,
        "LOGIN": login[:60],
        "PASSWORD": password,
        "EMAIL": email,
    })
    return usstamp, True


def _ensure_user_company(usstamp: str, feid: int, principal: bool, user_login: str) -> bool:
    existing = db.session.execute(text("""
        SELECT TOP 1 USFESTAMP
        FROM dbo.US_FE
        WHERE USSTAMP = :usstamp
          AND FEID = :feid
    """), {
        "usstamp": usstamp,
        "feid": feid,
    }).mappings().first()
    now = datetime.now()
    if existing:
        db.session.execute(text("""
            UPDATE dbo.US_FE
               SET ATIVO = 1,
                   PRINCIPAL = CASE WHEN :principal = 1 THEN 1 ELSE PRINCIPAL END,
                   DTAlteracao = :dtalt,
                   USERALTERACAO = :useralt
             WHERE USFESTAMP = :usfestamp
        """), {
            "principal": 1 if principal else 0,
            "dtalt": now,
            "useralt": user_login,
            "usfestamp": existing.get("USFESTAMP"),
        })
        return False

    db.session.execute(text("""
        INSERT INTO dbo.US_FE
        (
            USFESTAMP, USSTAMP, FEID, ATIVO, PRINCIPAL,
            DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO
        )
        VALUES
        (
            :USFESTAMP, :USSTAMP, :FEID, 1, :PRINCIPAL,
            :DTCriacao, :DTAlteracao, :USERCRIACAO, :USERALTERACAO
        )
    """), {
        "USFESTAMP": uuid.uuid4().hex.upper()[:25],
        "USSTAMP": usstamp,
        "FEID": feid,
        "PRINCIPAL": 1 if principal else 0,
        "DTCriacao": now,
        "DTAlteracao": now,
        "USERCRIACAO": user_login,
        "USERALTERACAO": user_login,
    })
    return True


def import_phc_users(selected_keys: list[str], user_login: str) -> dict:
    selected = {str(key or "").strip().upper() for key in selected_keys if str(key or "").strip()}
    if not selected:
        raise ValueError("Selecione pelo menos um utilizador para importar.")
    rows, warnings, _ = _aggregate_source_users()
    selected_rows = [row for row in rows if str(row.get("key") or "").strip().upper() in selected]
    if not selected_rows:
        raise ValueError("Nenhum dos utilizadores selecionados foi encontrado nas bases PHC.")

    imported = 0
    updated = 0
    linked = 0
    skipped: list[dict] = []
    for row in selected_rows:
        login = str(row.get("login") or "").strip()
        try:
            row_imported = 0
            row_updated = 0
            row_linked = 0
            with db.session.begin_nested():
                usstamp, created = _insert_or_update_user(row)
                if created:
                    row_imported = 1
                else:
                    row_updated = 1

                existing_principal = db.session.execute(text("""
                    SELECT TOP 1 USFESTAMP
                    FROM dbo.US_FE
                    WHERE USSTAMP = :usstamp
                      AND ISNULL(PRINCIPAL, 0) = 1
                """), {"usstamp": usstamp}).mappings().first()
                for index, feid in enumerate(row.get("feids") or []):
                    if _ensure_user_company(usstamp, int(feid), not existing_principal and index == 0, user_login):
                        row_linked += 1
            imported += row_imported
            updated += row_updated
            linked += row_linked
        except Exception as exc:
            skipped.append({"login": login, "error": str(exc)})

    db.session.commit()
    return {
        "ok": True,
        "imported": imported,
        "updated": updated,
        "linked": linked,
        "skipped": skipped,
        "warnings": warnings,
    }


def inactivate_phc_user(user_key: str) -> dict:
    clean_key = str(user_key or "").strip().upper()
    if not clean_key:
        raise ValueError("Utilizador em falta.")

    rows, warnings, _ = _aggregate_source_users()
    row = next((item for item in rows if str(item.get("key") or "").strip().upper() == clean_key), None)
    if not row:
        raise ValueError("Utilizador PHC não encontrado ou já não está ativo.")

    affected = 0
    results = []
    source_map = {
        int(source.get("FEID") or 0): source
        for source in _active_fe_sources()
        if int(source.get("FEID") or 0)
    }
    for feid in row.get("feids") or []:
        source = source_map.get(int(feid or 0))
        if not source:
            continue
        count, warning = _inactivate_source_user(source, row.get("login") or "")
        affected += count
        if warning:
            warnings.append(warning)
        results.append({
            "feid": int(feid or 0),
            "empresa": source.get("NOME") or "",
            "phc_db": source.get("PHC_DB") or "",
            "affected": count,
            "warning": warning,
        })

    return {
        "ok": True,
        "login": row.get("login") or "",
        "affected": affected,
        "results": results,
        "warnings": warnings,
    }
