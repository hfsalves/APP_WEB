from __future__ import annotations

import base64
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pyodbc
from flask import current_app

from services.colaborador_despesas_service import (
    _new_stamp,
    _phc_conn_str,
    _phc_insert,
    get_colaborador_context,
)


DOCUMENT_RE = re.compile(
    r"^(?P<tipo>AC|RV)_(?P<peno>\d+)_(?P<periodo>(?:19|20)\d{2}(?:0[1-9]|1[0-2]))\.pdf$",
    re.IGNORECASE,
)
MONTH_NAMES = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)
SIGNATURE_MAX_BYTES = 2 * 1024 * 1024
DOCUMENTS_FROM_DATE = "20250101"
SIGNATURE_DESCRIPTION = "Assinatura do colaborador - mapa de ajudas de custo"


def _documents_root() -> Path | None:
    configured = str(
        current_app.config.get("COLAB_RECIBOS_ROOT")
        or os.environ.get("COLAB_RECIBOS_ROOT")
        or ""
    ).strip()
    # The production service runs on Windows and reads directly from the
    # domain document share. Local development still supplies its own root.
    if not configured and os.name == "nt":
        configured = "//10.0.1.13/docs"
    if not configured:
        return None
    try:
        root = Path(configured).expanduser().resolve()
    except OSError:
        return None
    return root if root.is_dir() else None


def _signatures_root() -> Path | None:
    configured = str(
        current_app.config.get("COLAB_ASSINATURAS_ROOT")
        or os.environ.get("COLAB_ASSINATURAS_ROOT")
        or ""
    ).strip()
    if not configured and os.name == "nt":
        configured = "//10.0.1.13/docs/assinaturas"
    if not configured:
        return None
    try:
        return Path(configured).expanduser().resolve()
    except OSError:
        return None


def _company_documents_dir(colaborador: dict[str, Any]) -> Path | None:
    root = _documents_root()
    phc_db = str(colaborador.get("phc_db") or "").strip()
    if not root or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", phc_db):
        return None
    try:
        directory = (root / phc_db).resolve()
        directory.relative_to(root)
    except (OSError, ValueError):
        return None
    return directory if directory.is_dir() else None


def _document_data(path: Path, peno: int) -> dict[str, Any] | None:
    match = DOCUMENT_RE.fullmatch(path.name)
    if not match or int(match.group("peno")) != peno:
        return None
    period = match.group("periodo")
    year = int(period[:4])
    month = int(period[4:])
    doc_type = match.group("tipo").upper()
    return {
        "filename": path.name,
        "type": doc_type,
        "title": "Recibo de vencimento" if doc_type == "RV" else "Mapa de ajudas de custo",
        "year": year,
        "month": month,
        "period_label": f"{MONTH_NAMES[month - 1]} {year}",
    }


def _document_for_period(doc_type: str, peno: int, year: int, month: int) -> dict[str, Any]:
    clean_type = str(doc_type or '').upper()
    return {
        "filename": f"{clean_type}_{int(peno):05d}_{int(year):04d}{int(month):02d}.pdf",
        "type": clean_type,
        "title": "Recibo de vencimento" if clean_type == "RV" else "Mapa de ajudas de custo",
        "year": int(year),
        "month": int(month),
        "period_label": f"{MONTH_NAMES[int(month) - 1]} {int(year)}",
    }


def _period_key(year: int, month: int) -> tuple[int, int]:
    return (int(year), int(month))


