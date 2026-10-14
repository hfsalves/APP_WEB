from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import g, has_request_context

from modules.gr_subcontractor_measurements.service import list_companies_for_user
from . import sources
from .config import CATEGORIES, SourceUnavailable, TravelMapsError, payroll_rule, period_bounds


def clean(value):
    return str(value if value is not None else "").strip()


def original(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def decimal(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError
        return result
    except (InvalidOperation, TypeError, ValueError):
        raise SourceUnavailable("Foi encontrada uma quantidade ou valor PHC inválido. Os totais não foram calculados.") from None


def company_for_user(feid, user):
    try:
        selected = int(str(feid))
    except (TypeError, ValueError):
        raise TravelMapsError("Selecione uma empresa válida.") from None
    # A reconstruction can inspect many maps and evidence companies. Cache only
    # for this HTTP request, never across sessions or permission changes.
    identity = (str(getattr(user, 'USSTAMP', '')), str(getattr(user, 'LOGIN', '')),
                bool(getattr(user, 'ADMIN', False)), bool(getattr(user, 'DEV', False)))
    cached = getattr(g, '_travel_companies', None) if has_request_context() else None
    if cached is None or cached[0] != identity:
        companies = list_companies_for_user(user)
        if has_request_context():
            g._travel_companies = (identity, companies)
    else:
        companies = cached[1]
    for company in companies:
        if company["feid"] == selected:
            return company
    error = TravelMapsError("Sem acesso à empresa selecionada.")
    error.status_code = 403
    raise error


def public_company(company):
    return {key: company[key] for key in ("feid", "name", "phc_db")}


def empty_metrics(rule):
    return {category: {
        "quantity": Decimal(0) if rule and rule["codes"][category] is not None else None,
        "amount": Decimal(0) if rule and rule["codes"][category] is not None else None,
    } for category in CATEGORIES}


def serialize_metrics(metrics):
    return {category: {key: str(value) if value is not None else None for key, value in values.items()}
            for category, values in metrics.items()}


def aggregate_payroll(rows, company, start, end, rule):
    code_categories = {code: category for category in CATEGORIES for code in (rule["codes"][category] or [])} if rule else {}
    employees, seen_lines = {}, set()
    totals = empty_metrics(rule)
    receipts = set()
    for row in rows:
        number = clean(row["NO"])
        pestamp = clean(row.get("PESTAMP"))
        key = pestamp or f"unresolved:{number}"
        if key not in employees:
            employees[key] = {
                "key": f"{company['feid']}:{company['phc_db']}:{key}",
                "pestamp": pestamp or None, "number": number, "name": clean(row["NOME"]),
                "identity_resolved": bool(pestamp), "phc": empty_metrics(rule),
                "map": {category: None for category in CATEGORIES},
                "difference": {category: None for category in CATEGORIES},
                "reconciliation": {category: None for category in CATEGORIES},
                "state": "SEM_MAPA", "receipts": {}, "lines": [], "warnings": [],
            }
        employee = employees[key]
        if not pestamp and "Identidade PHC por resolver." not in employee["warnings"]:
            employee["warnings"].append("Identidade PHC por resolver.")
        receipt = clean(row["PRSTAMP"])
        receipts.add(receipt)
        employee["receipts"][receipt] = {key: original(row.get(key)) for key in ("PRSTAMP", "RECIBO", "DATA", "ANO", "MESREF", "STATUS")}
        line_stamp = clean(row.get("PRRESTAMP"))
        if not line_stamp:
            continue
        if line_stamp in seen_lines:
            raise SourceUnavailable("Foram encontradas linhas PHC duplicadas. Os totais não foram apresentados.")
        seen_lines.add(line_stamp)
        category = code_categories.get(int(row["CR"]))
        if category is None:
            raise SourceUnavailable("Foi encontrada uma rubrica fora do mapeamento configurado.")
        quantity, amount, rate = (decimal(row.get(field)) for field in ("RQTT", "ERE", "ERVU"))
        employee["phc"][category]["quantity"] += quantity
        employee["phc"][category]["amount"] += amount
        totals[category]["quantity"] += quantity
        totals[category]["amount"] += amount
        warnings = []
        reference = row.get("DTREF")
        reference_day = reference.date() if isinstance(reference, datetime) else reference
        if isinstance(reference_day, date) and reference_day > date(1900, 1, 1) and not start <= reference_day < end:
            warnings.append("Referência salarial fora do mês selecionado.")
        if quantity < 0 or amount < 0 or clean(row.get("ORIPRRESTAMP")):
            warnings.append("Regularização ou linha com origem: conferir o documento PHC.")
        if abs(amount - quantity * rate) > Decimal("0.01"):
            warnings.append("O valor PHC difere de quantidade × valor unitário; o valor original foi mantido.")
        employee["lines"].append({
            "category": category, "warnings": warnings,
            "source": {"database": company["phc_db"], "table": "PRRE", "stamp": line_stamp},
            "original": {key: original(row.get(key)) for key in (
                "PRSTAMP", "PRRESTAMP", "RECIBO", "DATA", "CR", "REM", "RQTT", "ERVU", "ERE", "DTREF", "ORIPRRESTAMP",
            )},
        })
        employee["warnings"] = list(dict.fromkeys([*employee["warnings"], *warnings]))
    for employee in employees.values():
        employee["phc"] = serialize_metrics(employee["phc"])
        employee["receipts"] = list(employee["receipts"].values())
    return {
        "rows": list(employees.values()), "totals": serialize_metrics(totals),
        "employee_count": len(employees), "receipt_count": len(receipts), "line_count": len(seen_lines),
    }


def monthly_panel(feid, year, month, user):
    start, end = period_bounds(year, month)
    company = company_for_user(feid, user)
    rule = payroll_rule(company["phc_db"], start, end)
    codes = sorted({code for category in CATEGORIES for code in (rule["codes"][category] or [])}) if rule else []
    result = aggregate_payroll(sources.payroll_rows(company, start, end, codes), company, start, end, rule)
    return {
        **result, "company": public_company(company), "year": start.year, "month": start.month,
        "read_at": datetime.now(timezone.utc).isoformat(), "currency": "EUR" if rule else None,
        "mapping": rule, "source_state": "AVAILABLE" if rule else "UNCONFIGURED",
        "period_basis": "PR.DATA",
        "warnings": [
            "Período pela data do recibo. São incluídos todos os recibos e mantidos os sinais das regularizações.",
            "Os estados dos recibos são apresentados para conferência; esta consulta não certifica o fecho salarial.",
            "— significa não configurado ou mapa ainda inexistente; não representa zero.",
        ],
    }


def monthly_measurements(feid, year, month, user):
    start, end = period_bounds(year, month)
    company = company_for_user(feid, user)
    records, series = sources.measurement_rows(company, start, end)
    works, result = set(), []
    for row in records:
        positive = int(row.get("POSITIVE_LINES") or 0) > 0
        work = clean(row.get("PROCESSO"))
        if positive and work:
            works.add(work)
        result.append({
            "bostamp": clean(row["BOSTAMP"]), "number": clean(row["OBRANO"]),
            "series": clean(row["NMDOS"]), "ndos": int(row["NDOS"]),
            "date": original(row["DATAOBRA"]), "work": work or None,
            "cost_center": clean(row.get("CCUSTO")), "description": clean(row.get("DESCRICAO")),
            "client": clean(row["CLIENT_NAME"]), "client_number": clean(row["CLIENT_NO"]),
            "address": clean(row.get("MORADA")), "locality": clean(row.get("LOCALIDADE")),
            "country": None, "work_matches": int(row.get("WORK_MATCHES") or 0),
            "has_positive_measurement": positive,
            "employee_assignment": None,
            "source": {"database": company["phc_db"], "table": "BO", "stamp": clean(row["BOSTAMP"])},
        })
    return {
        "company": public_company(company), "rows": result, "work_count": len(works),
        "series": [{"ndos": int(row["NDOS"]), "name": clean(row["NMDOS"])} for row in series],
        "source_state": "AVAILABLE" if series else "UNCONFIGURED",
        "read_at": datetime.now(timezone.utc).isoformat(),
        "warnings": [
            "Autos não anulados, selecionados pela data do documento. O período efetivo de produção necessita de confirmação.",
            "A medição positiva identifica obras candidatas; não comprova presença ou deslocação de um trabalhador.",
        ],
    }
