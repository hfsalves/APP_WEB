from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text

from models import db
from services.document_ai_inbox_access_service import INBOX_VIEW_DEFINITIONS


DOCUMENT_CLASSES = [
    {'value': 'mail', 'label': 'Correio'},
    {'value': 'invoice', 'label': 'Fatura'},
    {'value': 'credit_note', 'label': 'Nota de crédito'},
    {'value': 'purchase_order', 'label': 'Nota de encomenda'},
    {'value': 'delivery_note', 'label': 'Guia de remessa'},
    {'value': 'bank_statement', 'label': 'Extrato bancário'},
    {'value': 'advertising', 'label': 'Publicidade'},
]
DESTINATION_STATES = [
    {'value': 'automatic', 'label': 'Automático'},
    {'value': 'pending', 'label': 'Pendente'},
    {'value': 'validated', 'label': 'Validado'},
    {'value': 'none', 'label': '-'},
]
VALID_VIEWS = {item['value'] for item in INBOX_VIEW_DEFINITIONS}
VALID_CLASSES = {item['value'] for item in DOCUMENT_CLASSES}
VALID_STATES = {item['value'] for item in DESTINATION_STATES}
_schema_ready: set[str] = set()


def _stamp() -> str:
    return uuid.uuid4().hex[:25]


def _login(value: Any) -> str:
    return str(value or '').strip().lower()


def ensure_document_ai_distribution_schema() -> None:
    database_name = str(db.session.execute(text('SELECT DB_NAME()')).scalar() or '').strip().upper()
    if database_name in _schema_ready:
        return
    migration = Path(__file__).resolve().parents[1] / 'migrations' / 'document_ai_distribution.sql'
    sql = migration.read_text(encoding='utf-8').replace('\r\n', '\n')
    try:
        for statement in [part.strip() for part in sql.split('\nGO\n') if part.strip()]:
            db.session.execute(text(statement))
        _seed_distribution_rules()
        db.session.commit()
        _schema_ready.add(database_name)
    except Exception:
        db.session.rollback()
        raise


def _seed_distribution_rules() -> None:
    if db.session.execute(text('SELECT COUNT_BIG(1) FROM dbo.DOC_AI_DISTRIBUTION_RULE')).scalar():
        return
    defaults = [
        ('mail', 'home', None, 'none', True),
        ('invoice', 'home', 'management', 'automatic', False),
        ('invoice', 'home', 'accounting', 'pending', False),
        ('invoice', 'management', 'accounting', 'validated', False),
        ('invoice', 'accounting', None, 'none', True),
        ('credit_note', 'home', 'accounting', 'none', False),
        ('credit_note', 'accounting', None, 'none', True),
        ('advertising', 'home', None, 'none', True),
    ]
    for doc_class, source, destination, state, terminal in defaults:
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_DISTRIBUTION_RULE (
                DOC_AI_DISTRIBUTION_RULE_STAMP, DOC_CLASS, SOURCE_VIEW,
                DESTINATION_VIEW, DESTINATION_STATE, TERMINAL,
                USERCRIACAO, USERALTERACAO
            ) VALUES (:stamp, :doc_class, :source, :destination, :state, :terminal, 'system', 'system')
        """), {
            'stamp': _stamp(), 'doc_class': doc_class, 'source': source,
            'destination': destination, 'state': state, 'terminal': terminal,
        })


def _serialize_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('DOC_AI_DISTRIBUTION_RULE_STAMP') or ''),
        'doc_class': str(row.get('DOC_CLASS') or ''),
        'source': str(row.get('SOURCE_VIEW') or ''),
        'destination': str(row.get('DESTINATION_VIEW') or ''),
        'state': str(row.get('DESTINATION_STATE') or 'none'),
        'terminal': bool(row.get('TERMINAL')),
    }


def list_distribution_configuration() -> dict[str, Any]:
    ensure_document_ai_distribution_schema()
    rows = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_DISTRIBUTION_RULE
        ORDER BY DOC_CLASS, SOURCE_VIEW, DESTINATION_VIEW
    """)).mappings().all()
    return {
        'classifications': [dict(item) for item in DOCUMENT_CLASSES],
        'views': [dict(item) for item in INBOX_VIEW_DEFINITIONS],
        'states': [dict(item) for item in DESTINATION_STATES],
        'rules': [_serialize_rule(dict(row)) for row in rows],
    }


