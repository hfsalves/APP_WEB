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


def sign_ft_document(session, ftstamp: str, current_user: str = "") -> dict:
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
        SELECT TOP 1 FTSSTAMP
        FROM dbo.FTS
        WHERE
            FESTAMP=:festamp
            AND NDOC=:ndoc
            AND ISNULL(SERIE,'')=:serie
            AND ANO=:ano
    """), {"festamp": festamp, "ndoc": ndoc, "serie": serie, "ano": ftano}).mappings().first()

    hash_ant = ""
    if srow and srow.get("FTSSTAMP"):
        try:
            hx = session.execute(text("""
                SELECT TOP 1 ISNULL(LAST_HASH,'') AS LAST_HASH
                FROM dbo.FTSX
                WHERE FTSSTAMP=:s
            """), {"s": srow.get("FTSSTAMP")}).mappings().first()
            hash_ant = (hx.get("LAST_HASH") if hx else "") or ""
        except Exception:
            hash_ant = ""

    message = build_ft_hash_message(ft, fi_rows, hash_ant)
    digest_bytes, hash_hex = sha1_hex(message)

    private_key = load_private_key_from_pem(fe.get("RSA_PRIV_PATH") or "")
    signature_bytes = sign_sha1_prehashed(private_key, digest_bytes)
    signature_b64 = b64encode_signature(signature_bytes)

    hashver = (ft.get("HASHVER") or "").strip() or "1"
    keyid = (ft.get("KEYID") or "").strip() or (fe.get("KEYID") or "").strip()
    if not keyid:
        keyid = f"{(fe.get('NIF') or '').strip()}_{ftano}"

    return {
        "HASHVER": hashver,
        "HASHANT": hash_ant,
        "HASH": hash_hex,
        "ASSINATURA": signature_b64,
        "KEYID": keyid,
        "MESSAGE": message,
        "DIGEST_HEX": hash_hex,
    }

