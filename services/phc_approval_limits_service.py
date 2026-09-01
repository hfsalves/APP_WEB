from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import uuid
from typing import Any

import pyodbc
from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from models import db
from services.obra_360_service import is_gr360_hub_context
from services.opc_phc_info_service import _phc_conn_str


MASTER_DATABASE = "HSOLS_MASTER"
MENU_URL = "/approval-limits"
MENU_STAMP = "PHCAPROVALLIMITADMIN00001"
MENU_OBJECT_KEY = "PHC_APPROVAL_LIMITS"
MAX_LIMIT = Decimal("99999999999999999.99")


class PhcApprovalLimitsError(Exception):
    status_code = 400


class PhcApprovalLimitsNotFoundError(PhcApprovalLimitsError):
    status_code = 404


class PhcApprovalLimitsConflictError(PhcApprovalLimitsError):
    status_code = 409


def _clean(value: Any, maximum: int = 0) -> str:
    result = str(value or "").strip()
    return result[:maximum] if maximum else result


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _master_database() -> str:
    return _clean(current_app.config.get("PHC_MASTER_DATABASE") or MASTER_DATABASE, 128)


def _ensure_context() -> None:
    if not is_gr360_hub_context():
        raise PhcApprovalLimitsNotFoundError(
            "Esta configuração está disponível apenas no contexto GR360."
        )


def _connection():
    return pyodbc.connect(_phc_conn_str(_master_database()), timeout=15)


def _actor_initials(cursor, user) -> str:
    login = _clean(getattr(user, "LOGIN", ""), 20)
    if login:
        row = cursor.execute(
            """
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(INICIAIS, '')))
            FROM dbo.US WITH (NOLOCK)
            WHERE UPPER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = UPPER(?)
            ORDER BY ISNULL(INACTIVO, 0), USERNO
            """,
            login,
        ).fetchone()
        if row and _clean(row[0]):
            return _clean(row[0], 30)
    return _clean(login or "APP", 30)


def _parse_limit(value: Any) -> Decimal:
    raw = _clean(value).replace(" ", "").replace(",", ".")
    try:
        amount = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise PhcApprovalLimitsError("Indique um plafond válido.")
    if amount < 0:
        raise PhcApprovalLimitsError("O plafond não pode ser negativo.")
    if amount > MAX_LIMIT:
        raise PhcApprovalLimitsError("O plafond excede o limite permitido pelo PHC.")
    return amount


def _app_users() -> list[dict[str, Any]]:
    rows = db.session.execute(
        text("""
            SELECT
                LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS USERCODE,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS USERNAME,
                ISNULL(INATIVO, 0) AS INATIVO
            FROM dbo.US
            WHERE LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
            ORDER BY ISNULL(INATIVO, 0), NOME, LOGIN
        """)
    ).mappings().all()
    return [
        {
            "usercode": _clean(row.get("USERCODE"), 20),
            "username": _clean(row.get("USERNAME"), 30),
            "inactive": bool(row.get("INATIVO")),
        }
        for row in rows
    ]


def _user_row(_cursor, usercode: Any) -> dict[str, str]:
    clean_code = _clean(usercode, 20)
    if not clean_code:
        raise PhcApprovalLimitsError("Selecione um utilizador da aplicação.")
    selected = next(
        (
            user
            for user in _app_users()
            if _clean(user.get("usercode"), 20).casefold() == clean_code.casefold()
        ),
        None,
    )
    if not selected:
        raise PhcApprovalLimitsError("O utilizador selecionado não existe na aplicação.")
    return {
        "usercode": _clean(selected.get("usercode"), 20),
        "username": _clean(selected.get("username"), 30),
    }


def _item(row) -> dict[str, Any]:
    updated = row[7]
    return {
        "stamp": _clean(row[0], 25),
        "usercode": _clean(row[1], 20),
        "username": _clean(row[2], 30),
        "plafond": f"{Decimal(row[3] or 0):.2f}",
        "created_by": _clean(row[4], 30),
        "created_at": row[5].isoformat() if row[5] else "",
        "updated_by": _clean(row[6], 30),
        "updated_at": updated.isoformat() if updated else "",
        "duplicate_count": int(row[8] or 0),
    }


