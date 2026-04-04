import base64
import io
import os
import shutil
import subprocess
import tempfile
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote

from flask import current_app, render_template
from sqlalchemy import text
from services.miseimp_service import load_miseimp_map


NON_FISCAL_DOC_TYPES = {"PF", "OR"}

# Checklist art. 36 CIVA / Portaria 195/2020 no PDF:
# - Emitente: nome, morada, NIF
# - Adquirente: nome, morada, NIF
# - Identificação doc: tipo/série/nº e data
# - Linhas: descrição, quantidade, preço unitário, base, IVA %, IVA €, total
# - Totais: líquido, IVA e total documento
# - ATCUD visível
# - QR visível quando FT.CODIGOQR preenchido


def _to_decimal(value, default="0"):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return Decimal(default)
    if isinstance(value, bool):
        return Decimal("1" if value else "0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def fmt_money(value, places=2):
    quant = Decimal("1").scaleb(-int(places))
    val = _to_decimal(value, "0").quantize(quant, rounding=ROUND_HALF_UP)
    return format(val, "f")


def fmt_money_pt(value, places=2):
    return fmt_money(value, places).replace(".", ",")


def _safe_text(value) -> str:
    return str(value or "").strip()


def _table_has_columns(session, table_name: str, *column_names: str) -> bool:
    wanted = {str(name or "").strip().upper() for name in (column_names or []) if str(name or "").strip()}
    if not wanted:
        return True
    rows = session.execute(text("""
        SELECT UPPER(COLUMN_NAME) AS CN
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
    """), {"table_name": str(table_name or "").strip()}).mappings().all()
    existing = {str(row.get("CN") or "").upper() for row in rows}
    return wanted.issubset(existing)


def _locais_table_available(session) -> bool:
    row = session.execute(text("""
        SELECT TOP 1 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'LOCAIS'
    """)).first()
    return bool(row)


def _load_local_by_stamp(session, localstamp: str):
    localstamp = _safe_text(localstamp)
    if not localstamp or not _locais_table_available(session):
        return None
    row = session.execute(text("""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(LOCALSTAMP, ''))) AS LOCALSTAMP,
            LTRIM(RTRIM(ISNULL(DESIGNACAO, ''))) AS DESIGNACAO,
            LTRIM(RTRIM(ISNULL(MORADA, ''))) AS MORADA,
            LTRIM(RTRIM(ISNULL(MORADA2, ''))) AS MORADA2,
            LTRIM(RTRIM(ISNULL(CP, ''))) AS CP,
            LTRIM(RTRIM(ISNULL(LOCALIDADE, ''))) AS LOCALIDADE,
            LTRIM(RTRIM(ISNULL(PAIS, ''))) AS PAIS
        FROM dbo.LOCAIS
        WHERE LOCALSTAMP = :localstamp
    """), {"localstamp": localstamp}).mappings().first()
    return dict(row) if row else None


def _local_label(local_row: dict | None) -> str:
    if not local_row:
        return ""
    parts = [
        _safe_text(local_row.get("DESIGNACAO")),
        _safe_text(local_row.get("MORADA")),
        _safe_text(local_row.get("LOCALIDADE")),
    ]
    return " · ".join(part for part in parts if part)


def _fmt_datetime_display(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    raw = _safe_text(value)
    if not raw:
        return ""
    normalized = raw.replace(" ", "T")
    try:
        return datetime.fromisoformat(normalized[:19]).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def _fmt_date_display(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = _safe_text(value)
    if not raw:
        return ""
    normalized = raw.replace(" ", "T")
    if len(normalized) >= 10 and normalized[4:5] == "-" and normalized[7:8] == "-":
        return normalized[:10]
    return raw[:10]


def _doc_number(ft: dict) -> str:
    doc_type = get_ft_doc_type(ft)
    serie = _safe_text((ft or {}).get("SERIE"))
    fno = _safe_text((ft or {}).get("FNO"))
    if serie and fno:
        return f"{doc_type} {serie}/{fno}"
    if fno:
        return f"{doc_type} {fno}"
    return doc_type


def _hash_print4(ft: dict) -> str:
    raw = _safe_text((ft or {}).get("ASSINATURA") or (ft or {}).get("HASH"))
    if not raw:
        return ""
    return raw[:4]


def get_ft_doc_type(ft: dict) -> str:
    tiposaft = _safe_text((ft or {}).get("TIPOSAFT")).upper()
    if tiposaft:
        return tiposaft
    nmdoc = _safe_text((ft or {}).get("NMDOC")).upper()
    if "SIMPLIFICADA" in nmdoc or nmdoc.startswith("FS"):
        return "FS"
    if "PRO-FORMA" in nmdoc or "PRO FORMA" in nmdoc or nmdoc.startswith("PF"):
        return "PF"
    if "ORÃ‡AMENTO" in nmdoc or "ORCAMENTO" in nmdoc or nmdoc.startswith("OR"):
        return "OR"
    if "RECIBO" in nmdoc:
        return "FR"
    if "CRÃ‰DITO" in nmdoc or "CREDITO" in nmdoc or nmdoc.startswith("NC"):
        return "NC"
    return "FT"


def is_transport_doc(ft: dict) -> bool:
    return int(_to_decimal((ft or {}).get("IS_DOC_TRANSPORTE"), "0")) == 1


def is_ft_non_fiscal(ft: dict) -> bool:
    if is_transport_doc(ft):
        return False
    return get_ft_doc_type(ft) in NON_FISCAL_DOC_TYPES


def get_ft_display_title(ft: dict) -> str:
    doc_type = get_ft_doc_type(ft)
    if doc_type == "FS":
        return "Fatura Simplificada"
    if doc_type == "PF":
        return "Fatura PrÃ³-forma"
    if doc_type == "OR":
        return "OrÃ§amento"
    return _safe_text((ft or {}).get("NMDOC")) or "Fatura"


def get_ft_data(session, ftstamp: str):
    fts_transport_available = _table_has_columns(session, "FTS", "IS_DOC_TRANSPORTE")
    ft = session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.FT
        WHERE FTSTAMP=:s
    """), {"s": ftstamp}).mappings().first()
    if not ft:
        return None, [], None
    ft = dict(ft)
    try:
        fdata = ft.get("FDATA")
        ftano = int(getattr(fdata, "year")) if hasattr(fdata, "year") else int(_to_decimal(ft.get("FTANO"), "0"))
    except Exception:
        ftano = int(_to_decimal(ft.get("FTANO"), "0"))
    if ftano > 0 and _safe_text(ft.get("FESTAMP")) and int(_to_decimal(ft.get("NDOC"), "0")) > 0:
        srow = session.execute(text("""
            SELECT TOP 1
                ISNULL(TIPOSAFT, '') AS TIPOSAFT,
                ISNULL(NO_SAFT, 0) AS NO_SAFT
                """ + (", ISNULL(IS_DOC_TRANSPORTE, 0) AS IS_DOC_TRANSPORTE" if fts_transport_available else ", CAST(0 AS bit) AS IS_DOC_TRANSPORTE") + """
            FROM dbo.FTS
            WHERE
                FESTAMP=:festamp
                AND NDOC=:ndoc
                AND ISNULL(SERIE,'')=:serie
                AND ANO=:ano
        """), {
            "festamp": _safe_text(ft.get("FESTAMP")),
            "ndoc": int(_to_decimal(ft.get("NDOC"), "0")),
            "serie": _safe_text(ft.get("SERIE")),
            "ano": ftano,
        }).mappings().first()
        if srow:
            ft["TIPOSAFT"] = _safe_text(srow.get("TIPOSAFT"))
            ft["NO_SAFT"] = int(_to_decimal(srow.get("NO_SAFT"), "0"))
            if int(_to_decimal(ft.get("IS_DOC_TRANSPORTE"), "0")) != 1 and int(_to_decimal(srow.get("IS_DOC_TRANSPORTE"), "0")) == 1:
                ft["IS_DOC_TRANSPORTE"] = 1
    is_transport = is_transport_doc(ft)
    if is_transport:
        ft["LOCAL_CARGA_ID"] = _safe_text(ft.get("LOCAL_CARGA_ID"))
        ft["LOCAL_DESCARGA_ID"] = _safe_text(ft.get("LOCAL_DESCARGA_ID"))
        ft["MATRICULA"] = _safe_text(ft.get("MATRICULA"))
        ft["CODIGO_AT"] = _safe_text(ft.get("CODIGO_AT"))
        ft["DOC_TRANSPORTE_ESTADO"] = _safe_text(ft.get("DOC_TRANSPORTE_ESTADO")) or ("RASCUNHO" if int(_to_decimal(ft.get("ESTADO"), "0")) == 0 else "EMITIDO")
        local_carga = _load_local_by_stamp(session, ft.get("LOCAL_CARGA_ID") or "")
        local_descarga = _load_local_by_stamp(session, ft.get("LOCAL_DESCARGA_ID") or "")
        ft["LOCAL_CARGA_LABEL"] = _local_label(local_carga)
        ft["LOCAL_DESCARGA_LABEL"] = _local_label(local_descarga)
    miseimp_map = load_miseimp_map(session)
    fi_rows = session.execute(text("""
        SELECT *
        FROM dbo.FI
        WHERE FTSTAMP=:s
        ORDER BY ISNULL(LORDEM,0), FISTAMP
    """), {"s": ftstamp}).mappings().all()
    fi_rows = [dict(r) for r in fi_rows]
    for row in fi_rows:
        code = _safe_text(row.get("MISEIMP")).upper()
        row["MISEIMP"] = code
        row["MISEIMP_DESCRICAO"] = miseimp_map.get(code, "")
    fe = session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.FE
        WHERE FESTAMP=:f
    """), {"f": str(ft.get("FESTAMP") or "").strip()}).mappings().first()
    return ft, fi_rows, (dict(fe) if fe else {})


def discover_pdf_engines():
    chrome_paths = [
        os.environ.get("CHROME_PATH") or "",
        shutil.which("chrome") or "",
        shutil.which("google-chrome") or "",
        shutil.which("msedge") or "",
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        r"/usr/bin/google-chrome",
        r"/usr/bin/chromium",
    ]
    uniq = []
    seen = set()
    for p in chrome_paths:
        if not p:
            continue
        pp = str(p).strip()
        if not pp or pp in seen:
            continue
        seen.add(pp)
        uniq.append(pp)
    found = [p for p in uniq if os.path.isfile(p)]
    return {
        "CHROME_PATH_env": os.environ.get("CHROME_PATH", ""),
        "candidates": uniq,
        "found_browsers": found,
        "weasyprint_dll_dirs": os.environ.get("WEASYPRINT_DLL_DIRECTORIES", ""),
    }


def build_qr_base64(payload: str) -> str:
    data = (payload or "").strip()
    if not data:
        return ""
    try:
        import qrcode
    except Exception:
        return ""

    qr = qrcode.QRCode(version=None, box_size=5, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_logo_payload(rel_path: str = "static/images/guestspa.png") -> dict:
    fallback_path = "static/images/guestspa.png"
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    try:
        for candidate in [rel_path, fallback_path]:
            normalized = str(candidate or "").strip()
            if not normalized:
                continue
            abs_path = os.path.join(current_app.root_path, normalized.replace("/", os.sep))
            if not os.path.isfile(abs_path):
                continue
            ext = os.path.splitext(abs_path)[1].lower()
            with open(abs_path, "rb") as fh:
                return {
                    "b64": base64.b64encode(fh.read()).decode("ascii"),
                    "mime": mime_map.get(ext, "image/png"),
                }
    except Exception:
        return {"b64": "", "mime": "image/png"}
    return {"b64": "", "mime": "image/png"}


def render_ft_pdf_html(ft: dict, fi_rows: list[dict], fe: dict, qr_b64: str, at_certificado: str = "", modo_teste: bool = False, show_values: bool = True) -> str:
    is_non_fiscal = is_ft_non_fiscal(ft)
    is_transport = is_transport_doc(ft)
    display_title = get_ft_display_title(ft)
    if is_non_fiscal:
        qr_b64 = ""
        at_certificado = ""
    at_cert_raw = str(at_certificado or "").strip()
    at_cert_no_dec = at_cert_raw.split(".")[0] if "." in at_cert_raw else at_cert_raw
    dec2 = Decimal("0.01")
    dec6 = Decimal("0.000001")
    header_discount_pct = _to_decimal((ft or {}).get("DESCONTO"), "0").quantize(dec2, rounding=ROUND_HALF_UP)
    gross_before_discounts = Decimal("0.000000")
    discount_line_total = Decimal("0.000000")
    discount_header_total = Decimal("0.000000")
    net_total = Decimal("0.000000")
    vat_total = Decimal("0.00")
    buckets: dict[str, dict[str, Decimal]] = {}
    lines = []
    exempt_lines = []
    for row in fi_rows or []:
        qtt = _to_decimal(row.get("QTT"), "0").quantize(dec6, rounding=ROUND_HALF_UP)
        epv = _to_decimal(row.get("EPV"), "0").quantize(dec6, rounding=ROUND_HALF_UP)
        line_discount_pct = _to_decimal(row.get("DESCONTO"), "0").quantize(dec2, rounding=ROUND_HALF_UP)
        rate = _to_decimal(row.get("IVA"), "0").quantize(dec6, rounding=ROUND_HALF_UP)
        gross_line_total = (qtt * epv).quantize(dec6, rounding=ROUND_HALF_UP)
        desconto_linha_valor = (gross_line_total * line_discount_pct / Decimal("100")).quantize(dec6, rounding=ROUND_HALF_UP)
        total_apos_desc_linha = (gross_line_total - desconto_linha_valor).quantize(dec6, rounding=ROUND_HALF_UP)
        desconto_cabecalho_valor = (total_apos_desc_linha * header_discount_pct / Decimal("100")).quantize(dec6, rounding=ROUND_HALF_UP)
        total_liquido = (total_apos_desc_linha - desconto_cabecalho_valor).quantize(dec6, rounding=ROUND_HALF_UP)
        iva_val = (total_liquido * rate / Decimal("100")).quantize(dec2, rounding=ROUND_HALF_UP) if rate > 0 else Decimal("0.00")
        total_com_iva = (total_liquido + iva_val).quantize(dec2, rounding=ROUND_HALF_UP)

        gross_before_discounts += gross_line_total
        discount_line_total += desconto_linha_valor
        discount_header_total += desconto_cabecalho_valor
        net_total += total_liquido
        vat_total += iva_val

        rate_key = format(rate, "f")
        bucket = buckets.setdefault(rate_key, {"rate": rate, "base": Decimal("0.000000"), "vat": Decimal("0.00")})
        bucket["base"] += total_liquido
        bucket["vat"] += iva_val

        lines.append({
            **row,
            "_QTT": fmt_money_pt(qtt, 3),
            "_EPV": fmt_money_pt(epv, 2),
            "_DESC_PCT": fmt_money_pt(line_discount_pct, 2),
            "_BASE": fmt_money_pt(total_liquido, 2),
            "_IVA_TX": fmt_money_pt(rate, 2),
            "_IVA_VAL": fmt_money_pt(iva_val, 2),
            "_TOTAL": fmt_money_pt(total_apos_desc_linha, 2),
        })
        exempt_code = _safe_text(row.get("MISEIMP")).upper()
        exempt_desc = _safe_text(row.get("MISEIMP_DESCRICAO"))
        if rate == 0 and exempt_code:
            exempt_lines.append({
                "ref": _safe_text(row.get("REF")),
                "design": _safe_text(row.get("DESIGN")),
                "code": exempt_code,
                "description": exempt_desc or "Motivo de isen??o n?o definido",
            })
    iva_breakdown = []
    for bucket in sorted(buckets.values(), key=lambda item: item["rate"]):
        tx = bucket["rate"].quantize(dec2, rounding=ROUND_HALF_UP)
        base = bucket["base"].quantize(dec2, rounding=ROUND_HALF_UP)
        iva_val = bucket["vat"].quantize(dec2, rounding=ROUND_HALF_UP)
        if tx == 0 and base == 0 and iva_val == 0:
            continue
        iva_breakdown.append({
            "taxa": fmt_money_pt(tx, 2),
            "incidencia": fmt_money_pt(base, 2),
            "iva": fmt_money_pt(iva_val, 2),
        })
    discounts_total = (discount_line_total + discount_header_total).quantize(dec2, rounding=ROUND_HALF_UP)
    summary = {
        "header_discount_pct": fmt_money_pt(header_discount_pct, 2),
        "gross_before_discounts": fmt_money_pt(gross_before_discounts, 2),
        "discounts_total": fmt_money_pt(discounts_total, 2),
        "discount_line_total": fmt_money_pt(discount_line_total, 2),
        "discount_header_total": fmt_money_pt(discount_header_total, 2),
        "net_total": fmt_money_pt(net_total, 2),
        "vat_total": fmt_money_pt(vat_total, 2),
        "gross_total": fmt_money_pt((net_total + vat_total).quantize(dec2, rounding=ROUND_HALF_UP), 2),
    }
    transport_state = _safe_text((ft or {}).get("DOC_TRANSPORTE_ESTADO")).upper() or ("RASCUNHO" if int((ft or {}).get("ESTADO") or 0) == 0 else "EMITIDO")
    is_draft = transport_state == "RASCUNHO" if is_transport else int((ft or {}).get("BLOQUEADO") or 0) == 0
    status = transport_state if is_transport else ("RASCUNHO" if int((ft or {}).get("BLOQUEADO") or 0) == 0 else ("ANULADO" if int((ft or {}).get("ANULADA") or 0) == 1 else "EMITIDO"))
    return render_template(
        "faturacao/ft_pdf.html",
        ft=ft or {},
        fe=fe or {},
        lines=lines,
        summary=summary,
        iva_breakdown=iva_breakdown,
        exempt_lines=exempt_lines,
        qr_b64=qr_b64 or "",
        document_title=display_title,
        document_type=get_ft_doc_type(ft),
        document_number=_doc_number(ft),
        is_non_fiscal=is_non_fiscal,
        is_transport_doc=is_transport,
        transport_state=transport_state,
        logo=build_logo_payload(_safe_text((fe or {}).get("LOGOTIPO_PATH")) or "static/images/guestspa.png"),
        is_draft=is_draft,
        is_annulled=int((ft or {}).get("ANULADA") or 0) == 1,
        status=status,
        at_certificado=(at_certificado or "").strip(),
        at_cert_no_dec=at_cert_no_dec,
        hash4=("" if is_non_fiscal else _hash_print4(ft)),
        source_number=_safe_text((ft or {}).get("NUMDOC_ORIGEM")),
        source_date=_fmt_date_display((ft or {}).get("DATA_ORIGEM")),
        show_values=bool(show_values),
        transport_data_inicio=_fmt_datetime_display((ft or {}).get("DATA_HORA_INICIO_TRANSPORTE")),
        modo_teste=bool(modo_teste),
        fmt_money=fmt_money_pt,
    )


def generate_ft_pdf_bytes(html: str) -> bytes:
    engine_errors = []
    dll_dirs = os.environ.get("WEASYPRINT_DLL_DIRECTORIES", "").strip()
    if dll_dirs and hasattr(os, "add_dll_directory"):
        for part in dll_dirs.split(";"):
            p = part.strip()
            if p and os.path.isdir(p):
                try:
                    os.add_dll_directory(p)
                except Exception:
                    pass
    try:
        from weasyprint import HTML
        return HTML(string=html, base_url=current_app.root_path).write_pdf()
    except Exception as e:
        engine_errors.append(f"WeasyPrint: {e}")

    diag = discover_pdf_engines()
    browsers = [p for p in (diag.get("found_browsers") or []) if p]
    if browsers:
        for chrome in browsers:
            try:
                work_base = os.environ.get("PDF_TMP_DIR", "").strip() or os.path.join(current_app.root_path, ".pdf-tmp")
                os.makedirs(work_base, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=work_base, prefix="ftpdf_") as td:
                    html_path = os.path.join(td, "ft.html")
                    pdf_path = os.path.join(td, f"ft_{os.path.basename(chrome)}.pdf")
                    profile_base = os.environ.get("CHROME_USER_DATA_DIR", "").strip() or os.path.join(current_app.root_path, ".chrome-pdf-profile")
                    profile_dir = os.path.join(profile_base, f"p_{int(time.time() * 1000)}")
                    try:
                        os.makedirs(profile_dir, exist_ok=True)
                    except Exception:
                        profile_dir = ""
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html or "")
                    uri = "file:///" + html_path.replace("\\", "/")
                    data_uri = "data:text/html;charset=utf-8," + quote(html or "")
                    base_args = [
                        "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                        "--allow-file-access-from-files",
                        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
                        "--no-sandbox", "--disable-extensions", "--disable-sync",
                        "--disable-dev-shm-usage",
                    ]
                    if profile_dir:
                        base_args.append(f"--user-data-dir={profile_dir}")
                    cmd_variants = [
                        [chrome, "--headless=new", *base_args, f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", "--no-pdf-header-footer", uri],
                        [chrome, "--headless", *base_args, f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", "--no-pdf-header-footer", uri],
                        [chrome, "--headless=new", *base_args, f"--print-to-pdf={pdf_path}", uri],
                        [chrome, "--headless", *base_args, f"--print-to-pdf={pdf_path}", uri],
                        [chrome, "--headless=new", *base_args, f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", "--no-pdf-header-footer", data_uri],
                        [chrome, "--headless", *base_args, f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", "--no-pdf-header-footer", data_uri],
                    ]
                    for cmd in cmd_variants:
                        try:
                            run = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=18)
                            for _ in range(4):
                                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                                    with open(pdf_path, "rb") as pf:
                                        return pf.read()
                                time.sleep(0.25)
                            stderr_txt = (run.stderr or b"").decode("utf-8", errors="ignore").strip()
                            stdout_txt = (run.stdout or b"").decode("utf-8", errors="ignore").strip()
                            detail = (stderr_txt or stdout_txt or "sem saída de erro").strip()
                            engine_errors.append(f"Browser ({os.path.basename(chrome)}): sem PDF gerado. {detail[:220]}")
                        except Exception as e:
                            engine_errors.append(f"Browser ({os.path.basename(chrome)}): {e}")
            except Exception as e:
                engine_errors.append(f"Browser startup ({os.path.basename(chrome)}): {e}")
    else:
        engine_errors.append("Browser: CHROME_PATH/Chrome/Edge não encontrado no sistema.")

    raise RuntimeError("Nenhum gerador de PDF disponível. " + " | ".join(engine_errors[:3]))


def generate_ft_pdf_bytes_xhtml2pdf(html: str) -> bytes:
    from xhtml2pdf import pisa

    out = io.BytesIO()
    result = pisa.CreatePDF(src=html or "", dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("xhtml2pdf não conseguiu renderizar o HTML.")
    return out.getvalue()
