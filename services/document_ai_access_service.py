from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text

from models import db
from services.document_ai_inbox_access_service import INBOX_VIEW_DEFINITIONS


PERMISSION_COLUMNS = {
    'consult': 'CAN_CONSULT',
    'create': 'CAN_CREATE',
    'analyze': 'CAN_ANALYZE',
    'delete': 'CAN_DELETE',
    'ai': 'CAN_AI',
    'associate': 'CAN_ASSOCIATE',
    'validate': 'CAN_VALIDATE',
}
VALID_VIEWS = {item['value'] for item in INBOX_VIEW_DEFINITIONS}
_schema_ready = False


def _stamp() -> str:
    return uuid.uuid4().hex[:25]


def _login(value: Any) -> str:
    return str(value or '').strip().lower()


def ensure_document_ai_access_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    migration = Path(__file__).resolve().parents[1] / 'migrations' / 'document_ai_access.sql'
    sql = migration.read_text(encoding='utf-8')
    try:
        for statement in [part.strip() for part in sql.replace('\r\n', '\n').split('\nGO\n') if part.strip()]:
            db.session.execute(text(statement))
        db.session.commit()
        _schema_ready = True
    except Exception:
        db.session.rollback()
        raise


def is_access_admin(login: Any) -> bool:
    ensure_document_ai_access_schema()
    return bool(db.session.execute(text("""
        SELECT TOP (1) 1 FROM dbo.DOC_AI_ACCESS_ADMIN
        WHERE LOWER(LTRIM(RTRIM(LOGIN))) = :login AND ATIVO = 1
    """), {'login': _login(login)}).scalar())


def allowed_views(login: Any) -> list[dict[str, str]]:
    ensure_document_ai_access_schema()
    rows = db.session.execute(text("""
        SELECT VIEW_CODE FROM dbo.DOC_AI_ACCESS
        WHERE LOWER(LTRIM(RTRIM(LOGIN))) = :login AND CAN_CONSULT = 1
    """), {'login': _login(login)}).scalars().all()
    allowed = {str(value or '').strip().lower() for value in rows}
    return [dict(item) for item in INBOX_VIEW_DEFINITIONS if item['value'] in allowed]


def permission_profile(login: Any, view: Any) -> dict[str, Any]:
    ensure_document_ai_access_schema()
    normalized_view = str(view or '').strip().lower()
    if normalized_view not in VALID_VIEWS:
        return {'view': normalized_view, 'allowed': False, 'all_entities': False, 'entity_ids': [], 'permissions': {key: False for key in PERMISSION_COLUMNS}}
    row = db.session.execute(text("""
        SELECT TOP (1) * FROM dbo.DOC_AI_ACCESS
        WHERE LOWER(LTRIM(RTRIM(LOGIN))) = :login AND VIEW_CODE = :view
    """), {'login': _login(login), 'view': normalized_view}).mappings().first()
    if not row:
        return {'view': normalized_view, 'allowed': False, 'all_entities': False, 'entity_ids': [], 'permissions': {key: False for key in PERMISSION_COLUMNS}}
    all_entities = bool(row.get('ALL_ENTITIES'))
    entity_ids: list[int] = []
    if not all_entities:
        entity_ids = [int(value) for value in db.session.execute(text("""
            SELECT FEID FROM dbo.DOC_AI_ACCESS_ENTITY WHERE DOC_AI_ACCESS_STAMP = :stamp ORDER BY FEID
        """), {'stamp': row['DOC_AI_ACCESS_STAMP']}).scalars().all()]
    permissions = {key: bool(row.get(column)) for key, column in PERMISSION_COLUMNS.items()}
    return {
        'id': str(row['DOC_AI_ACCESS_STAMP']),
        'view': normalized_view,
        'allowed': permissions['consult'] and (all_entities or bool(entity_ids)),
        'all_entities': all_entities,
        'entity_ids': entity_ids,
        'permissions': permissions,
    }