def _normalize_rule(payload: dict[str, Any]) -> dict[str, Any]:
    doc_class = str(payload.get('doc_class') or '').strip().lower()
    source = str(payload.get('source') or '').strip().lower()
    destination = str(payload.get('destination') or '').strip().lower()
    terminal = bool(payload.get('terminal')) or destination in {'', 'none', 'terminal'}
    destination = '' if terminal else destination
    state = str(payload.get('state') or 'none').strip().lower()
    if doc_class not in VALID_CLASSES:
        raise ValueError('Seleciona uma classificação válida.')
    if source not in VALID_VIEWS:
        raise ValueError('Seleciona uma origem válida.')
    if not terminal and destination not in VALID_VIEWS:
        raise ValueError('Seleciona um destino válido.')
    if destination == source:
        raise ValueError('A origem e o destino não podem ser iguais.')
    if terminal:
        state = 'none'
    if state not in VALID_STATES:
        raise ValueError('Seleciona um estado válido.')
    if destination == 'management' and state != 'automatic':
        raise ValueError('O Controlo de Gestão usa o estado Automático.')
    if destination == 'accounting' and doc_class == 'invoice' and state not in {'pending', 'validated'}:
        raise ValueError('A Contabilidade de Faturas usa Pendente ou Validado.')
    if destination == 'accounting' and doc_class == 'credit_note' and state != 'none':
        raise ValueError('A Nota de crédito entra na Contabilidade sem estado.')
    return {
        'doc_class': doc_class, 'source': source, 'destination': destination,
        'state': state, 'terminal': terminal,
    }


def _assert_no_cycle(candidate: dict[str, Any], excluded_id: str = '') -> None:
    rows = db.session.execute(text("""
        SELECT DOC_AI_DISTRIBUTION_RULE_STAMP, DOC_CLASS, SOURCE_VIEW, DESTINATION_VIEW, TERMINAL
        FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_CLASS = :doc_class
    """), {'doc_class': candidate['doc_class']}).mappings().all()
    edges: dict[str, set[str]] = {}
    for row in rows:
        if str(row.get('DOC_AI_DISTRIBUTION_RULE_STAMP') or '') == excluded_id or bool(row.get('TERMINAL')):
            continue
        edges.setdefault(str(row.get('SOURCE_VIEW') or ''), set()).add(str(row.get('DESTINATION_VIEW') or ''))
    if not candidate['terminal']:
        edges.setdefault(candidate['source'], set()).add(candidate['destination'])

    def visits(node: str, path: set[str]) -> bool:
        if node in path:
            return True
        return any(visits(target, path | {node}) for target in edges.get(node, set()))

    if any(visits(node, set()) for node in edges):
        raise ValueError('A distribuição cria um circuito circular.')