def _load_ac_dossiers(colaborador: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip()
    if not peno or not phc_db:
        return {}

    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                BO.BOSTAMP,
                BO.DATAOBRA,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM dbo.ANEXOS AS A
                    WHERE A.RECSTAMP = BO.BOSTAMP
                ) THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS ASSINADO
            FROM dbo.BO AS BO
            WHERE BO.NDOS = 62
              AND BO.NOPAT = ?
              AND BO.DATAOBRA IS NOT NULL
              AND BO.DATAOBRA >= CONVERT(datetime, ?, 112)
            ORDER BY BO.DATAOBRA DESC, BO.BOSTAMP DESC
        """, peno, DOCUMENTS_FROM_DATE)
        dossiers: dict[tuple[int, int], dict[str, Any]] = {}
        for row in cursor.fetchall():
            dataobra = row.DATAOBRA
            if not dataobra:
                continue
            key = _period_key(dataobra.year, dataobra.month)
            # If PHC has more than one dossier for the month, one signed dossier
            # is enough to consider that monthly map signed.
            current = dossiers.get(key)
            signed = bool(row.ASSINADO)
            if not current or (signed and not current["signed"]):
                dossiers[key] = {
                    "bostamp": str(row.BOSTAMP or "").strip(),
                    "signed": signed,
                }
        return dossiers
    except Exception:
        current_app.logger.exception("Erro ao consultar dossiers de ajudas de custo no PHC.")
        return {}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _load_salary_receipts(colaborador: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip()
    if not peno or not phc_db:
        return {}

    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT PR.PRSTAMP, PR.DATA, PR.RECIBO
            FROM dbo.PR AS PR
            WHERE PR.NO = ?
              AND PR.DATA IS NOT NULL
              AND PR.DATA >= CONVERT(datetime, ?, 112)
            ORDER BY PR.DATA DESC, PR.RECIBO DESC, PR.PRSTAMP DESC
        """, peno, DOCUMENTS_FROM_DATE)
        receipts: dict[tuple[int, int], dict[str, Any]] = {}
        for row in cursor.fetchall():
            receipt_date = row.DATA
            if not receipt_date:
                continue
            key = _period_key(receipt_date.year, receipt_date.month)
            if key not in receipts:
                receipts[key] = {
                    "prstamp": str(row.PRSTAMP or "").strip(),
                    "receipt_number": int(row.RECIBO or 0),
                }
        return receipts
    except Exception:
        current_app.logger.exception("Erro ao consultar recibos de vencimento no PHC.")
        return {}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _decode_signature(data_url: Any) -> bytes:
    raw = str(data_url or "").strip()
    match = re.fullmatch(r"data:image/png;base64,([A-Za-z0-9+/=]+)", raw)
    if not match:
        raise ValueError("A assinatura enviada não é uma imagem PNG válida.")
    try:
        image = base64.b64decode(match.group(1), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("Não foi possível ler a assinatura.") from exc
    if not image.startswith(b"\x89PNG\r\n\x1a\n") or len(image) > SIGNATURE_MAX_BYTES:
        raise ValueError("A assinatura enviada não é válida.")
    return image


def _user_login(user: Any) -> str:
    for field in ("LOGIN", "NOME", "usercode", "username", "login", "nome"):
        value = str(getattr(user, field, "") or "").strip()
        if value:
            return value[:30]
    return "APP"


def _store_signature_file(phc_db: str, bostamp: str, peno: int, year: int, month: int, image: bytes) -> dict[str, Any]:
    root = _signatures_root()
    if not root:
        raise ValueError("A pasta partilhada para assinaturas não está disponível.")

    db_folder = re.sub(r"[^A-Za-z0-9_-]", "_", str(phc_db or "").upper()) or "PHC"
    stamp_suffix = re.sub(r"[^A-Za-z0-9]", "", str(bostamp or ""))[-12:] or _new_stamp()[-12:]
    fname = f"assinatura_ac_{int(peno)}_{int(year):04d}{int(month):02d}_{stamp_suffix}.png"
    directory = root / db_folder
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / fname).resolve()
        path.relative_to(root)
        path.write_bytes(image)
    except OSError as exc:
        raise ValueError("Não foi possível guardar a assinatura na pasta partilhada.") from exc
    return {
        "path": path,
        "fullname": str(path),
        "fname": Path(fname).stem[:150],
        "fext": "png",
        "flen": len(image),
    }