def has_permission(login: Any, view: Any, permission: str) -> bool:
    key = str(permission or '').strip().lower()
    if key not in PERMISSION_COLUMNS:
        return False
    profile = permission_profile(login, view)
    return bool(profile['allowed'] and profile['permissions'].get(key))


def can_access_document(login: Any, view: Any, permission: str, document_stamp: Any) -> bool:
    profile = permission_profile(login, view)
    if not profile['allowed'] or not profile['permissions'].get(str(permission or '').strip().lower()):
        return False
    if profile['all_entities']:
        return True
    feid = db.session.execute(text("""
        SELECT TOP (1) CAST(ISNULL(FEID, 0) AS int)
        FROM dbo.DOC_INBOX WHERE DOCINSTAMP = :stamp
    """), {'stamp': str(document_stamp or '').strip()}).scalar()
    return int(feid or 0) in set(profile['entity_ids'])


def list_access_configuration(search: str = '') -> dict[str, Any]:
    ensure_document_ai_access_schema()
    query = f"%{str(search or '').strip()}%"
    users = db.session.execute(text("""
        SELECT LOGIN, NOME FROM dbo.US
        WHERE ISNULL(INATIVO, 0) = 0
          AND (:query = '%%' OR LOGIN LIKE :query OR NOME LIKE :query)
        ORDER BY NOME, LOGIN
    """), {'query': query}).mappings().all()
    entities = db.session.execute(text("""
        SELECT CAST(FEID AS int) AS FEID, ISNULL(NULLIF(NOMEFISCAL, ''), NOME) AS NOME
        FROM dbo.FE WHERE ISNULL(ATIVA, 1) = 1 AND ISNULL(FEID, 0) > 0 ORDER BY NOME
    """)).mappings().all()
    access_rows = db.session.execute(text("SELECT * FROM dbo.DOC_AI_ACCESS ORDER BY LOGIN, VIEW_CODE")).mappings().all()
    entity_rows = db.session.execute(text("SELECT DOC_AI_ACCESS_STAMP, FEID FROM dbo.DOC_AI_ACCESS_ENTITY")).mappings().all()
    entity_map: dict[str, list[int]] = {}
    for item in entity_rows:
        entity_map.setdefault(str(item['DOC_AI_ACCESS_STAMP']), []).append(int(item['FEID']))
    admins = {_login(value) for value in db.session.execute(text("SELECT LOGIN FROM dbo.DOC_AI_ACCESS_ADMIN WHERE ATIVO=1")).scalars().all()}
    return {
        'users': [{'login': str(item['LOGIN']).strip(), 'name': str(item['NOME'] or item['LOGIN']).strip()} for item in users],
        'entities': [{'feid': int(item['FEID']), 'name': str(item['NOME'] or '').strip()} for item in entities],
        'views': [dict(item) for item in INBOX_VIEW_DEFINITIONS],
        'assignments': [{
            'id': str(row['DOC_AI_ACCESS_STAMP']),
            'login': _login(row['LOGIN']),
            'view': str(row['VIEW_CODE']),
            'all_entities': bool(row['ALL_ENTITIES']),
            'entity_ids': entity_map.get(str(row['DOC_AI_ACCESS_STAMP']), []),
            'permissions': {key: bool(row[column]) for key, column in PERMISSION_COLUMNS.items()},
        } for row in access_rows],
        'admin_logins': sorted(admins),
    }


def _snapshot(rows: list[dict[str, Any]], admins: set[str]) -> dict[str, Any]:
    return {'assignments': rows, 'admins': sorted(admins)}


