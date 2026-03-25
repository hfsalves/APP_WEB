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


def is_ft_non_fiscal(ft: dict) -> bool:
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
    fi_rows = session.execute(text("""
        SELECT *
        FROM dbo.FI
        WHERE FTSTAMP=:s
        ORDER BY ISNULL(LORDEM,0), FISTAMP
    """), {"s": ftstamp}).mappings().all()
    fe = session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.FE
        WHERE FESTAMP=:f
    """), {"f": str(ft.get("FESTAMP") or "").strip()}).mappings().first()
    return ft, [dict(r) for r in fi_rows], (dict(fe) if fe else {})


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


def build_logo_base64(rel_path: str = "static/images/guestspa.png") -> str:
    try:
        abs_path = os.path.join(current_app.root_path, rel_path.replace("/", os.sep))
        if not os.path.isfile(abs_path):
            return ""
        with open(abs_path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    except Exception:
        return ""


def render_ft_pdf_html(ft: dict, fi_rows: list[dict], fe: dict, qr_b64: str, at_certificado: str = "", modo_teste: bool = False) -> str:
    is_non_fiscal = is_ft_non_fiscal(ft)
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
    status = "RASCUNHO" if int((ft or {}).get("BLOQUEADO") or 0) == 0 else ("ANULADO" if int((ft or {}).get("ANULADA") or 0) == 1 else "EMITIDO")
    return render_template(
        "faturacao/ft_pdf.html",
        ft=ft or {},
        fe=fe or {},
        lines=lines,
        summary=summary,
        iva_breakdown=iva_breakdown,
        qr_b64=qr_b64 or "",
        document_title=display_title,
        document_type=get_ft_doc_type(ft),
        document_number=_doc_number(ft),
        is_non_fiscal=is_non_fiscal,
        logo_b64=build_logo_base64(),
        is_draft=int((ft or {}).get("BLOQUEADO") or 0) == 0,
        is_annulled=int((ft or {}).get("ANULADA") or 0) == 1,
        status=status,
        at_certificado=(at_certificado or "").strip(),
        at_cert_no_dec=at_cert_no_dec,
        hash4=("" if is_non_fiscal else _hash_print4(ft)),
        source_number=_safe_text((ft or {}).get("NUMDOC_ORIGEM")),
        source_date=_fmt_date_display((ft or {}).get("DATA_ORIGEM")),
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