def list_approval_limits() -> list[dict[str, Any]]:
    _ensure_context()
    try:
        with _connection() as connection:
            rows = connection.cursor().execute(
                """
                SELECT
                    LTRIM(RTRIM(ISNULL(U_APROPLAFSTAMP, ''))) AS U_APROPLAFSTAMP,
                    LTRIM(RTRIM(ISNULL(USERCODE, ''))) AS USERCODE,
                    LTRIM(RTRIM(ISNULL(USERNAME, ''))) AS USERNAME,
                    ISNULL(PLAFOND, 0) AS PLAFOND,
                    LTRIM(RTRIM(ISNULL(OUSRINIS, ''))) AS OUSRINIS,
                    OUSRDATA,
                    LTRIM(RTRIM(ISNULL(USRINIS, ''))) AS USRINIS,
                    USRDATA,
                    COUNT(*) OVER (
                        PARTITION BY UPPER(LTRIM(RTRIM(ISNULL(USERCODE, ''))))
                    ) AS DUPLICATE_COUNT
                FROM dbo.U_APROPLAF WITH (NOLOCK)
                ORDER BY USERNAME, USERCODE, USRDATA DESC, U_APROPLAFSTAMP
                """
            ).fetchall()
    except pyodbc.Error as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível ler os plafonds no PHC: {str(exc)}"
        ) from exc
    return [_item(row) for row in rows]


def list_phc_users() -> list[dict[str, Any]]:
    _ensure_context()
    try:
        users = _app_users()
    except SQLAlchemyError as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível ler os utilizadores da aplicação: {str(exc)}"
        ) from exc
    return [
        {
            "usercode": _clean(user.get("usercode"), 20),
            "username": _clean(user.get("username"), 30),
            "inactive": bool(user.get("inactive")),
        }
        for user in users
    ]