def _insert_signature_attachment(cursor, bostamp: str, signature_file: dict[str, Any], user_login: str) -> None:
    now = datetime.now()
    hour = now.strftime("%H:%M:%S")
    _phc_insert(cursor, "ANEXOS", {
        "anexosstamp": _new_stamp(),
        "oritable": "BO",
        "tabnm": "Dossiers Internos",
        "resumo": "Assinatura",
        "grupo": "",
        "recstamp": bostamp,
        "uniqueid": "",
        "descricao": SIGNATURE_DESCRIPTION,
        "bdados": pyodbc.Binary(b""),
        "fullname": str(signature_file["fullname"]),
        "fname": str(signature_file["fname"]),
        "fext": str(signature_file["fext"]),
        "flen": int(signature_file["flen"]),
        "tipo": 2,
        "passw": "",
        "origem": "",
        "keylook": "",
        "tpdos": 62,
        "tpdoc": 0,
        "ausrinis": user_login,
        "ausrdata": now,
        "ausrhora": hour,
        "eusrinis": user_login,
        "eusrdata": now,
        "eusrhora": hour,
        "anexopaistamp": "",
        "assinatura": 1,
        "timestamp": 0,
        "anexoversaostamp": "",
        "versao": 1,
        "idustamp": "",
        "ousrinis": user_login,
        "ousrdata": now,
        "ousrhora": hour,
        "usrinis": user_login,
        "usrdata": now,
        "usrhora": hour,
        "marcada": 0,
        "zipado": 0,
        "bdadosstamp": "",
        "invisivel": 0,
        "checkout": 0,
        "cuserno": 0,
        "cusername": "",
        "usnoopen": 0,
        "usnaopen": "",
        "isemail": 0,
        "emailid": "",
        "emaildata": datetime(1900, 1, 1),
        "startwkf": 0,
        "wtwstamp": "",
        "emailsubj": "",
        "privado": 0,
        "nivel": 0,
        "lsgq": 0,
        "u_enviado": 0,
        "u_jaobra": 0,
        "fiscrel": 0,
        "original": 1,
        "filestorageid": "",
        "marcadoenviar": 0,
        "ziparquivodigital": 0,
    })


def list_colaborador_recibos(user) -> dict[str, Any]:
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    result: dict[str, Any] = {
        "ok": True,
        "colaborador": colaborador,
        "documents": [],
        "warning": "",
    }
    if not peno or not str(colaborador.get("phc_db") or "").strip():
        result["warning"] = "Ficha de colaborador incompleta."
        return result

    ac_dossiers = _load_ac_dossiers(colaborador)
    salary_receipts = _load_salary_receipts(colaborador)
    documents: list[dict[str, Any]] = []
    for (year, month), dossier in ac_dossiers.items():
        document = _document_for_period("AC", peno, year, month)
        document["signed"] = bool(dossier.get("signed"))
        document["signable"] = not document["signed"]
        documents.append(document)

    for year, month in salary_receipts:
        documents.append(_document_for_period("RV", peno, year, month))

    unsigned_months = sorted(
        key
        for key, dossier in ac_dossiers.items()
        if not dossier.get("signed")
    )
    block_rv_from = unsigned_months[0] if unsigned_months else None
    visible_documents: list[dict[str, Any]] = []
    for document in documents:
        period = _period_key(document["year"], document["month"])
        if document["type"] == "AC":
            visible_documents.append(document)
            continue
        if block_rv_from and period >= block_rv_from:
            continue
        visible_documents.append(document)

    result["documents"] = sorted(
        visible_documents,
        key=lambda item: (int(item["year"]), int(item["month"]), item["type"]),
        reverse=True,
    )
    result["blocked_rv_from"] = block_rv_from
    return result


def get_colaborador_recibo_path(user, filename: str) -> tuple[Path, dict[str, Any]] | None:
    document = get_colaborador_recibo_document(user, filename)
    if not document:
        return None
    colaborador = get_colaborador_context(user)
    directory = _company_documents_dir(colaborador)
    if not directory:
        return None
    clean_filename = document["filename"]
    try:
        path = (directory / clean_filename).resolve()
        path.relative_to(directory)
    except (OSError, ValueError):
        return None
    if not path.is_file():
        return None
    return path, document


