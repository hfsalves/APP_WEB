#!/usr/bin/env python3
"""Repair the July 2026 BMSO import in HSOLS_FR without recreating documents.

This fixes the header fields and PF movement metadata to match PHC-native
supplier documents, then stores the original invoice PDF as an ANEXOS blob on
each pre-invoice. Bon Livraison Fourn. numbers are moved to BO.MAQUINA. It
never changes the BC -> BL -> PF BI.OBISTAMP chain.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pyodbc
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402
from modules.gr_subcontractor_measurements.service import (  # noqa: E402
    _new_stamp,
    _phc_columns,
    _phc_conn_str,
)


PHC_DB = "HSOLS_FR"
PHC_SERVER = "10.0.1.12"
SUPPLIER_NO = 31106
BL_NDOS = 130
PF_NDOS = 218
IMPORTED_BL_MIN = 8178
IMPORTED_DOC_MAX = 9000
INVOICE_PATTERN = re.compile(r"Facture\s+N[°o]?\s*(\d+)", re.IGNORECASE)


def _insert(cursor, table: str, values: dict[str, object]) -> None:
    valid = _phc_columns(cursor, table)
    fields = {key: value for key, value in values.items() if key.lower() in valid}
    cursor.execute(
        f"INSERT INTO dbo.{table} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
        tuple(fields.values()),
    )


def collect_invoice_pdfs(pdf_root: Path, output_dir: Path) -> dict[str, Path]:
    """Extract one PDF per invoice, preserving multi-page invoices."""
    pages: dict[str, list[tuple[Path, int]]] = {}
    for source in sorted(pdf_root.glob("*.pdf")):
        reader = PdfReader(str(source))
        for page_index, page in enumerate(reader.pages):
            match = INVOICE_PATTERN.search(page.extract_text() or "")
            if match:
                pages.setdefault(match.group(1), []).append((source, page_index))

    output_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}
    for invoice, source_pages in pages.items():
        target = output_dir / f"BMSO-Facture-{invoice}.pdf"
        writer = PdfWriter()
        readers: dict[Path, PdfReader] = {}
        for source, page_index in source_pages:
            reader = readers.setdefault(source, PdfReader(str(source)))
            writer.add_page(reader.pages[page_index])
        with target.open("wb") as handle:
            writer.write(handle)
        created[invoice] = target
    return created


def imported_preinvoices(cursor) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT B.BOSTAMP, LTRIM(RTRIM(B.FREF)) AS INVOICE, B.OBRANO, B.DATAOBRA
        FROM dbo.BO B
        WHERE B.NO = ? AND B.NDOS = ?
          AND B.OBRANO BETWEEN ? AND ?
          AND LTRIM(RTRIM(ISNULL(B.FREF, ''))) LIKE '900%'
        ORDER BY B.OBRANO
        """,
        (SUPPLIER_NO, PF_NDOS, IMPORTED_BL_MIN, IMPORTED_DOC_MAX),
    )
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def imported_delivery_notes(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT B.BOSTAMP
        FROM dbo.BO B
        LEFT JOIN dbo.BO3 B3 ON B3.BO3STAMP = B.BOSTAMP
        WHERE B.NO = ? AND B.NDOS = ?
          AND B.OBRANO BETWEEN ? AND ?
          AND (
              LTRIM(RTRIM(ISNULL(B.FREF, ''))) LIKE 'B4-%'
              OR LTRIM(RTRIM(ISNULL(B.MAQUINA, ''))) LIKE 'B4-%'
              OR LTRIM(RTRIM(ISNULL(B3.DOCUMENTNUMBERORI, ''))) LIKE 'B4-%'
          )
        """,
        (SUPPLIER_NO, BL_NDOS, IMPORTED_BL_MIN, IMPORTED_DOC_MAX),
    )
    return [str(row[0] or "").strip() for row in cursor.fetchall() if str(row[0] or "").strip()]


def repair_headers_and_lines(
    cursor, documents: list[dict[str, object]], bl_stamps: list[str]
) -> tuple[int, int, int, int]:
    """Repair only the PF documents selected before any values are cleared.

    PF and BL use different screen mappings. The existing PF repair remains
    unchanged. For BL the B4 number belongs in BO.MAQUINA, while
    BO3.DOCUMENTNUMBERORI feeds the field labelled Equipe and must stay empty.
    """
    stamps = [str(document["BOSTAMP"] or "").strip() for document in documents]
    stamps = [stamp for stamp in stamps if stamp]
    if not stamps and not bl_stamps:
        return 0, 0, 0, 0
    pf_headers = 0
    pf_lines = 0
    bl_headers = 0
    bl_lines = 0
    if stamps:
        placeholders = ", ".join("?" for _ in stamps)
        cursor.execute(
            f"""
            UPDATE B SET FREF = ''
            FROM dbo.BO B
            WHERE B.BOSTAMP IN ({placeholders})
            """,
            stamps,
        )
        pf_headers = cursor.rowcount
    if bl_stamps:
        placeholders_bl = ", ".join("?" for _ in bl_stamps)
        cursor.execute(
            f"""
            UPDATE B
               SET MAQUINA = CASE
                       WHEN LTRIM(RTRIM(ISNULL(B.MAQUINA, ''))) LIKE 'B4-%'
                           THEN LTRIM(RTRIM(B.MAQUINA))
                       WHEN LTRIM(RTRIM(ISNULL(B.FREF, ''))) LIKE 'B4-%'
                           THEN LTRIM(RTRIM(B.FREF))
                       ELSE LTRIM(RTRIM(ISNULL(B3.DOCUMENTNUMBERORI, '')))
                   END,
                   FREF = ''
            FROM dbo.BO B
            LEFT JOIN dbo.BO3 B3 ON B3.BO3STAMP = B.BOSTAMP
            WHERE B.BOSTAMP IN ({placeholders_bl})
            """,
            bl_stamps,
        )
        bl_headers = cursor.rowcount
        cursor.execute(
            f"""
            UPDATE B3 SET DOCUMENTNUMBERORI = ''
            FROM dbo.BO3 B3
            WHERE B3.BO3STAMP IN ({placeholders_bl})
            """,
            bl_stamps,
        )
        cursor.execute(
            f"""
            UPDATE I SET QTT2 = 0
            FROM dbo.BI I
            WHERE I.BOSTAMP IN ({placeholders_bl})
            """,
            bl_stamps,
        )
        bl_lines = cursor.rowcount
    if stamps:
        cursor.execute(
            f"""
            UPDATE B3 SET DOCUMENTNUMBERORI = ''
            FROM dbo.BO3 B3
            WHERE B3.BO3STAMP IN ({placeholders})
            """,
            stamps,
        )
        cursor.execute(
            f"""
            UPDATE I SET NDOC = 55, NMDOC = 'V/Facture', FNO = 0
            FROM dbo.BI I
            WHERE I.BOSTAMP IN ({placeholders})
            """,
            stamps,
        )
        pf_lines = cursor.rowcount
        cursor.execute(
            f"""
            UPDATE I2 SET ORIGBISTAMP = ''
            FROM dbo.BI2 I2
            INNER JOIN dbo.BI I ON I.BISTAMP = I2.BI2STAMP
            WHERE I.BOSTAMP IN ({placeholders})
            """,
            stamps,
        )
    return pf_headers, bl_headers, pf_lines, bl_lines


def ged_target(document: dict[str, object], ged_root: Path, invoice: str) -> tuple[Path, str]:
    document_date = document["DATAOBRA"]
    if not isinstance(document_date, datetime):
        raise ValueError(f"PF {document.get('OBRANO')} sem data valida.")
    month_names = ("JANV", "FEV", "MARS", "AVR", "MAI", "JUIN", "JUIL", "AOUT", "SEPT", "OCT", "NOV", "DEC")
    folder = f"{document_date.month} {month_names[document_date.month - 1]} {document_date:%y}"
    filename = f"fac-point P Bmso-{invoice}.pdf"
    target = ged_root / str(document_date.year) / folder / filename
    unc = "\\\\10.0.1.11\\ged\\hsols_fr\\facturation_fournisseurs\\" + "\\".join(
        (str(document_date.year), folder, filename)
    )
    return target, unc


def attach_pdfs(
    cursor, documents: list[dict[str, object]], invoice_pdfs: dict[str, Path], ged_root: Path
) -> tuple[int, list[str]]:
    now = datetime.now()
    hour = now.strftime("%H:%M:%S")
    attached = 0
    missing: list[str] = []
    for document in documents:
        invoice = str(document["INVOICE"] or "").strip()
        source = invoice_pdfs.get(invoice)
        if not source:
            missing.append(invoice)
            continue
        target, unc = ged_target(document, ged_root, invoice)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size != source.stat().st_size:
            shutil.copy2(source, target)

        cursor.execute(
            "DELETE FROM dbo.ANEXOS WHERE RECSTAMP = ? AND FNAME LIKE 'BMSO-Facture-%'",
            (document["BOSTAMP"],),
        )
        cursor.execute(
            """
            SELECT COUNT(*) FROM dbo.ANEXOS
            WHERE RECSTAMP = ?
              AND CONVERT(varchar(max), FULLNAME) = ?
            """,
            (document["BOSTAMP"], unc),
        )
        if int(cursor.fetchone()[0] or 0):
            continue
        _insert(cursor, "ANEXOS", {
            "anexosstamp": _new_stamp(),
            "oritable": "BO", "tabnm": "Dossiers Internos", "resumo": "PF",
            "grupo": "", "recstamp": document["BOSTAMP"], "uniqueid": "",
            "descricao": "", "bdados": pyodbc.Binary(b""),
            "fullname": unc, "fname": target.stem[:150], "fext": "pdf", "flen": 0,
            "tipo": 2, "passw": "", "origem": "Dossiers Internos", "keylook": "",
            "tpdos": PF_NDOS, "tpdoc": 0,
            "ausrinis": "APP", "ausrdata": now, "ausrhora": hour,
            "eusrinis": "APP", "eusrdata": now, "eusrhora": hour,
            "anexopaistamp": "", "assinatura": 0, "timestamp": 0,
            "anexoversaostamp": "", "versao": 0, "idustamp": "", "zipado": 0,
            "bdadosstamp": "", "invisivel": 0, "checkout": 0, "cuserno": 0,
            "cusername": "", "usnoopen": 0, "usnaopen": "", "isemail": 0,
            "emailid": "", "startwkf": 0, "wtwstamp": "", "privado": 0,
            "nivel": 0, "lsgq": 0, "fiscrel": 0, "original": 1,
            "ousrinis": "APP", "ousrdata": now, "ousrhora": hour,
            "usrinis": "APP", "usrdata": now, "usrhora": hour, "marcada": 0,
        })
        attached += 1
    return attached, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/bmso_invoice_pdfs"))
    parser.add_argument("--ged-root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    invoice_pdfs = collect_invoice_pdfs(args.pdf_root, args.output_dir)
    with app.app_context():
        with pyodbc.connect(_phc_conn_str(PHC_DB, PHC_SERVER), timeout=60) as connection:
            cursor = connection.cursor()
            documents = imported_preinvoices(cursor)
            bl_stamps = imported_delivery_notes(cursor)
            missing = sorted({str(row["INVOICE"]) for row in documents} - set(invoice_pdfs))
            print(f"PF importadas: {len(documents)}; PDFs extraidos: {len(invoice_pdfs)}; PDFs em falta: {len(missing)}")
            if missing:
                print("Faltam:", ", ".join(missing[:20]))
            if not args.execute:
                connection.rollback()
                print("Dry-run concluido. Nenhuma alteracao gravada.")
                return 0
            headers, bl_headers, lines, bl_lines = repair_headers_and_lines(cursor, documents, bl_stamps)
            attached, attach_missing = attach_pdfs(cursor, documents, invoice_pdfs, args.ged_root)
            connection.commit()
            print(
                "REPARACAO CONCLUIDA: "
                f"{headers} PF corrigidas, {bl_headers} BL corrigidos, "
                f"{lines} linhas PF corrigidas, {bl_lines} linhas BL corrigidas, "
                f"{attached} PDFs anexados."
            )
            if attach_missing:
                print("Sem PDF:", ", ".join(attach_missing[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
