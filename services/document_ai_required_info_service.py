from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text

from models import db
from services.document_ai_distribution_service import DOCUMENT_CLASSES, normalize_distribution_document_class
from services.document_ai_inbox_access_service import INBOX_VIEW_DEFINITIONS


FIELD_DEFINITIONS = (
    {'value': 'entity', 'label': 'Entidade', 'views': ('home', 'management', 'accounting')},
    {'value': 'supplier', 'label': 'Fornecedor', 'views': ('home', 'management', 'accounting')},
    {'value': 'supplier_resolved', 'label': 's/Fornecedor', 'views': ('home',)},
    {'value': 'classification', 'label': 'Classificação', 'views': ('home', 'management')},
    {'value': 'project', 'label': 'Obra', 'views': ('home', 'management', 'accounting')},
    {'value': 'article', 'label': 'Artigo', 'views': ('management', 'accounting')},
    {'value': 'description', 'label': 'Designação', 'views': ('management', 'accounting')},
    {'value': 'origin', 'label': 'BC/Contrato', 'views': ('management', 'accounting')},
    {'value': 'quantity', 'label': 'Quantidade', 'views': ('management', 'accounting')},
    {'value': 'unit_price', 'label': 'PU', 'views': ('management', 'accounting')},
    {'value': 'line_total', 'label': 'PT', 'views': ('management', 'accounting')},
    {'value': 'date', 'label': 'Data', 'views': ('management', 'accounting')},
    {'value': 'gross_total', 'label': 'Total', 'views': ('home', 'management', 'accounting')},
    {'value': 'tax_total', 'label': 'IVA', 'views': ('home', 'management', 'accounting')},
    {'value': 'net_total', 'label': 'Total s/IVA', 'views': ('home', 'management', 'accounting')},
    {'value': 'delivery_note', 'label': 'BL', 'views': ('management', 'accounting')},
    {'value': 'vehicle', 'label': 'Matrícula', 'views': ('management', 'accounting')},
)
VALID_CLASSES = {item['value'] for item in DOCUMENT_CLASSES}
VALID_VIEWS = {item['value'] for item in INBOX_VIEW_DEFINITIONS}
FIELD_LOOKUP = {item['value']: item for item in FIELD_DEFINITIONS}
_schema_ready: set[str] = set()


def _stamp() -> str:
    return uuid.uuid4().hex[:25]


def _login(value: Any) -> str:
    return str(value or '').strip().lower()


def ensure_required_info_schema() -> None:
    database_name = str(db.session.execute(text('SELECT DB_NAME()')).scalar() or '').strip().upper()
    if database_name in _schema_ready:
        return
    migration = Path(__file__).resolve().parents[1] / 'migrations' / 'document_ai_required_info.sql'
    sql = migration.read_text(encoding='utf-8').replace('\r\n', '\n')
    try:
        for statement in [part.strip() for part in sql.split('\nGO\n') if part.strip()]:
            db.session.execute(text(statement))
        _seed_required_fields()
        db.session.commit()
        _schema_ready.add(database_name)
    except Exception:
        db.session.rollback()
        raise


def _seed_required_fields() -> None:
    if db.session.execute(text('SELECT COUNT_BIG(1) FROM dbo.DOC_AI_REQUIRED_FIELD')).scalar():
        return
    defaults = {
        ('mail', 'home'): ('entity', 'supplier'),
        ('invoice', 'home'): ('entity', 'supplier'),
        ('credit_note', 'home'): ('entity', 'supplier'),
        ('advertising', 'home'): ('entity', 'supplier_resolved'),
        ('invoice', 'management'): (
            'entity', 'supplier', 'project', 'article', 'description', 'origin',
            'quantity', 'unit_price', 'line_total', 'date', 'gross_total',
            'tax_total', 'net_total', 'delivery_note', 'vehicle',
        ),
    }
    for (doc_class, view), fields in defaults.items():
        for field_code in fields:
            db.session.execute(text("""
                INSERT INTO dbo.DOC_AI_REQUIRED_FIELD (
                    DOC_AI_REQUIRED_FIELD_STAMP, DOC_CLASS, VIEW_CODE, FIELD_CODE,
                    USERCRIACAO, USERALTERACAO
                ) VALUES (:stamp, :doc_class, :view, :field, 'system', 'system')
            """), {'stamp': _stamp(), 'doc_class': doc_class, 'view': view, 'field': field_code})


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('DOC_AI_REQUIRED_FIELD_STAMP') or ''),
        'doc_class': str(row.get('DOC_CLASS') or ''),
        'view': str(row.get('VIEW_CODE') or ''),
        'field': str(row.get('FIELD_CODE') or ''),
    }


