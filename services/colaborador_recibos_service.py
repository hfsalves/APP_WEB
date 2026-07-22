from __future__ import annotations

import base64
import io
import os
import re
import tempfile
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Any

import pyodbc
from flask import current_app
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import text

from models import db

from services.colaborador_despesas_service import (
    _new_stamp,
    _phc_conn_str,
    _phc_insert,
    get_colaborador_context,
)


DOCUMENT_RE = re.compile(
    r"^(?P<tipo>AC|KM|KMS|RV)_(?P<peno>\d+)_(?P<periodo>(?:19|20)\d{2}(?:0[1-9]|1[0-2]))\.pdf$",
    re.IGNORECASE,
)
MONTH_NAMES = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)
SIGNATURE_MAX_BYTES = 2 * 1024 * 1024
DOCUMENTS_FROM_DATE = "20250101"
SIGNATURE_DESCRIPTION = "Assinatura do colaborador - mapa de ajudas de custo"
SIGNABLE_DOCUMENT_TYPES = {"AC", "KMS"}
KMS_MAP_TABLE = "COLAB_KMS_DOSSIER_MAP"


def _document_title(doc_type: str) -> str:
    return {
        "RV": "Recibo de vencimento",
        "KMS": "Mapa de quilómetros",
    }.get(str(doc_type or "").upper(), "Mapa de ajudas de custo")


def _normalise_document_type(doc_type: str) -> str:
    clean_type = str(doc_type or "").upper()
    return "KMS" if clean_type in {"KM", "KMS"} else clean_type


def _signature_description(doc_type: str) -> str:
    if str(doc_type or "").upper() == "KMS":
        return "Assinatura do colaborador - mapa de quilómetros"
    return SIGNATURE_DESCRIPTION


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


def _document_path_in_directory(directory: Path, filename: str) -> Path | None:
    """Resolve a document name safely, including shares mounted on case-sensitive hosts."""
    clean_filename = Path(str(filename or "")).name
    if not clean_filename or clean_filename != filename:
        return None
    try:
        direct_path = (directory / clean_filename).resolve()
        direct_path.relative_to(directory)
    except (OSError, ValueError):
        return None
    if direct_path.is_file():
        return direct_path
    try:
        for candidate in directory.iterdir():
            if candidate.is_file() and candidate.name.casefold() == clean_filename.casefold():
                path = candidate.resolve()
                path.relative_to(directory)
                return path
    except OSError:
        return None
    return None


def _document_data(path: Path, peno: int) -> dict[str, Any] | None:
    match = DOCUMENT_RE.fullmatch(path.name)
    if not match or int(match.group("peno")) != peno:
        return None
    period = match.group("periodo")
    year = int(period[:4])
    month = int(period[4:])
    doc_type = _normalise_document_type(match.group("tipo"))
    return {
        "filename": path.name,
        "type": doc_type,
        "title": _document_title(doc_type),
        "year": year,
        "month": month,
        "period_label": f"{MONTH_NAMES[month - 1]} {year}",
    }


def _document_for_period(
    doc_type: str,
    employee_number: int | str,
    year: int,
    month: int,
    filename: str | None = None,
) -> dict[str, Any]:
    clean_type = _normalise_document_type(doc_type)
    file_prefix = "KM" if clean_type == "KMS" else clean_type
    clean_employee_number = int(str(employee_number or "0").strip() or 0)
    return {
        "filename": filename or f"{file_prefix}_{clean_employee_number:05d}_{int(year):04d}{int(month):02d}.pdf",
        "type": clean_type,
        "title": _document_title(clean_type),
        "year": int(year),
        "month": int(month),
        "period_label": f"{MONTH_NAMES[int(month) - 1]} {int(year)}",
    }


def _period_key(year: int, month: int) -> tuple[int, int]:
    return (int(year), int(month))


