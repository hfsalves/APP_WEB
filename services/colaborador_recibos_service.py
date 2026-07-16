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


def _documents_root() -> Path | None:
    configured = str(
        current_app.config.get("COLAB_RECIBOS_ROOT")
        or os.environ.get("COLAB_RECIBOS_ROOT")
        or ""
    ).strip()
    if not configured:
        return None
    try:
        root = Path(configured).expanduser().resolve()
    except OSError:
        return None
    return root if root.is_dir() else None


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
            ORDER BY BO.DATAOBRA DESC, BO.BOSTAMP DESC
        """, peno)
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


def _insert_signature_attachment(cursor, bostamp: str, peno: int, year: int, month: int, image: bytes, user_login: str) -> None:
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
        "descricao": "Assinatura do colaborador - mapa de ajudas de custo",
        "bdados": pyodbc.Binary(image),
        "fullname": "",
        "fname": f"assinatura_ac_{peno}_{year:04d}{month:02d}.png"[:150],
        "fext": "png",
        "flen": len(image),
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

    directory = _company_documents_dir(colaborador)
    if not directory:
        result["warning"] = "Servidor de documentos indisponível para esta empresa."
        return result

    try:
        documents = [
            document
            for path in directory.iterdir()
            if path.is_file() and (document := _document_data(path, peno)) is not None
        ]
    except OSError:
        current_app.logger.exception("Erro ao consultar os recibos do colaborador.")
        result["warning"] = "Não foi possível consultar os documentos do colaborador."
        return result

    ac_dossiers = _load_ac_dossiers(colaborador)
    # Only a generated AC map can require a signature. Historical BO records
    # without the corresponding AC PDF must not permanently block receipts.
    available_ac_months = {
        _period_key(document["year"], document["month"])
        for document in documents
        if document["type"] == "AC"
    }
    unsigned_months = sorted(
        key
        for key, dossier in ac_dossiers.items()
        if key in available_ac_months and not dossier.get("signed")
    )
    block_rv_from = unsigned_months[0] if unsigned_months else None
    visible_documents: list[dict[str, Any]] = []
    for document in documents:
        period = _period_key(document["year"], document["month"])
        if document["type"] == "AC":
            dossier = ac_dossiers.get(period)
            document["signed"] = bool(dossier and dossier.get("signed"))
            document["signable"] = bool(dossier and not dossier.get("signed"))
            document["dossier_missing"] = not bool(dossier)
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
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    clean_filename = Path(str(filename or "")).name
    if not peno or clean_filename != filename:
        return None
    directory = _company_documents_dir(colaborador)
    if not directory:
        return None
    try:
        path = (directory / clean_filename).resolve()
        path.relative_to(directory)
    except (OSError, ValueError):
        return None
    document = _document_data(path, peno)
    if not document or not path.is_file():
        return None
    return path, document


def sign_colaborador_ac_document(user: Any, filename: str, signature_data: Any) -> dict[str, Any]:
    receipt = get_colaborador_recibo_path(user, filename)
    if not receipt:
        raise ValueError("Documento não encontrado.")
    _, document = receipt
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
        _insert_signature_attachment(
            cursor,
            str(row.BOSTAMP or "").strip(),
            peno,
            document["year"],
            document["month"],
            image,
            _user_login(user),
        )
        connection.commit()
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return {"ok": True, "message": "Mapa de ajudas de custo assinado."}