def get_colaborador_recibo_document(user, filename: str) -> dict[str, Any] | None:
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    clean_filename = Path(str(filename or "")).name
    if not peno or clean_filename != filename:
        return None
    return _document_data(Path(clean_filename), peno)


def sign_colaborador_ac_document(user: Any, filename: str, signature_data: Any) -> dict[str, Any]:
    document = get_colaborador_recibo_document(user, filename)
    if not document:
        raise ValueError("Documento não encontrado.")
    if document["type"] != "AC":
        raise ValueError("Apenas os mapas de ajudas de custo podem ser assinados.")

    image = _decode_signature(signature_data)
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip()
    period = _period_key(document["year"], document["month"])
    dossier = _load_ac_dossiers(colaborador).get(period)
    if not peno or not phc_db or not dossier:
        raise ValueError("Não existe dossier de ajudas de custo para este mês.")
    if dossier.get("signed"):
        raise ValueError("Este mapa de ajudas de custo já se encontra assinado.")

    connection = None
    cursor = None
    signature_file: dict[str, Any] | None = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT TOP 1 BO.BOSTAMP
            FROM dbo.BO AS BO
            WHERE BO.BOSTAMP = ?
              AND BO.NDOS = 62
              AND BO.NOPAT = ?
              AND YEAR(BO.DATAOBRA) = ?
              AND MONTH(BO.DATAOBRA) = ?
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.ANEXOS AS A WHERE A.RECSTAMP = BO.BOSTAMP
              )
        """, str(dossier["bostamp"]), peno, document["year"], document["month"])
        row = cursor.fetchone()
        if not row:
            raise ValueError("O mapa já foi assinado ou deixou de estar disponível.")
        signature_file = _store_signature_file(
            phc_db,
            str(row.BOSTAMP or "").strip(),
            peno,
            document["year"],
            document["month"],
            image,
        )
        _insert_signature_attachment(
            cursor,
            str(row.BOSTAMP or "").strip(),
            signature_file,
            _user_login(user),
        )
        connection.commit()
    except Exception:
        if connection:
            connection.rollback()
        if signature_file:
            try:
                Path(signature_file["path"]).unlink(missing_ok=True)
            except OSError:
                pass
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return {"ok": True, "message": "Mapa de ajudas de custo assinado."}


def migrate_legacy_signature_attachments(phc_db: str) -> int:
    """Moves signatures previously stored in BDADOS to the shared document server."""
    connection = None
    cursor = None
    migrated = 0
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT ANEXOSSTAMP, RECSTAMP, FNAME, FEXT, BDADOS
            FROM dbo.ANEXOS
            WHERE CONVERT(varchar(max), DESCRICAO) = ?
              AND ASSINATURA = 1
              AND (FULLNAME IS NULL OR LTRIM(RTRIM(CONVERT(varchar(max), FULLNAME))) = '')
        """, SIGNATURE_DESCRIPTION)
        for row in cursor.fetchall():
            image = bytes(row.BDADOS or b"")
            if not image.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            original = Path(str(row.FNAME or "assinatura")).stem
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", original) or "assinatura"
            root = _signatures_root()
            if not root:
                raise ValueError("A pasta partilhada para assinaturas não está disponível.")
            folder = root / (re.sub(r"[^A-Za-z0-9_-]", "_", str(phc_db).upper()) or "PHC")
            folder.mkdir(parents=True, exist_ok=True)
            path = (folder / f"{safe_name}_{str(row.ANEXOSSTAMP or '').strip()[-8:]}.png").resolve()
            path.relative_to(root)
            path.write_bytes(image)
            cursor.execute("""
                UPDATE dbo.ANEXOS
                SET FULLNAME = ?, FNAME = ?, FEXT = 'png', FLEN = ?, BDADOS = ?
                WHERE ANEXOSSTAMP = ?
            """, str(path), path.stem[:150], len(image), pyodbc.Binary(b""), row.ANEXOSSTAMP)
            migrated += 1
        connection.commit()
        return migrated
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
