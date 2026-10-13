from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import re
import uuid

import pyodbc
from flask import current_app
from sqlalchemy import text

from models import db
from services.auth_service import hash_password


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


def _portal_table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(text("""
        SELECT UPPER(COLUMN_NAME) AS COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
    """), {"table_name": str(table_name or "").strip()}).scalars().all()
    return {str(value or "").strip().upper() for value in rows}


def _first_existing_column(columns: set[str], candidates: list[str]) -> str:
    return next((candidate for candidate in candidates if candidate.upper() in columns), "")


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


def collaborator_user_company_options() -> list[dict]:
    """Return active companies, including whether they can supply PHC employees."""
    columns = _portal_table_columns("FE")
    database_column = _first_existing_column(columns, [
        "PHC_DATABASE", "PHC_DB", "DBPHC", "BDPHC",
        "ERP_DATABASE", "ERP_DB", "DBERP", "BDERP",
        "DATABASE_NAME", "DB_NAME", "DBNAME",
        "BASEDADOS", "BASE_DADOS", "BD", "NOMEBD",
    ])
    server_column = _first_existing_column(columns, [
        "PHC_SERVER", "SERVER_PHC", "ERP_SERVER", "SERVER_ERP",
        "SQLSERVER", "SQL_SERVER", "SERVIDOR", "SERVER",
    ])
    database_select = f"LTRIM(RTRIM(ISNULL([{database_column}], '')))" if database_column else "CAST('' AS varchar(128))"
    server_select = f"LTRIM(RTRIM(ISNULL([{server_column}], '')))" if server_column else "CAST('' AS varchar(128))"
    rows = db.session.execute(text(f"""
        SELECT
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            {database_select} AS PHC_DB,
            {server_select} AS PHC_SERVER
        FROM dbo.FE
        WHERE ISNULL(ATIVA, 1) = 1
        ORDER BY ISNULL(NOME, ''), ISNULL(FEID, 0)
    """)).mappings().all()
    return [
        {
            "feid": int(row.get("FEID") or 0),
            "nome": str(row.get("NOME") or "").strip(),
            "phc_configured": bool(str(row.get("PHC_DB") or "").strip()),
        }
        for row in rows
        if int(row.get("FEID") or 0)
    ]


def _collaborator_user_company(feid: int) -> dict | None:
    columns = _portal_table_columns("FE")
    database_column = _first_existing_column(columns, [
        "PHC_DATABASE", "PHC_DB", "DBPHC", "BDPHC",
        "ERP_DATABASE", "ERP_DB", "DBERP", "BDERP",
        "DATABASE_NAME", "DB_NAME", "DBNAME",
        "BASEDADOS", "BASE_DADOS", "BD", "NOMEBD",
    ])
    server_column = _first_existing_column(columns, [
        "PHC_SERVER", "SERVER_PHC", "ERP_SERVER", "SERVER_ERP",
        "SQLSERVER", "SQL_SERVER", "SERVIDOR", "SERVER",
    ])
    database_select = f"LTRIM(RTRIM(ISNULL([{database_column}], '')))" if database_column else "CAST('' AS varchar(128))"
    server_select = f"LTRIM(RTRIM(ISNULL([{server_column}], '')))" if server_column else "CAST('' AS varchar(128))"
    row = db.session.execute(text(f"""
        SELECT TOP 1
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            {database_select} AS PHC_DB,
            {server_select} AS PHC_SERVER
        FROM dbo.FE
        WHERE ISNULL(FEID, 0) = :feid
          AND ISNULL(ATIVA, 1) = 1
    """), {"feid": int(feid or 0)}).mappings().first()
    return dict(row) if row else None


def _source_table_columns(cursor, table_name: str) -> set[str]:
    cursor.execute("""
        SELECT LOWER(COLUMN_NAME) AS COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
    """, str(table_name or "").strip())
    return {str(row[0] or "").strip().lower() for row in cursor.fetchall()}


