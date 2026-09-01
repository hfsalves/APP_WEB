from __future__ import annotations

from typing import Any

from sqlalchemy import text


CORE_FIELD_WEIGHTS = {
    'feid': 20,
    'supplier': 20,
    'doc_class': 15,
    'document_date': 15,
    'document_number': 30,
}
SUPPORT_FIELD_WEIGHTS = {
    'gross_total': 5,
    'currency': 2,
}
POSSIBLE_DUPLICATE_THRESHOLD = 85


def _clean(value: Any) -> str:
    return str(value or '').strip().lower()


def _supplier_value(identity: dict[str, Any]) -> tuple[str, str]:
    supplier_no = str(identity.get('supplier_no') or '').strip()
    supplier_tax_id = ''.join(char for char in str(identity.get('supplier_tax_id') or '') if char.isdigit())
    return supplier_no, supplier_tax_id


def _supplier_match(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, bool]:
    left_no, left_tax = _supplier_value(left)
    right_no, right_tax = _supplier_value(right)
    available = bool((left_no or left_tax) and (right_no or right_tax))
    matches = bool(
        (left_no and right_no and left_no == right_no)
        or (left_tax and right_tax and left_tax == right_tax)
    )
    return available, matches


def evaluate_duplicate_match(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic and explainable duplicate assessment."""
    left_hash = _clean(left.get('file_hash'))
    right_hash = _clean(right.get('file_hash'))
    if left_hash and right_hash and left_hash == right_hash:
        return {
            'classification': 'certain',
            'match_type': 'exact',
            'score': 100,
            'matching_fields': ['file_hash'],
            'missing_fields': [],
            'conflicting_fields': [],
        }

    matching_fields: list[str] = []
    missing_fields: list[str] = []
    conflicting_fields: list[str] = []
    score = 0

    for field in ('feid', 'doc_class', 'document_date', 'document_number'):
        left_value = _clean(left.get(field))
        right_value = _clean(right.get(field))
        if not left_value or not right_value or (field == 'doc_class' and 'unknown' in {left_value, right_value}):
            missing_fields.append(field)
        elif left_value == right_value:
            matching_fields.append(field)
            score += CORE_FIELD_WEIGHTS[field]
        else:
            conflicting_fields.append(field)

    supplier_available, supplier_matches = _supplier_match(left, right)
    if not supplier_available:
        missing_fields.append('supplier')
    elif supplier_matches:
        matching_fields.append('supplier')
        score += CORE_FIELD_WEIGHTS['supplier']
    else:
        conflicting_fields.append('supplier')

    for field in ('gross_total', 'currency'):
        left_value = left.get(field)
        right_value = right.get(field)
        if left_value in (None, '') or right_value in (None, ''):
            continue
        if _clean(left_value) == _clean(right_value):
            matching_fields.append(field)
            score += SUPPORT_FIELD_WEIGHTS[field]

    score = min(score, 100)
    complete_key = not any(field in missing_fields for field in CORE_FIELD_WEIGHTS)
    if not conflicting_fields and complete_key:
        classification = 'certain'
        match_type = 'business'
        score = 100
    elif not conflicting_fields and score >= POSSIBLE_DUPLICATE_THRESHOLD:
        classification = 'possible'
        match_type = 'possible'
    else:
        classification = 'new'
        match_type = ''

    return {
        'classification': classification,
        'match_type': match_type,
        'score': score,
        'matching_fields': matching_fields,
        'missing_fields': missing_fields,
        'conflicting_fields': conflicting_fields,
    }


def find_exact_file_duplicate(
    session,
    file_hash: Any,
    *,
    exclude_document_id: str = '',
    exclude_expense_id: str = '',
) -> dict[str, Any] | None:
    """Find the same file in Document AI or employee expenses."""
    normalized_hash = _clean(file_hash)
    if not normalized_hash:
        return None
    row = session.execute(text("""
        SELECT TOP 1 SOURCE_AREA, RECORD_ID, FILE_NAME
        FROM (
            SELECT
                'document_ai' AS SOURCE_AREA,
                D.DOCINSTAMP AS RECORD_ID,
                ISNULL(D.FILE_NAME, '') AS FILE_NAME,
                D.DTCRI AS CREATED_AT
            FROM dbo.DOC_INBOX D
            WHERE LOWER(ISNULL(D.FILE_HASH, '')) = :file_hash
              AND D.DOCINSTAMP <> :exclude_document_id

            UNION ALL

            SELECT
                'document_ai' AS SOURCE_AREA,
                I.DOCINSTAMP AS RECORD_ID,
                ISNULL(D.FILE_NAME, '') AS FILE_NAME,
                I.DTALT AS CREATED_AT
            FROM dbo.DOC_DUPLICATE_INDEX I
            INNER JOIN dbo.DOC_INBOX D ON D.DOCINSTAMP = I.DOCINSTAMP
            WHERE LOWER(ISNULL(I.FILE_HASH, '')) = :file_hash
              AND I.DOCINSTAMP <> :exclude_document_id
              AND I.ATIVO = 1

            UNION ALL

            SELECT
                'expenses' AS SOURCE_AREA,
                L.DESPLINHASTAMP AS RECORD_ID,
                ISNULL(NULLIF(L.FICHEIRO_ORIGINAL, ''), L.FICHEIRO) AS FILE_NAME,
                L.DTCRI AS CREATED_AT
            FROM dbo.COLAB_DESPESA_LINHA L
            WHERE LOWER(ISNULL(L.FILE_HASH, '')) = :file_hash
              AND L.DESPLINHASTAMP <> :exclude_expense_id
              AND ISNULL(L.ANULADA, 0) = 0
        ) DUPLICATES
        ORDER BY CREATED_AT DESC
    """), {
        'file_hash': normalized_hash,
        'exclude_document_id': str(exclude_document_id or '').strip(),
        'exclude_expense_id': str(exclude_expense_id or '').strip(),
    }).mappings().first()
    if not row:
        return None
    return {
        'source_area': str(row.get('SOURCE_AREA') or ''),
        'record_id': str(row.get('RECORD_ID') or ''),
        'file_name': str(row.get('FILE_NAME') or ''),
        'classification': 'certain',
        'match_type': 'exact',
        'score': 100,
        'matching_fields': ['file_hash'],
    }


def acquire_duplicate_lock(session, file_hash: Any, timeout_ms: int = 10000) -> None:
    """Serialize equal-file imports until the surrounding transaction finishes."""
    normalized_hash = _clean(file_hash)
    if not normalized_hash:
        return
    result = session.execute(text("""
        DECLARE @result int;
        EXEC @result = sys.sp_getapplock
            @Resource = :resource,
            @LockMode = 'Exclusive',
            @LockOwner = 'Transaction',
            @LockTimeout = :timeout_ms;
        SELECT @result;
    """), {
        'resource': f'DOC_DUPLICATE:{normalized_hash}',
        'timeout_ms': max(int(timeout_ms or 0), 0),
    }).scalar()
    if int(result if result is not None else -999) < 0:
        raise RuntimeError('Não foi possível concluir a verificação de duplicados. Tenta novamente.')
