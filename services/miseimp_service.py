from sqlalchemy import text


def load_miseimp_map(session) -> dict[str, str]:
    try:
        rows = session.execute(text("""
            SELECT
                UPPER(LTRIM(RTRIM(ISNULL(CODIGO, '')))) AS CODIGO,
                LTRIM(RTRIM(ISNULL(DESCRICAO, ''))) AS DESCRICAO
            FROM dbo.MISEIMP
            WHERE LTRIM(RTRIM(ISNULL(CODIGO, ''))) <> ''
        """)).mappings().all()
    except Exception:
        return {}
    out: dict[str, str] = {}
    for row in rows:
        code = str(row.get('CODIGO') or '').strip().upper()
        desc = str(row.get('DESCRICAO') or '').strip()
        if code and desc:
            out[code] = desc
    return out


def get_miseimp_description(session, code: str) -> str:
    code_norm = str(code or '').strip().upper()
    if not code_norm:
        return ''
    return load_miseimp_map(session).get(code_norm, '')