def _read_company_employees(company: dict, query: str = "", employee_no: int = 0) -> list[dict]:
    database_name = str(company.get("PHC_DB") or "").strip()
    if not database_name:
        raise ValueError("A empresa selecionada não tem uma base PHC configurada.")

    conn_str = _phc_conn_str(database_name, company.get("PHC_SERVER") or "")
    with pyodbc.connect(conn_str, timeout=12) as conn:
        cursor = conn.cursor()
        columns = _source_table_columns(cursor, "PE")
        missing = sorted({"no", "nome"} - columns)
        if missing:
            raise ValueError(f"A tabela PE não contém os campos necessários: {', '.join(missing)}.")

        status_select = "ISNULL(CONVERT(int, PE.STATUS), 1)" if "status" in columns else "1"
        status_filter = "ISNULL(PE.STATUS, 1) <> 3" if "status" in columns else ""
        stadesc_select = (
            "LTRIM(RTRIM(ISNULL(CONVERT(varchar(120), PE.STADESC), '')))"
            if "stadesc" in columns else "CAST('' AS varchar(120))"
        )
        email_select = (
            "LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), PE.EMAIL), '')))"
            if "email" in columns else "CAST('' AS varchar(160))"
        )
        ncont_select = (
            "LTRIM(RTRIM(ISNULL(CONVERT(varchar(40), PE.NCONT), '')))"
            if "ncont" in columns else "CAST('' AS varchar(40))"
        )

        where_parts = ["ISNULL(PE.NO, 0) <> 0", status_filter]
        params: list = []
        if int(employee_no or 0):
            where_parts.append("PE.NO = ?")
            params.append(int(employee_no))
        else:
            clean_query = str(query or "").strip()[:80]
            if clean_query:
                like_value = f"%{clean_query}%"
                search_parts = [
                    "LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), PE.NOME), ''))) LIKE ?",
                    "CONVERT(varchar(20), PE.NO) LIKE ?",
                ]
                params.extend([like_value, like_value])
                if "email" in columns:
                    search_parts.append("LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), PE.EMAIL), ''))) LIKE ?")
                    params.append(like_value)
                if "ncont" in columns:
                    search_parts.append("LTRIM(RTRIM(ISNULL(CONVERT(varchar(40), PE.NCONT), ''))) LIKE ?")
                    params.append(like_value)
                where_parts.append("(" + " OR ".join(search_parts) + ")")

        where_sql = " AND ".join(part for part in where_parts if part)
        cursor.execute(f"""
            SELECT TOP 200
                ISNULL(CONVERT(int, PE.NO), 0) AS NO,
                LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), PE.NOME), ''))) AS NOME,
                {status_select} AS STATUS,
                {stadesc_select} AS STADESC,
                {email_select} AS EMAIL,
                {ncont_select} AS NCONT
            FROM dbo.PE AS PE
            WHERE {where_sql}
            ORDER BY LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), PE.NOME), ''))), PE.NO
        """, *params)
        return [
            {
                "no": int(row.NO or 0),
                "nome": str(row.NOME or "").strip(),
                "status": int(row.STATUS or 0),
                "estado": str(row.STADESC or "").strip(),
                "email": str(row.EMAIL or "").strip(),
                "ncont": str(row.NCONT or "").strip(),
            }
            for row in cursor.fetchall()
            if int(row.NO or 0)
        ]


def collaborator_user_employee_options(feid: int, query: str = "") -> dict:
    company = _collaborator_user_company(int(feid or 0))
    if not company:
        raise ValueError("Empresa inválida ou inativa.")
    rows = _read_company_employees(company, query=query)
    return {
        "ok": True,
        "empresa": {"feid": int(company["FEID"]), "nome": str(company.get("NOME") or "").strip()},
        "rows": rows,
        "limited": len(rows) >= 200,
    }