def save_distribution_rule(payload: dict[str, Any], actor_login: Any) -> dict[str, Any]:
    ensure_document_ai_distribution_schema()
    actor = _login(actor_login)
    rule_id = str(payload.get('id') or '').strip()
    normalized = _normalize_rule(payload)
    before_row = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_AI_DISTRIBUTION_RULE_STAMP = :rule_id
    """), {'rule_id': rule_id}).mappings().first() if rule_id else None
    _assert_no_cycle(normalized, rule_id)
    duplicate = db.session.execute(text("""
        SELECT TOP (1) DOC_AI_DISTRIBUTION_RULE_STAMP
        FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_CLASS = :doc_class AND SOURCE_VIEW = :source
          AND ((:terminal = 1 AND TERMINAL = 1) OR (:terminal = 0 AND DESTINATION_VIEW = :destination))
          AND DOC_AI_DISTRIBUTION_RULE_STAMP <> :rule_id
    """), {**normalized, 'rule_id': rule_id}).scalar()
    if duplicate:
        raise ValueError('Já há uma distribuição.')
    terminal_conflict = db.session.execute(text("""
        SELECT TOP (1) DOC_AI_DISTRIBUTION_RULE_STAMP
        FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_CLASS=:doc_class AND SOURCE_VIEW=:source
          AND DOC_AI_DISTRIBUTION_RULE_STAMP <> :rule_id
          AND (TERMINAL=1 OR :terminal=1)
    """), {**normalized, 'rule_id': rule_id}).scalar()
    if terminal_conflict:
        raise ValueError('Uma distribuição terminal não pode coexistir com outros destinos.')
    if rule_id and not before_row:
        raise ValueError('Distribuição não encontrada.')
    if not rule_id:
        rule_id = _stamp()
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_DISTRIBUTION_RULE (
                DOC_AI_DISTRIBUTION_RULE_STAMP, DOC_CLASS, SOURCE_VIEW,
                DESTINATION_VIEW, DESTINATION_STATE, TERMINAL,
                USERCRIACAO, USERALTERACAO
            ) VALUES (:id, :doc_class, :source, NULLIF(:destination, ''), :state, :terminal, :actor, :actor)
        """), {'id': rule_id, 'actor': actor, **normalized})
        action = 'ADD_RULE'
    else:
        db.session.execute(text("""
            UPDATE dbo.DOC_AI_DISTRIBUTION_RULE SET
                DOC_CLASS=:doc_class, SOURCE_VIEW=:source,
                DESTINATION_VIEW=NULLIF(:destination, ''), DESTINATION_STATE=:state,
                TERMINAL=:terminal, DTALT=GETDATE(), USERALTERACAO=:actor
            WHERE DOC_AI_DISTRIBUTION_RULE_STAMP=:id
        """), {'id': rule_id, 'actor': actor, **normalized})
        action = 'UPDATE_RULE'
    retroactive_result = None
    _log_rule(action, rule_id, actor, _serialize_rule(dict(before_row)) if before_row else {}, {'id': rule_id, **normalized})
    if bool(payload.get('apply_to_existing')):
        retroactive_result = apply_distribution_to_existing(normalized['doc_class'], normalized['source'], actor)
    db.session.commit()
    response = list_distribution_configuration()
    if retroactive_result is not None:
        response['retroactive'] = retroactive_result
    return response


def delete_distribution_rule(rule_id: str, actor_login: Any) -> dict[str, Any]:
    ensure_document_ai_distribution_schema()
    row = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_AI_DISTRIBUTION_RULE_STAMP=:rule_id
    """), {'rule_id': str(rule_id or '').strip()}).mappings().first()
    if not row:
        raise ValueError('Distribuição não encontrada.')
    before = _serialize_rule(dict(row))
    db.session.execute(text('DELETE FROM dbo.DOC_AI_DISTRIBUTION_RULE WHERE DOC_AI_DISTRIBUTION_RULE_STAMP=:rule_id'), {'rule_id': before['id']})
    _log_rule('DELETE_RULE', before['id'], _login(actor_login), before, {})
    db.session.commit()
    return list_distribution_configuration()


def _log_rule(action: str, rule_id: str, actor: str, before: dict[str, Any], after: dict[str, Any], result: dict[str, Any] | None = None) -> None:
    db.session.execute(text("""
        INSERT INTO dbo.DOC_AI_DISTRIBUTION_LOG (
            DOC_AI_DISTRIBUTION_LOG_STAMP, ACTOR_LOGIN, ACTION_CODE,
            RULE_STAMP, BEFORE_JSON, AFTER_JSON, RESULT_JSON
        ) VALUES (:stamp, :actor, :action, :rule_id, :before_json, :after_json, :result_json)
    """), {
        'stamp': _stamp(), 'actor': actor, 'action': action, 'rule_id': rule_id or None,
        'before_json': json.dumps(before or {}, ensure_ascii=False, default=str),
        'after_json': json.dumps(after or {}, ensure_ascii=False, default=str),
        'result_json': json.dumps(result or {}, ensure_ascii=False, default=str),
    })


def normalize_distribution_document_class(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    return 'invoice' if normalized == 'provisional_invoice' else normalized


def _validated_column(view: str) -> str:
    return {
        'home': 'RECEPTION_VALIDATED',
        'management': 'MANAGEMENT_VALIDATED',
        'accounting': 'ACCOUNTING_VALIDATED',
    }[view]


def distribution_impact(payload: dict[str, Any]) -> dict[str, Any]:
    """Preview how many already validated documents match a rule source."""
    ensure_document_ai_distribution_schema()
    normalized = _normalize_rule(payload)
    validated_column = _validated_column(normalized['source'])
    value = db.session.execute(text(f"""
        SELECT COUNT_BIG(1)
        FROM dbo.DOC_INBOX D
        WHERE ISNULL(D.{validated_column}, 0) = 1
          AND CASE
                WHEN LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, '')))) = 'provisional_invoice'
                    THEN 'invoice'
                ELSE LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, ''))))
              END = :doc_class
    """), {'doc_class': normalized['doc_class']}).scalar()
    return {
        'doc_class': normalized['doc_class'],
        'source': normalized['source'],
        'documents': int(value or 0),
    }


def _document_view_validated(document: Any, view: str) -> bool:
    return bool({
        'home': getattr(document, 'reception_validated', False),
        'management': getattr(document, 'management_validated', False),
        'accounting': getattr(document, 'accounting_validated', False),
    }.get(view, False))


def _distribution_rules(doc_class: str, source: str) -> list[dict[str, Any]]:
    rows = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_DISTRIBUTION_RULE
        WHERE DOC_CLASS=:doc_class AND SOURCE_VIEW=:source
        ORDER BY TERMINAL, DESTINATION_VIEW
    """), {'doc_class': doc_class, 'source': source}).mappings().all()
    return [_serialize_rule(dict(row)) for row in rows]