def create_approval_limit(payload: dict[str, Any], user) -> dict[str, Any]:
    _ensure_context()
    amount = _parse_limit(payload.get("plafond"))
    try:
        with _connection() as connection:
            connection.autocommit = False
            cursor = connection.cursor()
            selected_user = _user_row(cursor, payload.get("usercode"))
            duplicate = cursor.execute(
                """
                SELECT TOP 1 1
                FROM dbo.U_APROPLAF WITH (UPDLOCK, HOLDLOCK)
                WHERE UPPER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = UPPER(?)
                """,
                selected_user["usercode"],
            ).fetchone()
            if duplicate:
                raise PhcApprovalLimitsConflictError(
                    "Já existe um plafond para este utilizador. Edite o registo existente."
                )

            now = datetime.now()
            actor = _actor_initials(cursor, user)
            stamp = _stamp()
            cursor.execute(
                """
                INSERT INTO dbo.U_APROPLAF (
                    U_APROPLAFSTAMP, USERCODE, USERNAME, PLAFOND,
                    OUSRINIS, OUSRDATA, OUSRHORA,
                    USRINIS, USRDATA, USRHORA, MARCADA
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                stamp,
                selected_user["usercode"],
                selected_user["username"],
                amount,
                actor,
                now,
                now.strftime("%H:%M:%S"),
                actor,
                now,
                now.strftime("%H:%M:%S"),
            )
            connection.commit()
    except PhcApprovalLimitsError:
        raise
    except pyodbc.Error as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível criar o plafond no PHC: {str(exc)}"
        ) from exc
    return get_approval_limit(stamp)


def get_approval_limit(stamp: Any) -> dict[str, Any]:
    _ensure_context()
    clean_stamp = _clean(stamp, 25)
    try:
        with _connection() as connection:
            row = connection.cursor().execute(
                """
                SELECT
                    LTRIM(RTRIM(ISNULL(U_APROPLAFSTAMP, ''))),
                    LTRIM(RTRIM(ISNULL(USERCODE, ''))),
                    LTRIM(RTRIM(ISNULL(USERNAME, ''))),
                    ISNULL(PLAFOND, 0),
                    LTRIM(RTRIM(ISNULL(OUSRINIS, ''))), OUSRDATA,
                    LTRIM(RTRIM(ISNULL(USRINIS, ''))), USRDATA,
                    (SELECT COUNT(*) FROM dbo.U_APROPLAF D
                     WHERE UPPER(LTRIM(RTRIM(ISNULL(D.USERCODE, '')))) =
                           UPPER(LTRIM(RTRIM(ISNULL(U_APROPLAF.USERCODE, '')))))
                FROM dbo.U_APROPLAF WITH (NOLOCK)
                WHERE U_APROPLAFSTAMP = ?
                """,
                clean_stamp,
            ).fetchone()
    except pyodbc.Error as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível ler o plafond no PHC: {str(exc)}"
        ) from exc
    if not row:
        raise PhcApprovalLimitsNotFoundError("O plafond indicado já não existe.")
    return _item(row)


def update_approval_limit(stamp: Any, payload: dict[str, Any], user) -> dict[str, Any]:
    _ensure_context()
    clean_stamp = _clean(stamp, 25)
    amount = _parse_limit(payload.get("plafond"))
    try:
        with _connection() as connection:
            connection.autocommit = False
            cursor = connection.cursor()
            exists = cursor.execute(
                "SELECT TOP 1 1 FROM dbo.U_APROPLAF WITH (UPDLOCK, HOLDLOCK) WHERE U_APROPLAFSTAMP = ?",
                clean_stamp,
            ).fetchone()
            if not exists:
                raise PhcApprovalLimitsNotFoundError("O plafond indicado já não existe.")

            selected_user = _user_row(cursor, payload.get("usercode"))
            duplicate = cursor.execute(
                """
                SELECT TOP 1 1
                FROM dbo.U_APROPLAF WITH (UPDLOCK, HOLDLOCK)
                WHERE U_APROPLAFSTAMP <> ?
                  AND UPPER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = UPPER(?)
                """,
                clean_stamp,
                selected_user["usercode"],
            ).fetchone()
            if duplicate:
                raise PhcApprovalLimitsConflictError(
                    "Já existe outro plafond para este utilizador. Elimine o duplicado antes de alterar este registo."
                )

            now = datetime.now()
            actor = _actor_initials(cursor, user)
            cursor.execute(
                """
                UPDATE dbo.U_APROPLAF
                SET USERCODE = ?, USERNAME = ?, PLAFOND = ?,
                    USRINIS = ?, USRDATA = ?, USRHORA = ?
                WHERE U_APROPLAFSTAMP = ?
                """,
                selected_user["usercode"],
                selected_user["username"],
                amount,
                actor,
                now,
                now.strftime("%H:%M:%S"),
                clean_stamp,
            )
            connection.commit()
    except PhcApprovalLimitsError:
        raise
    except pyodbc.Error as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível atualizar o plafond no PHC: {str(exc)}"
        ) from exc
    return get_approval_limit(clean_stamp)


def delete_approval_limit(stamp: Any) -> None:
    _ensure_context()
    clean_stamp = _clean(stamp, 25)
    try:
        with _connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM dbo.U_APROPLAF WHERE U_APROPLAFSTAMP = ?",
                clean_stamp,
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise PhcApprovalLimitsNotFoundError("O plafond indicado já não existe.")
            connection.commit()
    except PhcApprovalLimitsError:
        raise
    except pyodbc.Error as exc:
        raise PhcApprovalLimitsError(
            f"Não foi possível eliminar o plafond no PHC: {str(exc)}"
        ) from exc


def ensure_phc_approval_limits_menu() -> None:
    expected_database = _clean(
        current_app.config.get("GR360_HUB_EXPECTED_DATABASE", "GR360_CORE")
    ).upper()
    current_database = _clean(current_app.config.get("DB_CLIENT_NAME")).upper()
    if current_database and current_database != expected_database:
        return

    exists = db.session.execute(
        text("""
            SELECT TOP 1 1 FROM dbo.MENU
            WHERE LTRIM(RTRIM(ISNULL(URL, ''))) = :url
        """),
        {"url": MENU_URL},
    ).scalar()
    if not exists:
        db.session.execute(
            text("""
                INSERT INTO dbo.MENU (
                    MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
                ) VALUES (
                    :stamp, 826, 'Plafonds de aprovação', 'U_APROPLAF', :url, 1,
                    'fa-solid fa-shield-halved', '', '', 0, 0
                )
            """),
            {"stamp": MENU_STAMP, "url": MENU_URL},
        )

    admin_module = db.session.execute(
        text("""
            SELECT TOP 1 MODSTAMP FROM dbo.MODULOS
            WHERE UPPER(LTRIM(RTRIM(ISNULL(NOME, '')))) = 'ADMIN'
        """)
    ).scalar()
    if admin_module:
        object_exists = db.session.execute(
            text("""
                SELECT TOP 1 1 FROM dbo.MOD_OBJETOS
                WHERE MODSTAMP = :modstamp AND OBJKEY = :objkey
            """),
            {"modstamp": _clean(admin_module), "objkey": MENU_OBJECT_KEY},
        ).scalar()
        if not object_exists:
            db.session.execute(
                text("""
                    INSERT INTO dbo.MOD_OBJETOS (
                        MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA, MENUSTAMP,
                        ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO
                    ) VALUES (
                        :stamp, :modstamp, 'MENU', :objkey, 'Plafonds de aprovação',
                        :url, :menustamp, 826, 1, GETDATE(), 'APP', 'APP'
                    )
                """),
                {
                    "stamp": _stamp(),
                    "modstamp": _clean(admin_module),
                    "objkey": MENU_OBJECT_KEY,
                    "url": MENU_URL,
                    "menustamp": MENU_STAMP,
                },
            )
    db.session.commit()
