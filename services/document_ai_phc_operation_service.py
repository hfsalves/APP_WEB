import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from models import db
from services.gr360_audit_service import redact_data


class DocumentPhcOperationInProgressError(RuntimeError):
    """Raised when another request still owns a recent PHC/GED attempt."""


_PENDING_OPERATION_LEASE = timedelta(minutes=2)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_meta(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(str(value or '{}'))
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _dump_meta(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str)


def _public_result(result: dict[str, Any], allowed_fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in allowed_fields
        if result.get(key) not in (None, '')
    }


def _pending_attempt_is_live(operation: dict[str, Any], now: datetime) -> bool:
    if str(operation.get('status') or '').strip().lower() != 'pending':
        return False
    raw_attempted_at = str(operation.get('attempted_at_utc') or '').strip()
    if not raw_attempted_at:
        return False
    try:
        attempted_at = datetime.fromisoformat(raw_attempted_at.replace('Z', '+00:00'))
    except ValueError:
        return False
    if attempted_at.tzinfo is None:
        attempted_at = attempted_at.replace(tzinfo=timezone.utc)
    return now - attempted_at.astimezone(timezone.utc) < _PENDING_OPERATION_LEASE


def run_document_phc_operation(
    document: Any,
    *,
    operation_type: str,
    requested_by: str,
    execute: Callable[[], dict[str, Any]],
    is_complete: Callable[[dict[str, Any]], bool],
    result_fields: tuple[str, ...],
    operation_context: dict[str, Any] | None = None,
    legacy_meta_key: str = 'phc_integration',
    on_confirmed: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one PHC/GED operation with a durable, reusable recovery record.

    The PHC callback owns its database transaction and business locks. This
    coordinator persists intent before calling it and persists the resulting
    identity before the Portal workflow can advance.
    """
    clean_type = str(operation_type or '').strip().lower()
    if not clean_type:
        raise ValueError('O tipo da operação PHC é obrigatório.')

    meta = _load_meta(getattr(document, 'processing_meta_json', '{}'))
    operations = dict(meta.get('phc_operations') or {})
    existing = dict(operations.get(clean_type) or meta.get(legacy_meta_key) or {})
    if is_complete(existing):
        return existing

    now = _utc_now()
    if _pending_attempt_is_live(existing, now):
        raise DocumentPhcOperationInProgressError(
            'A integração PHC/GED deste documento já está em curso. Tenta novamente dentro de instantes.'
        )
    operation_id = uuid4().hex
    safe_context = redact_data(dict(operation_context or {}))
    pending = {
        **existing,
        'operation_id': operation_id,
        'type': clean_type,
        'status': 'pending',
        'attempted_at_utc': now.isoformat(),
        'attempted_by': str(requested_by or ''),
        'context': safe_context,
    }
    operations[clean_type] = pending
    meta['phc_operations'] = operations
    meta[legacy_meta_key] = pending
    document.processing_meta_json = _dump_meta(meta)
    document.processing_stage = 'integration_pending'
    document.dtalt = now.replace(tzinfo=None)
    document.useralteracao = requested_by or getattr(document, 'useralteracao', '') or ''
    db.session.commit()

    try:
        raw_result = dict(execute() or {})
    except Exception as exc:
        failed_at = _utc_now()
        meta = _load_meta(getattr(document, 'processing_meta_json', '{}'))
        operations = dict(meta.get('phc_operations') or {})
        failed = {
            **dict(operations.get(clean_type) or pending),
            'status': 'failed_recoverable',
            'failed_at_utc': failed_at.isoformat(),
            'error': str(exc)[:1000],
        }
        operations[clean_type] = failed
        meta['phc_operations'] = operations
        meta[legacy_meta_key] = failed
        document.processing_meta_json = _dump_meta(meta)
        document.processing_stage = 'integration_failed_recoverable'
        document.last_processing_error = str(exc)[:4000]
        document.dtalt = failed_at.replace(tzinfo=None)
        db.session.commit()
        raise

    confirmed_at = _utc_now()
    # A recovery callback may only be able to rediscover part of an identity.
    # Keep every previously persisted public identifier and overlay the newly
    # confirmed values, so retry/reconciliation never erases useful lineage.
    recovered_identity = _public_result(existing, result_fields)
    recovered_identity.update(_public_result(raw_result, result_fields))
    confirmed = {
        'operation_id': operation_id,
        'type': clean_type,
        'status': 'confirmed',
        'integrated_at_utc': confirmed_at.isoformat(),
        'integrated_by': str(requested_by or ''),
        'context': safe_context,
        **recovered_identity,
    }
    if not is_complete(confirmed):
        message = 'A integração PHC/GED não devolveu todos os identificadores obrigatórios.'
        failed = {
            **confirmed,
            'status': 'failed_recoverable',
            'failed_at_utc': confirmed_at.isoformat(),
            'error': message,
        }
        meta = _load_meta(getattr(document, 'processing_meta_json', '{}'))
        operations = dict(meta.get('phc_operations') or {})
        operations[clean_type] = failed
        meta['phc_operations'] = operations
        meta[legacy_meta_key] = failed
        document.processing_meta_json = _dump_meta(meta)
        document.processing_stage = 'integration_failed_recoverable'
        document.last_processing_error = message
        document.dtalt = confirmed_at.replace(tzinfo=None)
        db.session.commit()
        raise RuntimeError(message)

    meta = _load_meta(getattr(document, 'processing_meta_json', '{}'))
    operations = dict(meta.get('phc_operations') or {})
    operations[clean_type] = confirmed
    meta['phc_operations'] = operations
    meta[legacy_meta_key] = confirmed
    document.processing_meta_json = _dump_meta(meta)
    document.last_processing_error = ''
    document.dtalt = confirmed_at.replace(tzinfo=None)
    document.useralteracao = requested_by or getattr(document, 'useralteracao', '') or ''
    if on_confirmed:
        on_confirmed(confirmed)
    db.session.commit()
    return confirmed