def assert_document_distribution_available(document: Any, source: str, document_type: Any = None) -> list[dict[str, Any]]:
    ensure_document_ai_distribution_schema()
    doc_class = normalize_distribution_document_class(
        document_type if document_type is not None else getattr(document, 'doc_type_detected', '')
    )
    rules = _distribution_rules(doc_class, source)
    if not rules and source == 'accounting':
        return [{'id': '', 'doc_class': doc_class, 'source': source, 'destination': '', 'state': 'none', 'terminal': True}]
    if not rules:
        label = next((item['label'] for item in DOCUMENT_CLASSES if item['value'] == doc_class), doc_class or 'Desconhecido')
        source_label = next((item['label'] for item in INBOX_VIEW_DEFINITIONS if item['value'] == source), source)
        raise ValueError(f'Não existe distribuição para {label} a partir de {source_label}.')
    if any(rule['terminal'] for rule in rules) and len(rules) > 1:
        raise ValueError('A distribuição terminal não pode coexistir com outros destinos.')
    return rules


def _upsert_assignment(document: Any, rule: dict[str, Any], actor: str) -> str:
    destination = rule['destination']
    existing = db.session.execute(text("""
        SELECT TOP (1) * FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT
        WHERE DOCINSTAMP=:document_id AND VIEW_CODE=:destination
    """), {'document_id': document.docinstamp, 'destination': destination}).mappings().first()
    already_validated = _document_view_validated(document, destination) or bool(existing and existing.get('VALIDADO'))
    if existing:
        if already_validated:
            return 'preserved'
        db.session.execute(text("""
            UPDATE dbo.DOC_AI_WORKFLOW_ASSIGNMENT SET
                STATE_CODE=:state, SOURCE_VIEW=:source, RULE_STAMP=:rule_id,
                ATIVO=1, DTALT=GETDATE(), USERALTERACAO=:actor
            WHERE DOC_AI_WORKFLOW_ASSIGNMENT_STAMP=:assignment_id
        """), {
            'state': rule['state'], 'source': rule['source'], 'rule_id': rule['id'],
            'actor': actor, 'assignment_id': existing['DOC_AI_WORKFLOW_ASSIGNMENT_STAMP'],
        })
        action = 'updated'
    else:
        active = not already_validated
        validated = already_validated
        state = 'validated' if already_validated else rule['state']
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_WORKFLOW_ASSIGNMENT (
                DOC_AI_WORKFLOW_ASSIGNMENT_STAMP, DOCINSTAMP, VIEW_CODE,
                STATE_CODE, SOURCE_VIEW, RULE_STAMP, ATIVO, VALIDADO,
                USERCRIACAO, USERALTERACAO
            ) VALUES (:assignment_id, :document_id, :destination, :state,
                      :source, :rule_id, :active, :validated, :actor, :actor)
        """), {
            'assignment_id': _stamp(), 'document_id': document.docinstamp,
            'destination': destination, 'state': state,
            'source': rule['source'], 'rule_id': rule['id'], 'actor': actor,
            'active': active, 'validated': validated,
        })
        action = 'preserved' if already_validated else 'created'
    _log_rule('ASSIGN_DOCUMENT', rule['id'], actor, {}, {
        'document_id': document.docinstamp,
        'view': destination,
        'state': rule['state'],
        'action': action,
    })
    return action


def apply_document_distribution(document: Any, source: str, actor_login: Any) -> dict[str, Any]:
    """Apply one validated stage without committing the caller transaction."""
    source = str(source or '').strip().lower()
    if source not in VALID_VIEWS:
        raise ValueError('Origem de distribuição inválida.')
    actor = _login(actor_login)
    rules = assert_document_distribution_available(document, source)
    desired_destinations = {rule['destination'] for rule in rules if not rule['terminal']}
    stale_rows = db.session.execute(text("""
        SELECT DOC_AI_WORKFLOW_ASSIGNMENT_STAMP, VIEW_CODE
        FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT
        WHERE DOCINSTAMP=:document_id AND SOURCE_VIEW=:source
          AND ATIVO=1 AND VALIDADO=0
    """), {'document_id': document.docinstamp, 'source': source}).mappings().all()
    for stale in stale_rows:
        if str(stale.get('VIEW_CODE') or '') in desired_destinations:
            continue
        db.session.execute(text("""
            UPDATE dbo.DOC_AI_WORKFLOW_ASSIGNMENT SET
                ATIVO=0, DTALT=GETDATE(), USERALTERACAO=:actor
            WHERE DOC_AI_WORKFLOW_ASSIGNMENT_STAMP=:assignment_id
        """), {'actor': actor, 'assignment_id': stale['DOC_AI_WORKFLOW_ASSIGNMENT_STAMP']})
        _log_rule('REMOVE_ASSIGNMENT', '', actor, {
            'document_id': document.docinstamp,
            'view': str(stale.get('VIEW_CODE') or ''),
        }, {})
    source_assignment = db.session.execute(text("""
        SELECT TOP (1) DOC_AI_WORKFLOW_ASSIGNMENT_STAMP
        FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT
        WHERE DOCINSTAMP=:document_id AND VIEW_CODE=:source
    """), {'document_id': document.docinstamp, 'source': source}).scalar()
    if source_assignment:
        db.session.execute(text("""
            UPDATE dbo.DOC_AI_WORKFLOW_ASSIGNMENT SET
                ATIVO=0, VALIDADO=1, STATE_CODE='validated',
                DTALT=GETDATE(), USERALTERACAO=:actor
            WHERE DOC_AI_WORKFLOW_ASSIGNMENT_STAMP=:assignment_id
        """), {'actor': actor, 'assignment_id': source_assignment})
    outcomes = []
    for rule in rules:
        if rule['terminal']:
            outcomes.append({'terminal': True})
        else:
            outcomes.append({
                'destination': rule['destination'],
                'state': rule['state'],
                'action': _upsert_assignment(document, rule, actor),
            })
    _log_rule('DISTRIBUTE_DOCUMENT', '', actor, {}, {
        'document_id': document.docinstamp,
        'source': source,
        'doc_class': normalize_distribution_document_class(document.doc_type_detected),
    }, {'outcomes': outcomes})
    return {'document_id': document.docinstamp, 'source': source, 'outcomes': outcomes}


def apply_distribution_to_existing(doc_class: str, source: str, actor_login: Any) -> dict[str, Any]:
    """Apply current rules to old documents, preserving completed destinations."""
    validated_column = _validated_column(source)
    rows = db.session.execute(text(f"""
        SELECT D.DOCINSTAMP
        FROM dbo.DOC_INBOX D
        WHERE ISNULL(D.{validated_column}, 0) = 1
          AND CASE
                WHEN LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, '')))) = 'provisional_invoice'
                    THEN 'invoice'
                ELSE LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, ''))))
              END = :doc_class
        ORDER BY D.DTCRI, D.DOCINSTAMP
    """), {'doc_class': normalize_distribution_document_class(doc_class)}).scalars().all()
    from models import DocInbox
    applied = 0
    for document_id in rows:
        document = db.session.get(DocInbox, document_id)
        if not document:
            continue
        apply_document_distribution(document, source, actor_login)
        applied += 1
    return {'documents': len(rows), 'applied': applied, 'preserved_completed': True}