def _collaborator_user_employee(feid: int, employee_no: int) -> tuple[dict, dict]:
    company = _collaborator_user_company(int(feid or 0))
    if not company:
        raise ValueError("Empresa inválida ou inativa.")
    rows = _read_company_employees(company, employee_no=int(employee_no or 0))
    if not rows:
        raise ValueError("O funcionário selecionado não existe ou já não está ativo nessa empresa.")
    return company, rows[0]


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
            vendedor_sql = "ISNULL(CONVERT(int, vendedor), 0)" if "vendedor" in columns else "0"
            cursor.execute(f"""
                SELECT
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), username), ''))) AS username,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), usercode), ''))) AS usercode,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), email), ''))) AS email,
                    LTRIM(RTRIM(ISNULL(CONVERT(varchar(250), aextpw), ''))) AS aextpw,
                    {vendedor_sql} AS vendedor
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
                    "vendedor": int(row.vendedor or 0),
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


def _generated_missing_email(login: str) -> str:
    clean_login = re.sub(r"[^A-Za-z0-9._-]+", "", str(login or "").strip()) or "user"
    clean_login = clean_login[:40].strip(".-_") or "user"
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"sem-email-{clean_login}-{stamp}-{suffix}@phc.local"[:120]


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
                    "vendedor": int(row.get("vendedor") or 0),
                    "vendedor_intersol": False,
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
            source_is_intersol = str(source.get("PHC_DB") or "").strip().casefold() == "intersol"
            source_vendedor = int(row.get("vendedor") or 0)
            if source_is_intersol:
                item["vendedor"] = source_vendedor
                item["vendedor_intersol"] = True
            elif not item.get("vendedor_intersol") and not item.get("vendedor") and source_vendedor:
                item["vendedor"] = source_vendedor
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
            item["status"] = "Sem email; será gerado ao importar"
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
    home = str(row.get("home") or "").strip().strip("/")[:120]
    vendedor = int(row.get("vendedor") or 0)
    if not email:
        email = _generated_missing_email(login)
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
                   PASSWORD = :password,
                   VENDEDOR = :vendedor
             WHERE USSTAMP = :usstamp
        """), {
            "nome": nome,
            "email": email,
            "password": password,
            "vendedor": vendedor,
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
            IS_ACTIVE, PENO, PENOME, MOTORISTA, VENDEDOR
        )
        VALUES
        (
            :USSTAMP, :NOME, :LOGIN, :PASSWORD, :EMAIL,
            0, '', '', 0, :HOME, 0, 0, 0,
            '', '', 0, '', 0, 0, 'LIGHT MODE',
            0, 0, 0,
            1, 0, '', '', :VENDEDOR
        )
    """), {
        "USSTAMP": usstamp,
        "NOME": nome,
        "LOGIN": login[:60],
        "PASSWORD": password,
        "EMAIL": email,
        "HOME": home,
        "VENDEDOR": vendedor,
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


def _ensure_collaborator_accesses(login: str, usstamp: str) -> None:
    """Grant only the self-service modules available to a collaborator."""
    access_levels = {
        "DESPESAS": {"consultar": 1, "inserir": 1, "editar": 1, "eliminar": 0},
        "FERIAS": {"consultar": 1, "inserir": 1, "editar": 1, "eliminar": 0},
        "RECIBOS": {"consultar": 1, "inserir": 0, "editar": 0, "eliminar": 0},
    }
    for table_name, permissions in access_levels.items():
        existing = db.session.execute(text("""
            SELECT TOP 1 ACESSOSSTAMP
            FROM dbo.ACESSOS
            WHERE UPPER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = :login
              AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :tabela
        """), {"login": login.upper(), "tabela": table_name}).mappings().first()
        params = {
            "utilizador": login,
            "tabela": table_name,
            "consultar": permissions["consultar"],
            "inserir": permissions["inserir"],
            "editar": permissions["editar"],
            "eliminar": permissions["eliminar"],
            "usstamp": usstamp,
        }
        if existing:
            db.session.execute(text("""
                UPDATE dbo.ACESSOS
                   SET CONSULTAR = :consultar,
                       INSERIR = :inserir,
                       EDITAR = :editar,
                       ELIMINAR = :eliminar,
                       USSTAMP = :usstamp
                 WHERE ACESSOSSTAMP = :acessosstamp
            """), {**params, "acessosstamp": existing.get("ACESSOSSTAMP")})
            continue
        db.session.execute(text("""
            INSERT INTO dbo.ACESSOS
            (ACESSOSSTAMP, UTILIZADOR, TABELA, CONSULTAR, INSERIR, EDITAR, ELIMINAR, USSTAMP)
            VALUES
            (:acessosstamp, :utilizador, :tabela, :consultar, :inserir, :editar, :eliminar, :usstamp)
        """), {**params, "acessosstamp": uuid.uuid4().hex.upper()[:25]})


def _local_us_columns() -> set[str]:
    return _portal_table_columns("US")


def _require_employee_link_columns() -> set[str]:
    columns = _local_us_columns()
    missing = sorted({"PENO", "PENOME", "PEFEID"} - columns)
    if missing:
        raise RuntimeError(
            "A estrutura de utilizadores não suporta a associação ao funcionário PHC. "
            "Execute a migration migrations/us_employee_link.sql."
        )
    return columns


def _employee_link_conflict(pefeid: int, peno: int) -> dict | None:
    columns = _require_employee_link_columns()
    active_filter = "AND ISNULL(IS_ACTIVE, 1) = 1" if "IS_ACTIVE" in columns else ""
    row = db.session.execute(text(f"""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS USSTAMP,
            LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
        FROM dbo.US
        WHERE ISNULL(PEFEID, 0) = :pefeid
          AND ISNULL(PENO, 0) = :peno
          AND ISNULL(INATIVO, 0) = 0
          {active_filter}
        ORDER BY LOGIN
    """), {"pefeid": int(pefeid), "peno": int(peno)}).mappings().first()
    return dict(row) if row else None


def _set_user_employee_link(usstamp: str, company: dict, employee: dict) -> None:
    columns = _require_employee_link_columns()
    assignments = ["PENO = :peno", "PENOME = :penome", "PEFEID = :pefeid"]
    params = {
        "peno": int(employee.get("no") or 0),
        "penome": str(employee.get("nome") or "").strip()[:60],
        "pefeid": int(company.get("FEID") or 0),
        "usstamp": str(usstamp or "").strip(),
    }
    if "PEEMPRESA" in columns:
        assignments.append("PEEMPRESA = :peempresa")
        params["peempresa"] = str(company.get("NOME") or "").strip()[:120]
    db.session.execute(text(f"""
        UPDATE dbo.US
           SET {', '.join(assignments)}
         WHERE USSTAMP = :usstamp
    """), params)


def _set_initial_password_hash(usstamp: str, password: str) -> None:
    columns = _local_us_columns()
    if not {"PASSWORD_HASH", "PASSWORD_ALGO"}.issubset(columns):
        return
    password_hash, password_algo = hash_password(password)
    assignments = [
        "PASSWORD_HASH = :password_hash",
        "PASSWORD_ALGO = :password_algo",
    ]
    if "PASSWORD_MIGRADA" in columns:
        assignments.append("PASSWORD_MIGRADA = 1")
    if "PASSWORD_CHANGED_AT" in columns:
        assignments.append("PASSWORD_CHANGED_AT = :changed_at")
    db.session.execute(text(f"""
        UPDATE dbo.US
           SET {', '.join(assignments)}
         WHERE USSTAMP = :usstamp
    """), {
        "password_hash": password_hash,
        "password_algo": password_algo,
        "changed_at": datetime.now(),
        "usstamp": str(usstamp or "").strip(),
    })


def create_collaborator_user(payload: dict, user_login: str) -> dict:
    """Create a GR360-only login linked to an employee from a selected PHC company."""
    payload = payload if isinstance(payload, dict) else {}
    nome = str(payload.get("nome") or "").strip()
    login = str(payload.get("login") or "").strip()
    password = str(payload.get("password") or "").strip()
    email = str(payload.get("email") or "").strip()
    raw_feids = payload.get("feids") if isinstance(payload.get("feids"), list) else []
    try:
        employer_feid = int(payload.get("employer_feid") or 0)
        employee_no = int(payload.get("employee_no") or 0)
        principal_feid = int(payload.get("principal_feid") or 0)
    except (TypeError, ValueError):
        raise ValueError("Empresa ou funcionário inválido.")

    if not nome:
        raise ValueError("Nome em falta.")
    if not login:
        raise ValueError("Login em falta.")
    if not password:
        raise ValueError("Password em falta.")
    if len(password) < 4:
        raise ValueError("A password deve ter pelo menos 4 caracteres.")
    if not email or "@" not in email:
        raise ValueError("Indique um email válido.")
    if len(nome) > 60 or len(login) > 60 or len(password) > 128 or len(email) > 120:
        raise ValueError("Um dos campos excede o tamanho permitido.")

    feids: list[int] = []
    for value in raw_feids:
        try:
            feid = int(value)
        except (TypeError, ValueError):
            continue
        if feid and feid not in feids:
            feids.append(feid)
    if not feids:
        raise ValueError("Selecione pelo menos uma empresa.")
    if not employer_feid:
        raise ValueError("Selecione a empresa onde o colaborador trabalha.")
    if not employee_no:
        raise ValueError("Selecione o funcionário da empresa.")
    if employer_feid not in feids:
        raise ValueError("A empresa onde o colaborador trabalha também deve estar nas empresas acessíveis.")
    if not principal_feid:
        principal_feid = employer_feid
    if principal_feid not in feids:
        raise ValueError("A empresa principal deve fazer parte das empresas acessíveis.")

    available_feids = {row["feid"] for row in collaborator_user_company_options()}
    invalid_feids = [str(feid) for feid in feids if feid not in available_feids]
    if invalid_feids:
        raise ValueError("Uma das empresas selecionadas deixou de estar disponível.")
    if _find_local_user_by_login(login):
        raise ValueError(f"Já existe um utilizador com o login {login}.")
    if _email_conflict(email):
        raise ValueError(f"Já existe um utilizador com o email {email}.")

    employer, employee = _collaborator_user_employee(employer_feid, employee_no)
    employee_conflict = _employee_link_conflict(employer_feid, employee_no)
    if employee_conflict:
        raise ValueError(
            f"O funcionário {employee.get('nome') or employee_no} já está associado "
            f"ao utilizador {employee_conflict.get('LOGIN') or employee_conflict.get('NOME') or '-'}."
        )

    with db.session.begin_nested():
        usstamp, created = _insert_or_update_user({
            "nome": nome,
            "login": login,
            "password": password,
            "email": email,
            "home": "dashboard",
            "vendedor": 0,
        })
        if not created:
            raise ValueError(f"Já existe um utilizador com o login {login}.")
        _set_initial_password_hash(usstamp, password)
        _set_user_employee_link(usstamp, employer, employee)
        for feid in feids:
            _ensure_user_company(usstamp, feid, feid == principal_feid, user_login)
        _ensure_collaborator_accesses(login, usstamp)
    db.session.commit()
    return {
        "ok": True,
        "usstamp": usstamp,
        "login": login,
        "empresas": len(feids),
        "employee": {
            "pefeid": employer_feid,
            "peno": employee_no,
            "penome": str(employee.get("nome") or "").strip(),
        },
    }


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