def save_access_configuration(payload: dict[str, Any], actor_login: Any) -> dict[str, Any]:
    ensure_document_ai_access_schema()
    actor = _login(actor_login)
    if not is_access_admin(actor):
        raise PermissionError('Sem permissão para administrar acessos Document AI.')
    raw_assignments = payload.get('assignments') or []
    admin_logins = {_login(value) for value in (payload.get('admin_logins') or []) if _login(value)}
    if not admin_logins:
        raise ValueError('Tem de existir pelo menos um administrador de acessos ativo.')

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_assignments:
        login = _login(item.get('login'))
        view = str(item.get('view') or '').strip().lower()
        if not login or view not in VALID_VIEWS or (login, view) in seen:
            continue
        seen.add((login, view))
        all_entities = bool(item.get('all_entities'))
        entity_ids = sorted({int(value) for value in (item.get('entity_ids') or []) if str(value).isdigit() and int(value) > 0})
        permissions = {key: bool((item.get('permissions') or {}).get(key)) for key in PERMISSION_COLUMNS}
        if not all_entities and not entity_ids:
            permissions['consult'] = False
        normalized.append({'login': login, 'view': view, 'all_entities': all_entities, 'entity_ids': entity_ids, 'permissions': permissions})

    before = list_access_configuration()
    before_snapshot = _snapshot(before['assignments'], set(before['admin_logins']))
    after_snapshot = _snapshot(normalized, admin_logins)
    try:
        db.session.execute(text('DELETE FROM dbo.DOC_AI_ACCESS_ENTITY'))
        db.session.execute(text('DELETE FROM dbo.DOC_AI_ACCESS'))
        for item in normalized:
            stamp = _stamp()
            params = {'stamp': stamp, 'login': item['login'], 'view': item['view'], 'all_entities': item['all_entities'], 'actor': actor}
            params.update({column.lower(): bool(item['permissions'][key]) for key, column in PERMISSION_COLUMNS.items()})
            db.session.execute(text("""
                INSERT INTO dbo.DOC_AI_ACCESS (
                    DOC_AI_ACCESS_STAMP, LOGIN, VIEW_CODE, ALL_ENTITIES,
                    CAN_CONSULT, CAN_CREATE, CAN_ANALYZE, CAN_DELETE, CAN_AI, CAN_ASSOCIATE, CAN_VALIDATE,
                    USERCRIACAO, USERALTERACAO
                ) VALUES (
                    :stamp, :login, :view, :all_entities,
                    :can_consult, :can_create, :can_analyze, :can_delete, :can_ai, :can_associate, :can_validate,
                    :actor, :actor
                )
            """), params)
            for feid in item['entity_ids'] if not item['all_entities'] else []:
                db.session.execute(text("""
                    INSERT INTO dbo.DOC_AI_ACCESS_ENTITY
                        (DOC_AI_ACCESS_ENTITY_STAMP, DOC_AI_ACCESS_STAMP, FEID, USERCRIACAO)
                    VALUES (:stamp, :access_stamp, :feid, :actor)
                """), {'stamp': _stamp(), 'access_stamp': stamp, 'feid': feid, 'actor': actor})

        db.session.execute(text('DELETE FROM dbo.DOC_AI_ACCESS_ADMIN'))
        for login in sorted(admin_logins):
            db.session.execute(text("""
                INSERT INTO dbo.DOC_AI_ACCESS_ADMIN
                    (DOC_AI_ACCESS_ADMIN_STAMP, LOGIN, ATIVO, USERCRIACAO, USERALTERACAO)
                VALUES (:stamp, :login, 1, :actor, :actor)
            """), {'stamp': _stamp(), 'login': login, 'actor': actor})
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_ACCESS_LOG
                (DOC_AI_ACCESS_LOG_STAMP, ACTOR_LOGIN, TARGET_LOGIN, VIEW_CODE, ACTION_CODE, BEFORE_JSON, AFTER_JSON)
            VALUES (:stamp, :actor, '*', '*', 'SAVE_CONFIGURATION', :before_json, :after_json)
        """), {
            'stamp': _stamp(), 'actor': actor,
            'before_json': json.dumps(before_snapshot, ensure_ascii=False, default=str),
            'after_json': json.dumps(after_snapshot, ensure_ascii=False, default=str),
        })
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return list_access_configuration()


def scope_filters_for(login: Any, view: Any) -> dict[str, Any]:
    profile = permission_profile(login, view)
    return {
        'all_entities': bool(profile['all_entities'] and profile['allowed']),
        'allowed_feids': None if profile['all_entities'] and profile['allowed'] else list(profile['entity_ids']) if profile['allowed'] else [],
    }