def list_required_info_configuration() -> dict[str, Any]:
    ensure_required_info_schema()
    rows = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_REQUIRED_FIELD
        ORDER BY DOC_CLASS, VIEW_CODE, FIELD_CODE
    """)).mappings().all()
    return {
        'classifications': [dict(item) for item in DOCUMENT_CLASSES],
        'views': [dict(item) for item in INBOX_VIEW_DEFINITIONS],
        'fields': [dict(item) for item in FIELD_DEFINITIONS],
        'rules': [_serialize(dict(row)) for row in rows],
    }


def _normalize(payload: dict[str, Any]) -> dict[str, str]:
    doc_class = normalize_distribution_document_class(payload.get('doc_class'))
    view = str(payload.get('view') or '').strip().lower()
    field_code = str(payload.get('field') or '').strip().lower()
    if doc_class not in VALID_CLASSES:
        raise ValueError('Seleciona um tipo de documento válido.')
    if view not in VALID_VIEWS:
        raise ValueError('Seleciona uma origem válida.')
    definition = FIELD_LOOKUP.get(field_code)
    if not definition or view not in definition['views']:
        raise ValueError('Seleciona uma informação compatível com a origem.')
    if field_code == 'supplier_resolved' and doc_class != 'advertising':
        raise ValueError('s/Fornecedor só está disponível para Publicidade.')
    return {'doc_class': doc_class, 'view': view, 'field': field_code}


def _log(action: str, actor: str, rule_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    db.session.execute(text("""
        INSERT INTO dbo.DOC_AI_REQUIRED_FIELD_LOG (
            DOC_AI_REQUIRED_FIELD_LOG_STAMP, ACTOR_LOGIN, ACTION_CODE,
            RULE_STAMP, BEFORE_JSON, AFTER_JSON
        ) VALUES (:stamp, :actor, :action, :rule_id, :before_json, :after_json)
    """), {
        'stamp': _stamp(), 'actor': actor, 'action': action, 'rule_id': rule_id or None,
        'before_json': json.dumps(before or {}, ensure_ascii=False),
        'after_json': json.dumps(after or {}, ensure_ascii=False),
    })


def save_required_info_rule(payload: dict[str, Any], actor_login: Any) -> dict[str, Any]:
    ensure_required_info_schema()
    normalized = _normalize(payload)
    actor = _login(actor_login)
    rule_id = str(payload.get('id') or '').strip()
    before_row = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_REQUIRED_FIELD
        WHERE DOC_AI_REQUIRED_FIELD_STAMP=:rule_id
    """), {'rule_id': rule_id}).mappings().first() if rule_id else None
    duplicate = db.session.execute(text("""
        SELECT TOP (1) DOC_AI_REQUIRED_FIELD_STAMP
        FROM dbo.DOC_AI_REQUIRED_FIELD
        WHERE DOC_CLASS=:doc_class AND VIEW_CODE=:view AND FIELD_CODE=:field
          AND DOC_AI_REQUIRED_FIELD_STAMP<>:rule_id
    """), {**normalized, 'rule_id': rule_id}).scalar()
    if duplicate:
        raise ValueError('Já há uma informação.')
    if rule_id and not before_row:
        raise ValueError('Informação não encontrada.')
    if rule_id:
        db.session.execute(text("""
            UPDATE dbo.DOC_AI_REQUIRED_FIELD SET DOC_CLASS=:doc_class,
                VIEW_CODE=:view, FIELD_CODE=:field, DTALT=GETDATE(), USERALTERACAO=:actor
            WHERE DOC_AI_REQUIRED_FIELD_STAMP=:rule_id
        """), {**normalized, 'actor': actor, 'rule_id': rule_id})
        action = 'UPDATE'
    else:
        rule_id = _stamp()
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_REQUIRED_FIELD (
                DOC_AI_REQUIRED_FIELD_STAMP, DOC_CLASS, VIEW_CODE, FIELD_CODE,
                USERCRIACAO, USERALTERACAO
            ) VALUES (:rule_id, :doc_class, :view, :field, :actor, :actor)
        """), {**normalized, 'actor': actor, 'rule_id': rule_id})
        action = 'ADD'
    _log(action, actor, rule_id, _serialize(dict(before_row)) if before_row else {}, {'id': rule_id, **normalized})
    db.session.commit()
    return list_required_info_configuration()


def delete_required_info_rule(rule_id: str, actor_login: Any) -> dict[str, Any]:
    ensure_required_info_schema()
    row = db.session.execute(text("""
        SELECT * FROM dbo.DOC_AI_REQUIRED_FIELD WHERE DOC_AI_REQUIRED_FIELD_STAMP=:rule_id
    """), {'rule_id': str(rule_id or '').strip()}).mappings().first()
    if not row:
        raise ValueError('Informação não encontrada.')
    before = _serialize(dict(row))
    db.session.execute(text('DELETE FROM dbo.DOC_AI_REQUIRED_FIELD WHERE DOC_AI_REQUIRED_FIELD_STAMP=:rule_id'), {'rule_id': before['id']})
    _log('DELETE', _login(actor_login), before['id'], before, {})
    db.session.commit()
    return list_required_info_configuration()


def required_fields_for(doc_type: Any, view: Any) -> list[str]:
    ensure_required_info_schema()
    doc_class = normalize_distribution_document_class(doc_type)
    rows = db.session.execute(text("""
        SELECT FIELD_CODE FROM dbo.DOC_AI_REQUIRED_FIELD
        WHERE DOC_CLASS=:doc_class AND VIEW_CODE=:view
        ORDER BY FIELD_CODE
    """), {'doc_class': doc_class, 'view': str(view or '').strip().lower()}).scalars().all()
    return [str(value or '') for value in rows]


def required_fields_by_class(view: Any) -> dict[str, list[str]]:
    """Load all required fields for one workflow view in a single query."""
    ensure_required_info_schema()
    normalized_view = str(view or '').strip().lower()
    rows = db.session.execute(text("""
        SELECT DOC_CLASS, FIELD_CODE
        FROM dbo.DOC_AI_REQUIRED_FIELD
        WHERE VIEW_CODE=:view
        ORDER BY DOC_CLASS, FIELD_CODE
    """), {'view': normalized_view}).mappings().all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(str(row.get('DOC_CLASS') or ''), []).append(str(row.get('FIELD_CODE') or ''))
    return result


def _has_value(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _positive_int(value: Any) -> bool:
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(str(value).replace(' ', '').replace(',', '.'))
    except (TypeError, ValueError):
        return None


def evaluate_required_info(
    document_data: dict[str, Any] | None,
    view: Any,
    *,
    stored_feid: Any = 0,
    stored_supplier_no: Any = 0,
    processing_meta: dict[str, Any] | None = None,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    data = dict(document_data or {})
    customer = dict(data.get('customer') or {})
    supplier = dict(data.get('supplier') or {})
    totals = dict(data.get('totals') or {})
    lines = [dict(item) for item in (data.get('lines') or []) if isinstance(item, dict)]
    financial_lines = [item for item in lines if not bool(item.get('informative') or item.get('is_informative'))]
    doc_type = normalize_distribution_document_class(data.get('document_type'))
    required = list(required_fields) if required_fields is not None else required_fields_for(doc_type, view)
    meta = dict(processing_meta or {})
    origins = meta.get('phc_origins') if isinstance(meta.get('phc_origins'), list) else []
    if not origins and isinstance(meta.get('phc_origin'), dict):
        origins = [meta['phc_origin']]
    invoice_type = str(data.get('invoice_type') or '').strip().lower()

    checks = {
        'entity': _positive_int(customer.get('feid') or stored_feid),
        'supplier': _positive_int(supplier.get('supplier_no') or supplier.get('no') or stored_supplier_no),
        'supplier_resolved': bool(
            _positive_int(supplier.get('supplier_no') or supplier.get('no') or stored_supplier_no)
            or data.get('supplier_explicitly_absent')
            or supplier.get('explicitly_absent')
            or supplier.get('without_supplier')
        ),
        'classification': doc_type not in {'', 'unknown'},
        'project': bool(
            str((data.get('origin_project') or {}).get('ccusto') or '').strip()
            or (financial_lines and all(str(item.get('ccusto') or item.get('project_ccusto') or item.get('project') or '').strip() for item in financial_lines))
        ),
        'article': bool(financial_lines and all(str(item.get('article_ref') or item.get('article') or item.get('ref') or '').strip() for item in financial_lines)),
        'description': bool(lines and all(str(item.get('description') or '').strip() for item in lines)),
        'origin': bool([item for item in origins if isinstance(item, dict) and str(item.get('stamp') or '').strip()]),
        'quantity': bool(financial_lines and all(_has_value(item.get('qty') if 'qty' in item else item.get('quantity')) for item in financial_lines)),
        'unit_price': bool(financial_lines and all(_has_value(item.get('unit_price')) for item in financial_lines)),
        'line_total': bool(financial_lines and all(_has_value(item.get('net_amount') if 'net_amount' in item else item.get('line_total')) for item in financial_lines)),
        'date': bool(data.get('document_date')) and all(_has_value(item.get('date') or data.get('document_date')) for item in financial_lines),
        'gross_total': _has_value(totals.get('gross_total')),
        'tax_total': _has_value(totals.get('tax_total')),
        'net_total': _has_value(totals.get('net_total')),
        'delivery_note': True,
        'vehicle': True,
    }
    delivery_required = any(str(item.get('origin_delivery_note_number') or '').strip() for item in lines)
    if delivery_required:
        checks['delivery_note'] = bool(financial_lines and all(str(item.get('origin_delivery_note_number') or '').strip() for item in financial_lines))
    vehicle_lines = [item for item in financial_lines if bool(item.get('vehicle_required'))]
    if vehicle_lines:
        checks['vehicle'] = all(str(item.get('registration') or item.get('matricula') or '').strip() for item in vehicle_lines)

    consistency_messages: list[str] = []
    consistency_targets: set[str] = set()
    if str(view or '').strip().lower() in {'management', 'accounting'}:
        bad_line_total = False
        group_principals: set[str] = set()
        group_associates: set[str] = set()
        invalid_group = False
        for item in financial_lines:
            qty = _number(item.get('qty') if 'qty' in item else item.get('quantity'))
            unit_price = _number(item.get('unit_price'))
            line_total = _number(item.get('net_amount') if 'net_amount' in item else item.get('line_total'))
            if qty is not None and unit_price is not None and line_total is not None:
                bad_line_total = bad_line_total or abs((qty * unit_price) - line_total) > 0.02
            group_code = str(item.get('article_group_code') or '').strip().upper()
            if not group_code:
                continue
            if len(group_code) < 2 or group_code[0] not in {'P', 'A'} or not group_code[1:].isdigit() or int(group_code[1:]) <= 0:
                invalid_group = True
            elif group_code.startswith('P'):
                invalid_group = invalid_group or group_code[1:] in group_principals
                group_principals.add(group_code[1:])
            else:
                group_associates.add(group_code[1:])
        if bad_line_total:
            consistency_messages.append('Existem linhas em que Quantidade x PU não corresponde ao PT.')
            consistency_targets.add('docAiExtractLinesSection')
        if invalid_group or any(group not in group_principals for group in group_associates):
            consistency_messages.append('Existem grupos de artigos inválidos ou sem linha principal.')
            consistency_targets.add('docAiExtractLinesSection')
        gross = _number(totals.get('gross_total'))
        tax = _number(totals.get('tax_total'))
        net = _number(totals.get('net_total'))
        if gross is not None and tax is not None and net is not None and abs((net + tax) - gross) > 0.02:
            consistency_messages.append('Os totais do documento não são coerentes: Total s/IVA + IVA deve corresponder ao Total.')
            consistency_targets.add('docAiExtractTotalsCard')

    messages = {
        'entity': 'Falta a entidade.', 'supplier': 'Falta o fornecedor.',
        'supplier_resolved': 'Falta resolver o fornecedor.', 'classification': 'Falta a classificação.',
        'project': 'Falta a obra.', 'article': 'Falta o artigo.',
        'description': 'Falta a designação.', 'origin': 'Falta associar um BC ou contrato.',
        'quantity': 'Falta a quantidade.', 'unit_price': 'Falta o PU.',
        'line_total': 'Falta o PT.', 'date': 'Falta a data.',
        'gross_total': 'Falta o total.', 'tax_total': 'Falta o IVA.',
        'net_total': 'Falta o total s/IVA.', 'delivery_note': 'Falta distribuir os BLs.',
        'vehicle': 'Falta a matrícula.',
    }
    targets = {
        'entity': 'docAiExtractCustomerCard', 'supplier': 'docAiExtractSupplierCard',
        'supplier_resolved': 'docAiExtractSupplierCard', 'classification': 'docAiExtractModeCard',
        'project': 'docAiExtractProjectCard', 'gross_total': 'docAiExtractTotalsCard',
        'tax_total': 'docAiExtractTotalsCard', 'net_total': 'docAiExtractTotalsCard',
        'origin': 'docAiExtractOriginSection',
    }
    missing = [code for code in required if not checks.get(code, False)]
    return {
        'ok': not missing and not consistency_messages,
        'required': required,
        'missing': missing,
        'messages': [messages.get(code, 'Informação a corrigir.') for code in missing] + consistency_messages,
        'targets': sorted(
            {targets.get(code, 'docAiExtractLinesSection') for code in missing} | consistency_targets
        ),
    }
