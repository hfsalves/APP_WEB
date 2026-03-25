from sqlalchemy import text

from services.hash_service import build_ft_hash_message, sha1_hex
from services.rsa_service import (
    b64encode_signature,
    load_private_key_from_pem,
    sign_sha1_prehashed,
)


def _to_int(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return int(default)
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return int(default)


def sign_ft_document(session, ftstamp: str, current_user: str = "", hash_ant_override: str | None = None) -> dict:
    ft = session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.FT WITH (UPDLOCK, ROWLOCK)
        WHERE FTSTAMP=:s
    """), {"s": ftstamp}).mappings().first()
    if not ft:
        raise ValueError("Documento FT não encontrado para assinatura.")
    ft = dict(ft)

    fi_rows = session.execute(text("""
        SELECT *
        FROM dbo.FI WITH (UPDLOCK, ROWLOCK)
        WHERE FTSTAMP=:s
        ORDER BY ISNULL(LORDEM,0), FISTAMP
    """), {"s": ftstamp}).mappings().all()
    fi_rows = [dict(r) for r in fi_rows]

    festamp = (ft.get("FESTAMP") or "").strip()
    if not festamp:
        raise ValueError("FESTAMP vazio no documento FT.")

    fe = session.execute(text("""
        SELECT TOP 1
            ISNULL(RSA_PRIV_PATH,'') AS RSA_PRIV_PATH,
            ISNULL(RSA_PUB_PATH,'') AS RSA_PUB_PATH,
            ISNULL(KEYID,'') AS KEYID,
            CONVERT(varchar(20), ISNULL(NIF,0)) AS NIF
        FROM dbo.FE
        WHERE FESTAMP=:f
    """), {"f": festamp}).mappings().first()
    if not fe:
        raise ValueError("Emitente FE não encontrado para o FESTAMP do documento.")
    fe = dict(fe)

    ndoc = _to_int(ft.get("NDOC"), 0)
    serie = (ft.get("SERIE") or "").strip()
    ftano = _to_int(ft.get("FTANO"), 0)
    if ndoc <= 0 or not serie or ftano <= 0:
        raise ValueError("Dados de série inválidos para assinatura (NDOC/SERIE/ANO).")

    srow = session.execute(text("""
        SELECT TOP 1 FTSSTAMP, ISNULL(TIPOSAFT,'') AS TIPOSAFT
        FROM dbo.FTS
        WHERE
            FESTAMP=:festamp
            AND NDOC=:ndoc
            AND ISNULL(SERIE,'')=:serie
            AND ANO=:ano
    """), {"festamp": festamp, "ndoc": ndoc, "serie": serie, "ano": ftano}).mappings().first()

    prev_signature = ""
    if hash_ant_override is not None:
        prev_signature = str(hash_ant_override or "").strip()
    else:
        prev_row = session.execute(text("""
            SELECT TOP 1 ISNULL(ASSINATURA,'') AS ASSINATURA
            FROM dbo.FT
            WHERE
                FESTAMP=:festamp
                AND NDOC=:ndoc
                AND ISNULL(SERIE,'')=:serie
                AND ISNULL(FTANO,0)=:ano
                AND ISNULL(FNO,0) < :fno
                AND ISNULL(BLOQUEADO,0)=1
            ORDER BY ISNULL(FNO,0) DESC, FTSTAMP DESC
        """), {
            "festamp": festamp,
            "ndoc": ndoc,
            "serie": serie,
            "ano": ftano,
            "fno": _to_int(ft.get("FNO"), 0),
        }).mappings().first()
        prev_signature = str((prev_row or {}).get("ASSINATURA") or "").strip()

    if srow:
        ft["TIPOSAFT"] = str(srow.get("TIPOSAFT") or "").strip()
    if str(ft.get("TIPOSAFT") or "").strip().upper() in {"PF", "OR"}:
        raise ValueError("Documentos PF/OR não usam assinatura fiscal.")

    message = build_ft_hash_message(ft, fi_rows, prev_signature)
    digest_bytes, digest_hex = sha1_hex(message)

    private_key = load_private_key_from_pem(fe.get("RSA_PRIV_PATH") or "")
    signature_bytes = sign_sha1_prehashed(private_key, digest_bytes)
    signature_b64 = b64encode_signature(signature_bytes)

    hashver = (ft.get("HASHVER") or "").strip() or "1"
    keyid = (ft.get("KEYID") or "").strip() or (fe.get("KEYID") or "").strip()
    if not keyid:
        keyid = f"{(fe.get('NIF') or '').strip()}_{ftano}"

    return {
        "HASHVER": hashver,
        "HASHANT": prev_signature[:128],
        "HASH": digest_hex,
        "ASSINATURA": signature_b64,
        "KEYID": keyid,
        "MESSAGE": message,
        "DIGEST_HEX": digest_hex,
    }
