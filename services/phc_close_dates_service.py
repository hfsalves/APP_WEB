from __future__ import annotations

from datetime import date, datetime
import uuid
from typing import Any

import pyodbc
from flask import current_app
from sqlalchemy import text

from models import db
from services.obra_360_service import is_gr360_hub_context
from services.opc_phc_info_service import _phc_conn_str


PARAMETER_NAME = "GE_FECHO"
MENU_URL = "/phc-close-dates"
MENU_STAMP = "PHCCLOSEDATEADMIN00000001"
MENU_OBJECT_KEY = "PHC_CLOSE_DATES"


class PhcCloseDatesError(Exception):
    pass


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _parse_close_date(value: Any) -> date | None:
    if value is None or _clean(value) == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _clean(value)
    for pattern in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    return None


def _format_close_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _ensure_gr360_admin() -> None:
    if not is_gr360_hub_context():
        raise PhcCloseDatesError("Esta configuração está disponível apenas no contexto GR360.")


def _companies() -> list[dict[str, Any]]:
    rows = db.session.execute(text("""
        SELECT
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(PHC_DB, ''))) AS PHC_DB,
            LTRIM(RTRIM(ISNULL(PHC_SERVER, ''))) AS PHC_SERVER
        FROM dbo.FE
        WHERE ISNULL(ATIVA, 1) = 1
          AND ISNULL(FEID, 0) <> 0
          AND LTRIM(RTRIM(ISNULL(PHC_DB, ''))) <> ''
        ORDER BY LTRIM(RTRIM(ISNULL(NOME, '')))
    """)).mappings().all()
    return [
        {
            "feid": int(row["FEID"] or 0),
            "name": _clean(row["NOME"]),
            "phc_db": _clean(row["PHC_DB"]),
            "phc_server": _clean(row["PHC_SERVER"]),
        }
        for row in rows
    ]


def _find_company(feid: int) -> dict[str, Any] | None:
    return next((company for company in _companies() if company["feid"] == int(feid)), None)


def _read_parameter(company: dict[str, Any]) -> dict[str, Any]:
    try:
        with pyodbc.connect(
            _phc_conn_str(company["phc_db"], company["phc_server"]), timeout=10
        ) as connection:
            row = connection.cursor().execute("""
                SELECT TOP 1 LTRIM(RTRIM(ISNULL(VALOR, ''))) AS VALOR
                FROM dbo.PARA1 WITH (NOLOCK)
                WHERE UPPER(LTRIM(RTRIM(ISNULL(DESCRICAO, '')))) = ?
            """, PARAMETER_NAME).fetchone()
    except pyodbc.Error as exc:
        return {"status": "error", "message": f"Não foi possível ler a base PHC: {str(exc)}"}

    if not row:
        return {"status": "missing", "message": "Parâmetro GE_FECHO não encontrado."}

    raw_value = _clean(row[0])
    parsed = _parse_close_date(raw_value)
    if raw_value and not parsed:
        return {
            "status": "invalid",
            "message": f"Valor atual inválido no PHC: {raw_value}",
            "raw_value": raw_value,
        }
    return {
        "status": "ok",
        "value": parsed.isoformat() if parsed else "",
        "display_value": _format_close_date(parsed) if parsed else "Sem data definida",
    }


def list_close_dates() -> list[dict[str, Any]]:
    _ensure_gr360_admin()
    items: list[dict[str, Any]] = []
    for company in _companies():
        item = {**company, **_read_parameter(company)}
        items.append(item)
    return items


def update_close_date(feid: int, value: Any) -> dict[str, Any]:
    _ensure_gr360_admin()
    company = _find_company(feid)
    if not company:
        raise PhcCloseDatesError("Empresa PHC não encontrada.")

    parsed = _parse_close_date(value)
    if not parsed or _clean(value) != parsed.isoformat():
        raise PhcCloseDatesError("Indique uma data válida.")

    try:
        with pyodbc.connect(
            _phc_conn_str(company["phc_db"], company["phc_server"]), timeout=10
        ) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE dbo.PARA1
                SET VALOR = ?
                WHERE UPPER(LTRIM(RTRIM(ISNULL(DESCRICAO, '')))) = ?
            """, _format_close_date(parsed), PARAMETER_NAME)
            if cursor.rowcount != 1:
                connection.rollback()
                raise PhcCloseDatesError("O parâmetro GE_FECHO não existe nesta base PHC.")
            connection.commit()
    except PhcCloseDatesError:
        raise
    except pyodbc.Error as exc:
        raise PhcCloseDatesError(f"Não foi possível gravar a data fechada: {str(exc)}") from exc

    return {
        **company,
        "status": "ok",
        "value": parsed.isoformat(),
        "display_value": _format_close_date(parsed),
    }


def update_all_close_dates(value: Any) -> list[dict[str, Any]]:
    """Apply a date independently to every configured PHC database."""
    parsed = _parse_close_date(value)
    if not parsed or _clean(value) != parsed.isoformat():
        raise PhcCloseDatesError("Indique uma data válida.")

    results: list[dict[str, Any]] = []
    for company in _companies():
        try:
            item = update_close_date(company["feid"], parsed.isoformat())
            results.append({"feid": company["feid"], "ok": True, "item": item})
        except PhcCloseDatesError as exc:
            results.append({"feid": company["feid"], "ok": False, "error": str(exc)})
    return results


def ensure_phc_close_dates_menu() -> None:
    """Register the Admin entry only in GR360_CORE."""
    expected_database = _clean(current_app.config.get("GR360_HUB_EXPECTED_DATABASE", "GR360_CORE")).upper()
    current_database = _clean(current_app.config.get("DB_CLIENT_NAME")).upper()
    if current_database and current_database != expected_database:
        return

    exists = db.session.execute(text("""
        SELECT TOP 1 1 FROM dbo.MENU
        WHERE LTRIM(RTRIM(ISNULL(URL, ''))) = :url
    """), {"url": MENU_URL}).scalar()
    if not exists:
        db.session.execute(text("""
            INSERT INTO dbo.MENU (
                MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
            ) VALUES (
                :stamp, 825, 'Data fechada PHC', 'PARA1', :url, 1,
                'fa-solid fa-calendar-xmark', '', '', 0, 0
            )
        """), {"stamp": MENU_STAMP, "url": MENU_URL})

    admin_module = db.session.execute(text("""
        SELECT TOP 1 MODSTAMP
        FROM dbo.MODULOS
        WHERE UPPER(LTRIM(RTRIM(ISNULL(NOME, '')))) = 'ADMIN'
    """)).scalar()
    if admin_module:
        object_exists = db.session.execute(text("""
            SELECT TOP 1 1 FROM dbo.MOD_OBJETOS
            WHERE MODSTAMP = :modstamp AND OBJKEY = :objkey
        """), {"modstamp": _clean(admin_module), "objkey": MENU_OBJECT_KEY}).scalar()
        if not object_exists:
            db.session.execute(text("""
                INSERT INTO dbo.MOD_OBJETOS (
                    MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA, MENUSTAMP,
                    ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO
                ) VALUES (
                    :stamp, :modstamp, 'MENU', :objkey, 'Data fechada PHC', :url, :menustamp,
                    825, 1, GETDATE(), 'APP', 'APP'
                )
            """), {
                "stamp": _stamp(),
                "modstamp": _clean(admin_module),
                "objkey": MENU_OBJECT_KEY,
                "url": MENU_URL,
                "menustamp": MENU_STAMP,
            })
    db.session.commit()