def _salary_pdf_employee_number(colaborador: dict[str, Any]) -> int:
    """Gets the employee number used by the payroll PDF filename.

    HSOLS_FR publishes salary receipts using PE2.U_NUMIMP, while the PHC PR
    records and the remaining companies use PE.NO.
    """
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip().upper()
    if not peno or phc_db != "HSOLS_FR":
        return peno

    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(
            _phc_conn_str(phc_db, str(colaborador.get("phc_server") or "").strip()),
            timeout=12,
        )
        cursor = connection.cursor()
        row = cursor.execute("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(PE2.U_NUMIMP, ''))) AS U_NUMIMP
            FROM dbo.PE AS PE
            INNER JOIN dbo.PE2 AS PE2
              ON PE2.PE2STAMP = PE.PESTAMP
            WHERE PE.NO = ?
        """, peno).fetchone()
        value = str(row.U_NUMIMP or "").strip() if row else ""
        return int(value) if re.fullmatch(r"\d+", value) else peno
    except Exception:
        current_app.logger.exception("Erro ao obter PE2.U_NUMIMP para recibos HSOLS_FR.")
        return peno
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _ensure_kms_dossier_map_schema() -> None:
    """Keeps the legacy PDF-to-PHC kilometre mapping out of the page request."""
    db.session.execute(text(f"""
        IF OBJECT_ID('dbo.{KMS_MAP_TABLE}', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.{KMS_MAP_TABLE} (
                PHC_DB VARCHAR(128) NOT NULL,
                BOSTAMP VARCHAR(50) NOT NULL,
                PENO INT NOT NULL,
                ANO SMALLINT NOT NULL,
                MES TINYINT NOT NULL,
                FILENAME VARCHAR(255) NOT NULL CONSTRAINT DF_{KMS_MAP_TABLE}_FILENAME DEFAULT '',
                KMS_TOTAL DECIMAL(12,2) NOT NULL CONSTRAINT DF_{KMS_MAP_TABLE}_KMS_TOTAL DEFAULT 0,
                CREATED_AT DATETIME2 NOT NULL CONSTRAINT DF_{KMS_MAP_TABLE}_CREATED_AT DEFAULT SYSDATETIME(),
                UPDATED_AT DATETIME2 NOT NULL CONSTRAINT DF_{KMS_MAP_TABLE}_UPDATED_AT DEFAULT SYSDATETIME(),
                CONSTRAINT PK_{KMS_MAP_TABLE} PRIMARY KEY CLUSTERED (PHC_DB, BOSTAMP)
            );
            CREATE INDEX IX_{KMS_MAP_TABLE}_COLABORADOR
                ON dbo.{KMS_MAP_TABLE} (PHC_DB, PENO, ANO, MES);
        END
    """))
    db.session.commit()


def _load_cached_kms_dossiers(colaborador: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip().upper()
    if not peno or not phc_db:
        return {}
    try:
        _ensure_kms_dossier_map_schema()
        rows = db.session.execute(text(f"""
            SELECT PHC_DB, BOSTAMP, ANO, MES, FILENAME, KMS_TOTAL
            FROM dbo.{KMS_MAP_TABLE}
            WHERE PHC_DB = :phc_db
              AND PENO = :peno
              AND (ANO > 2025 OR (ANO = 2025 AND MES >= 1))
        """), {"phc_db": phc_db, "peno": peno}).mappings().all()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao consultar a cache de mapas de quilómetros.")
        return {}
    return {
        _period_key(row["ANO"], row["MES"]): {
            "bostamp": str(row["BOSTAMP"] or "").strip(),
            "filename": str(row["FILENAME"] or "").strip(),
            "kms_total": Decimal(str(row["KMS_TOTAL"] or 0)),
        }
        for row in rows
    }


def _store_kms_dossier_mappings(colaborador: dict[str, Any], dossiers: dict[tuple[int, int], dict[str, Any]]) -> None:
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip().upper()
    if not peno or not phc_db or not dossiers:
        return
    try:
        _ensure_kms_dossier_map_schema()
        for (year, month), dossier in dossiers.items():
            db.session.execute(text(f"""
                MERGE dbo.{KMS_MAP_TABLE} AS target
                USING (SELECT :phc_db AS PHC_DB, :bostamp AS BOSTAMP) AS source
                ON target.PHC_DB = source.PHC_DB AND target.BOSTAMP = source.BOSTAMP
                WHEN MATCHED THEN UPDATE SET
                    PENO = :peno, ANO = :year, MES = :month, FILENAME = :filename,
                    KMS_TOTAL = :kms_total, UPDATED_AT = SYSDATETIME()
                WHEN NOT MATCHED THEN INSERT (PHC_DB, BOSTAMP, PENO, ANO, MES, FILENAME, KMS_TOTAL)
                    VALUES (:phc_db, :bostamp, :peno, :year, :month, :filename, :kms_total);
            """), {
                "phc_db": phc_db,
                "bostamp": dossier["bostamp"],
                "peno": peno,
                "year": year,
                "month": month,
                "filename": dossier.get("filename") or "",
                "kms_total": dossier.get("kms_total") or Decimal("0"),
            })
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao guardar a cache de mapas de quilómetros.")


def _extract_km_total(pdf_path: Path) -> Decimal | None:
    """Extract the kilometre total printed by PHC on a monthly KM map."""
    try:
        reader = PdfReader(str(pdf_path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        current_app.logger.warning("Não foi possível ler os quilómetros de %s.", pdf_path.name)
        return None

    matches = re.findall(r"(\d{1,7}(?:[.,]\d{1,2})?)\s*Total\b", text, re.IGNORECASE)
    if not matches:
        return None
    try:
        raw_total = matches[-1]
        if "," in raw_total:
            raw_total = raw_total.replace(".", "").replace(",", ".")
        return Decimal(raw_total)
    except InvalidOperation:
        return None


def _km_documents_from_share(colaborador: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    """Lists only this collaborator's legacy PHC KM PDFs from the document share."""
    peno = int(colaborador.get("peno") or 0)
    directory = _company_documents_dir(colaborador)
    if not peno or not directory:
        return {}

    documents: dict[tuple[int, int], dict[str, Any]] = {}
    try:
        candidates = list(directory.iterdir())
    except OSError:
        current_app.logger.warning("Não foi possível consultar a pasta de mapas de quilómetros.")
        return {}

    for path in candidates:
        if not path.is_file():
            continue
        document = _document_data(path, peno)
        if not document or document["type"] != "KMS":
            continue
        document["kms_total"] = _extract_km_total(path)
        documents[_period_key(document["year"], document["month"])] = document
    return documents


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
                    "ndos": 62,
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


def _discover_kms_dossiers_from_share(
    colaborador: dict[str, Any],
    km_documents: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> dict[tuple[int, int], dict[str, Any]]:
    """Links legacy KM PDFs to their PHC dossier using month and kilometre total.

    In the existing PHC dossiers, ``BO.NOPAT`` is always zero and the header is
    assigned to the generic HSOLS entity. The employee number is only present in
    the PDF filename, while the exact kilometre total is stored in ``BI.QTT``.
    """
    phc_db = str(colaborador.get("phc_db") or "").strip()
    km_documents = km_documents if km_documents is not None else _km_documents_from_share(colaborador)
    if not km_documents or not phc_db:
        return {}

    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                BO.BOSTAMP,
                BO.NDOS,
                BO.DATAOBRA,
                BI.QTT AS KMS_TOTAL,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM dbo.ANEXOS AS A
                    WHERE A.RECSTAMP = BO.BOSTAMP
                ) THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS ASSINADO
            FROM dbo.BO AS BO
            INNER JOIN dbo.BI AS BI ON BI.BOSTAMP = BO.BOSTAMP
            WHERE BO.DATAOBRA IS NOT NULL
              AND BO.DATAOBRA >= CONVERT(datetime, ?, 112)
              AND UPPER(LTRIM(RTRIM(ISNULL(BO.NMDOS, '')))) LIKE '%QUIL%'
            ORDER BY BO.DATAOBRA DESC, BO.BOSTAMP DESC
        """, DOCUMENTS_FROM_DATE)
        candidates: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for row in cursor.fetchall():
            dataobra = row.DATAOBRA
            if not dataobra:
                continue
            try:
                kms_total = Decimal(str(row.KMS_TOTAL or 0))
            except InvalidOperation:
                continue
            candidates.setdefault(_period_key(dataobra.year, dataobra.month), []).append({
                "bostamp": str(row.BOSTAMP or "").strip(),
                "signed": bool(row.ASSINADO),
                "ndos": int(row.NDOS or 0),
                "kms_total": kms_total,
            })

        dossiers: dict[tuple[int, int], dict[str, Any]] = {}
        for key, document in km_documents.items():
            kms_total = document.get("kms_total")
            if kms_total is None:
                continue
            matching = [
                item for item in candidates.get(key, [])
                if abs(item["kms_total"] - kms_total) < Decimal("0.01")
            ]
            if len(matching) == 1:
                dossiers[key] = {**matching[0], "filename": document["filename"]}
            elif len(matching) > 1:
                current_app.logger.warning(
                    "Foram encontrados %s dossiers de quilómetros para %s/%s com %s km.",
                    len(matching), key[1], key[0], kms_total,
                )
        return dossiers
    except Exception:
        current_app.logger.exception("Erro ao consultar dossiers de quilómetros no PHC.")
        return {}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _load_kms_dossiers(colaborador: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    """Loads mapped KM dossiers from SQL; PDF inspection is only a one-off fallback."""
    cached = _load_cached_kms_dossiers(colaborador)
    if not cached:
        discovered = _discover_kms_dossiers_from_share(colaborador)
        _store_kms_dossier_mappings(colaborador, discovered)
        return discovered

    phc_db = str(colaborador.get("phc_db") or "").strip()
    stamps = [item["bostamp"] for item in cached.values() if item.get("bostamp")]
    if not phc_db or not stamps:
        return {}
    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        placeholders = ", ".join("?" for _ in stamps)
        cursor.execute(f"""
            SELECT BO.BOSTAMP, BO.NDOS,
                CASE WHEN EXISTS (
                    SELECT 1 FROM dbo.ANEXOS AS A WHERE A.RECSTAMP = BO.BOSTAMP
                ) THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS ASSINADO
            FROM dbo.BO AS BO
            WHERE BO.BOSTAMP IN ({placeholders})
        """, *stamps)
        state = {
            str(row.BOSTAMP or "").strip(): {
                "ndos": int(row.NDOS or 0),
                "signed": bool(row.ASSINADO),
            }
            for row in cursor.fetchall()
        }
        return {
            key: {**item, **state.get(item["bostamp"], {})}
            for key, item in cached.items()
            if item["bostamp"] in state
        }
    except Exception:
        current_app.logger.exception("Erro ao consultar os dossiers de quilómetros no PHC.")
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


def _signature_overlay_pdf(page_width: float, page_height: float, image: bytes) -> bytes:
    """Builds a transparent signature overlay for the standard AC map layout."""
    with Image.open(io.BytesIO(image)).convert("RGBA") as source:
        grayscale = source.convert("L")
        alpha = grayscale.point(lambda value: max(0, min(255, (255 - value) * 3)))
        box = alpha.getbbox()
        if not box:
            raise ValueError("A assinatura não contém traço visível.")
        padding = 8
        box = (
            max(0, box[0] - padding), max(0, box[1] - padding),
            min(source.width, box[2] + padding), min(source.height, box[3] + padding),
        )
        signature = Image.new("RGBA", source.size, (23, 38, 59, 0))
        signature.putalpha(alpha)
        signature = signature.crop(box)
        signature_buffer = io.BytesIO()
        signature.save(signature_buffer, format="PNG")

    overlay_buffer = io.BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
    # The standard PHC map is A4 landscape; these proportional coordinates
    # keep the signature above the "Recebi a importância supra" signature line.
    overlay.drawImage(
        ImageReader(io.BytesIO(signature_buffer.getvalue())),
        page_width * 0.485,
        page_height * 0.162,
        width=page_width * 0.120,
        height=page_height * 0.045,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )
    overlay.save()
    return overlay_buffer.getvalue()


def _create_signed_claim_pdf(
    phc_db: str,
    peno: int,
    year: int,
    month: int,
    bostamp: str,
    image: bytes,
    doc_type: str,
    source_filename: str | None = None,
) -> dict[str, Any]:
    documents_root = _documents_root()
    signatures_root = _signatures_root()
    clean_db = re.sub(r"[^A-Za-z0-9_-]", "_", str(phc_db or "").upper()) or "PHC"
    clean_type = str(doc_type or "").upper()
    if clean_type not in SIGNABLE_DOCUMENT_TYPES:
        raise ValueError("Tipo de documento inválido para assinatura.")
    source_prefix = "KM" if clean_type == "KMS" else clean_type
    source_name = source_filename or f"{source_prefix}_{int(peno):05d}_{int(year):04d}{int(month):02d}.pdf"
    if not documents_root or not signatures_root:
        raise ValueError("A pasta partilhada de documentos não está disponível.")

    try:
        source_directory = (documents_root / clean_db).resolve()
        source_directory.relative_to(documents_root)
    except (OSError, ValueError) as exc:
        raise ValueError("Não foi possível localizar o mapa original.") from exc
    source = _document_path_in_directory(source_directory, source_name)
    if not source:
        raise ValueError("O PDF original deste mapa não está disponível. Contacte o departamento de RH.")

    stamp_suffix = re.sub(r"[^A-Za-z0-9]", "", str(bostamp or ""))[-12:] or _new_stamp()[-12:]
    fname = f"mapa_{clean_type.lower()}_assinado_{int(peno):05d}_{int(year):04d}{int(month):02d}_{stamp_suffix}.pdf"
    target_dir = signatures_root / clean_db
    temporary_path = None
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = (target_dir / fname).resolve()
        target.relative_to(signatures_root)
        reader = PdfReader(str(source))
        if not reader.pages:
            raise ValueError("O PDF original do mapa não tem páginas.")
        writer = PdfWriter()
        for index, page in enumerate(reader.pages):
            if index == 0:
                overlay = PdfReader(io.BytesIO(_signature_overlay_pdf(float(page.mediabox.width), float(page.mediabox.height), image)))
                page.merge_page(overlay.pages[0])
            writer.add_page(page)
        with tempfile.NamedTemporaryFile(dir=target_dir, suffix=".pdf", delete=False) as handle:
            temporary_path = Path(handle.name)
            writer.write(handle)
        os.replace(temporary_path, target)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Não foi possível criar o PDF assinado do mapa.") from exc
    finally:
        if temporary_path:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    return {
        "path": target,
        "fullname": str(target),
        "fname": target.stem[:150],
        "fext": "pdf",
        "flen": target.stat().st_size,
    }


def _insert_signature_attachment(
    cursor,
    bostamp: str,
    signature_file: dict[str, Any],
    user_login: str,
    ndos: int,
    doc_type: str,
) -> None:
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
        "descricao": _signature_description(doc_type),
        "bdados": pyodbc.Binary(b""),
        "fullname": str(signature_file["fullname"]),
        "fname": str(signature_file["fname"]),
        "fext": str(signature_file["fext"]),
        "flen": int(signature_file["flen"]),
        "tipo": 2,
        "passw": "",
        "origem": "",
        "keylook": "",
        "tpdos": int(ndos or 0),
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
    salary_pdf_number = _salary_pdf_employee_number(colaborador)
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
    kms_dossiers = _load_kms_dossiers(colaborador)
    salary_receipts = _load_salary_receipts(colaborador)
    documents: list[dict[str, Any]] = []
    for (year, month), dossier in ac_dossiers.items():
        document = _document_for_period("AC", peno, year, month)
        document["signed"] = bool(dossier.get("signed"))
        document["signable"] = not document["signed"]
        documents.append(document)

    for (year, month), dossier in kms_dossiers.items():
        document = _document_for_period("KMS", peno, year, month, dossier.get("filename") or None)
        document["signed"] = bool(dossier.get("signed"))
        document["signable"] = not document["signed"]
        documents.append(document)

    for year, month in salary_receipts:
        documents.append(_document_for_period("RV", salary_pdf_number, year, month))

    unsigned_months = sorted(
        key
        for dossiers in (ac_dossiers, kms_dossiers)
        for key, dossier in dossiers.items()
        if not dossier.get("signed")
    )
    block_rv_from = unsigned_months[0] if unsigned_months else None
    visible_documents: list[dict[str, Any]] = []
    for document in documents:
        period = _period_key(document["year"], document["month"])
        if document["type"] in SIGNABLE_DOCUMENT_TYPES:
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
    path = _document_path_in_directory(directory, document["filename"])
    if not path:
        return None
    return path, document


def get_colaborador_recibo_document(user, filename: str) -> dict[str, Any] | None:
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    clean_filename = Path(str(filename or "")).name
    if not peno or clean_filename != filename:
        return None
    match = DOCUMENT_RE.fullmatch(clean_filename)
    if not match:
        return None
    document_type = _normalise_document_type(match.group("tipo"))
    expected_number = _salary_pdf_employee_number(colaborador) if document_type == "RV" else peno
    return _document_data(Path(clean_filename), expected_number)


def sign_colaborador_ac_document(user: Any, filename: str, signature_data: Any) -> dict[str, Any]:
    document = get_colaborador_recibo_document(user, filename)
    if not document:
        raise ValueError("Documento não encontrado.")
    if document["type"] not in SIGNABLE_DOCUMENT_TYPES:
        raise ValueError("Apenas os mapas de ajudas de custo e quilómetros podem ser assinados.")

    image = _decode_signature(signature_data)
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get("peno") or 0)
    phc_db = str(colaborador.get("phc_db") or "").strip()
    period = _period_key(document["year"], document["month"])
    dossiers = _load_ac_dossiers(colaborador) if document["type"] == "AC" else _load_kms_dossiers(colaborador)
    dossier = dossiers.get(period)
    if not peno or not phc_db or not dossier:
        raise ValueError("Não existe dossier para este mês.")
    if dossier.get("signed"):
        raise ValueError("Este mapa de ajudas de custo já se encontra assinado.")

    connection = None
    cursor = None
    signature_file: dict[str, Any] | None = None
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        where_employee = "AND BO.NOPAT = ?" if document["type"] == "AC" else ""
        parameters: list[Any] = [
            str(dossier["bostamp"]), int(dossier.get("ndos") or 0),
        ]
        if document["type"] == "AC":
            parameters.append(peno)
        parameters.extend([document["year"], document["month"]])
        cursor.execute(f"""
            SELECT TOP 1 BO.BOSTAMP
            FROM dbo.BO AS BO
            WHERE BO.BOSTAMP = ?
              AND BO.NDOS = ?
              {where_employee}
              AND YEAR(BO.DATAOBRA) = ?
              AND MONTH(BO.DATAOBRA) = ?
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.ANEXOS AS A WHERE A.RECSTAMP = BO.BOSTAMP
              )
        """, *parameters)
        row = cursor.fetchone()
        if not row:
            raise ValueError("O mapa já foi assinado ou deixou de estar disponível.")
        signature_file = _create_signed_claim_pdf(
            phc_db,
            peno,
            document["year"],
            document["month"],
            str(row.BOSTAMP or "").strip(),
            image,
            document["type"],
            document["filename"],
        )
        _insert_signature_attachment(
            cursor,
            str(row.BOSTAMP or "").strip(),
            signature_file,
            _user_login(user),
            int(dossier.get("ndos") or 0),
            document["type"],
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

    return {"ok": True, "message": f"{_document_title(document['type'])} assinado."}


def migrate_legacy_signature_attachments(phc_db: str) -> int:
    """Converts the early standalone PNG signatures into signed AC PDFs."""
    connection = None
    cursor = None
    migrated = 0
    try:
        connection = pyodbc.connect(_phc_conn_str(phc_db), timeout=12)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT ANEXOSSTAMP, RECSTAMP, FNAME, FEXT, FULLNAME, BDADOS
            FROM dbo.ANEXOS
            WHERE CONVERT(varchar(max), DESCRICAO) = ?
              AND ASSINATURA = 1
        """, SIGNATURE_DESCRIPTION)
        for row in cursor.fetchall():
            if str(row.FEXT or "").strip().lower() == "pdf":
                continue
            image = bytes(row.BDADOS or b"")
            if not image and str(row.FULLNAME or "").strip():
                try:
                    image = Path(str(row.FULLNAME).strip()).read_bytes()
                except OSError:
                    image = b""
            if not image.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            match = re.search(r"assinatura_ac_(\d+)_(20\d{4})", str(row.FNAME or ""), re.IGNORECASE)
            if not match:
                continue
            peno = int(match.group(1))
            period = match.group(2)
            signed_pdf = _create_signed_claim_pdf(
                phc_db, peno, int(period[:4]), int(period[4:]), str(row.RECSTAMP or ""), image, "AC",
            )
            cursor.execute("""
                UPDATE dbo.ANEXOS
                SET FULLNAME = ?, FNAME = ?, FEXT = 'pdf', FLEN = ?, BDADOS = ?
                WHERE ANEXOSSTAMP = ?
            """, signed_pdf["fullname"], signed_pdf["fname"], signed_pdf["flen"], pyodbc.Binary(b""), row.ANEXOSSTAMP)
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
