"""Read-only employee insurance map sourced from Guest_SPA_Tur.dbo.PE."""

from __future__ import annotations

import io
import json
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import text

from models import db


ACCESS_TABLE = "PE_SEGURO"
DEFAULT_SOURCE_DATABASE = "Guest_SPA_Tur"
MEAL_ALLOWANCE_DAYS = Decimal("22")
SORT_FIELDS = {
    "nome": "nome",
    "nacionalidade": "nacionalidade",
    "nif": "nif",
    "niss": "niss",
    "nascimento": "nascimento",
    "salario_base": "salario_base",
    "subsidio_refeicao": "subsidio_refeicao",
    "profissao": "profissao_descricao",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _source_database() -> str:
    value = _clean(os.environ.get("GUESTSPA_PE_DATABASE") or DEFAULT_SOURCE_DATABASE)
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise RuntimeError("A base de dados de pessoal configurada não é válida.")
    return value


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date) and value.year > 1900:
        return value
    return None


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def calculate_meal_allowance(daily_value: Any) -> Decimal:
    """Insurance map uses the current monthly convention of 22 paid days."""
    return (_money(daily_value) * MEAL_ALLOWANCE_DAYS).quantize(Decimal("0.01"))


def _employee_from_row(row: dict[str, Any]) -> dict[str, Any]:
    profession_code = _clean(row.get("CPROFISS"))
    profession_description = _clean(row.get("PROFISSAO_MAPEADA") or row.get("CCPROFISS"))
    employee = {
        "pestamp": _clean(row.get("PESTAMP")),
        "numero": int(row.get("NO") or 0),
        "nome": _clean(row.get("NOME")),
        "nacionalidade": _clean(row.get("NACNAT")),
        "nif": _clean(row.get("NCONT")),
        "niss": _clean(row.get("NBENEF")),
        "nascimento": _as_date(row.get("NASC")),
        "admissao": _as_date(row.get("DATAADM")),
        "salario_base": _money(row.get("EBASEMES")),
        "subsidio_refeicao": calculate_meal_allowance(row.get("EREFEICAO")),
        "profissao_codigo": profession_code,
        "profissao_descricao": profession_description,
    }
    employee["profissao"] = " — ".join(filter(None, (profession_code, profession_description)))
    employee["incompleto"] = any(not employee[field] for field in (
        "nome", "nacionalidade", "nif", "niss", "nascimento", "profissao_descricao"
    )) or employee["salario_base"] <= 0
    return employee


def active_employees(as_of: date | None = None) -> list[dict[str, Any]]:
    source = _source_database()
    reference_date = as_of or date.today()
    rows = db.session.execute(text(f"""
        SELECT
            RTRIM(P.PESTAMP) AS PESTAMP,
            P.NO, RTRIM(P.NOME) AS NOME, P.DATAADM,
            RTRIM(P.NCONT) AS NCONT, RTRIM(P.NBENEF) AS NBENEF, P.NASC,
            RTRIM(P.NACNAT) AS NACNAT, P.EBASEMES, P.EREFEICAO,
            RTRIM(P.CPROFISS) AS CPROFISS, RTRIM(P.CCPROFISS) AS CCPROFISS,
            RTRIM(ISNULL(M.DESCRICAO, '')) AS PROFISSAO_MAPEADA
        FROM [{source}].dbo.PE AS P
        LEFT JOIN dbo.GUESTSPA_EMPLOYEE_PROFESSION AS M
          ON LTRIM(RTRIM(ISNULL(M.CODIGO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
           = LTRIM(RTRIM(ISNULL(P.CPROFISS, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
         AND ISNULL(M.ATIVO, 1) = 1
        WHERE ISNULL(P.STATUS, 0) = 1
          AND CAST(P.DATAADM AS date) <= :as_of
          AND (CAST(P.DATAOUT AS date) <= '19000102' OR CAST(P.DATAOUT AS date) > :as_of)
        ORDER BY P.NOME
    """), {"as_of": reference_date}).mappings().all()
    return [_employee_from_row(dict(row)) for row in rows]


def _last_snapshot() -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    issue = db.session.execute(text("""
        SELECT TOP 1 ISSUESTAMP, UTILIZADOR, DTEMISSAO, TOTAL_ATUAIS, TOTAL_NOVOS, TOTAL_SAIDAS
        FROM dbo.GUESTSPA_EMPLOYEE_INSURANCE_ISSUE
        ORDER BY DTEMISSAO DESC, ISSUESTAMP DESC
    """)).mappings().first()
    if not issue:
        return None, []
    rows = db.session.execute(text("""
        SELECT PESTAMP, NUMERO, NOME, NACIONALIDADE, NIF, NISS, NASCIMENTO, ADMISSAO,
               SALARIO_BASE, SUBSIDIO_REFEICAO, PROFISSAO_CODIGO, PROFISSAO_DESCRICAO
        FROM dbo.GUESTSPA_EMPLOYEE_INSURANCE_SNAPSHOT
        WHERE ISSUESTAMP = :issue
        ORDER BY NOME
    """), {"issue": issue["ISSUESTAMP"]}).mappings().all()
    snapshot = []
    for raw in rows:
        item = {
            "pestamp": _clean(raw["PESTAMP"]), "numero": int(raw["NUMERO"] or 0),
            "nome": _clean(raw["NOME"]), "nacionalidade": _clean(raw["NACIONALIDADE"]),
            "nif": _clean(raw["NIF"]), "niss": _clean(raw["NISS"]),
            "nascimento": _as_date(raw["NASCIMENTO"]), "admissao": _as_date(raw["ADMISSAO"]),
            "salario_base": _money(raw["SALARIO_BASE"]),
            "subsidio_refeicao": _money(raw["SUBSIDIO_REFEICAO"]),
            "profissao_codigo": _clean(raw["PROFISSAO_CODIGO"]),
            "profissao_descricao": _clean(raw["PROFISSAO_DESCRICAO"]),
        }
        item["profissao"] = " — ".join(filter(None, (item["profissao_codigo"], item["profissao_descricao"])))
        item["incompleto"] = False
        snapshot.append(item)
    return dict(issue), snapshot


def classify_changes(
    current: list[dict[str, Any]], previous: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    previous_by_stamp = {row["pestamp"]: row for row in previous}
    current_stamps = {row["pestamp"] for row in current}
    has_baseline = bool(previous)
    for employee in current:
        employee["novo"] = has_baseline and employee["pestamp"] not in previous_by_stamp
    departures = [dict(row, saiu=True) for row in previous if row["pestamp"] not in current_stamps]
    return current, departures


def _matches(employee: dict[str, Any], filters: dict[str, Any]) -> bool:
    query = _clean(filters.get("q")).casefold()
    if query and query not in " ".join(_clean(employee.get(field)) for field in (
        "nome", "nacionalidade", "nif", "niss", "profissao_codigo", "profissao_descricao"
    )).casefold():
        return False
    nationality = _clean(filters.get("nacionalidade"))
    if nationality and employee.get("nacionalidade") != nationality:
        return False
    profession = _clean(filters.get("profissao"))
    return not profession or employee.get("profissao_codigo") == profession


def filter_and_sort(rows: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    filtered = [row for row in rows if _matches(row, filters)]
    sort_key = SORT_FIELDS.get(_clean(filters.get("ordenar")).lower(), "nome")
    reverse = _clean(filters.get("direcao")).lower() == "desc"
    return sorted(filtered, key=lambda row: (row.get(sort_key) is None, row.get(sort_key) or ""), reverse=reverse)


def employee_insurance_report(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    selected_filters = dict(filters or {})
    current_all = active_employees()
    last_issue, previous = _last_snapshot()
    current_all, departures_all = classify_changes(current_all, previous)
    current = filter_and_sort(current_all, selected_filters)
    departures = filter_and_sort(departures_all, selected_filters)
    nationalities = sorted({row["nacionalidade"] for row in current_all if row["nacionalidade"]})
    professions = sorted(
        ({"codigo": row["profissao_codigo"], "descricao": row["profissao_descricao"]} for row in current_all if row["profissao_codigo"]),
        key=lambda item: (item["descricao"], item["codigo"]),
    )
    # Deduplicate profession codes while retaining sorted descriptions.
    professions = list({item["codigo"]: item for item in professions}.values())
    return {
        "gerado_em": datetime.now(),
        "atuais": current,
        "saidas": departures,
        "atuais_todos": current_all,
        "saidas_todas": departures_all,
        "totais": {
            "atuais": len(current_all), "visiveis": len(current),
            "novos": sum(1 for row in current_all if row.get("novo")),
            "saidas": len(departures_all),
            "incompletos": sum(1 for row in current_all if row.get("incompleto")),
        },
        "ultima_emissao": last_issue,
        "filtros": selected_filters,
        "opcoes": {"nacionalidades": nationalities, "profissoes": professions},
    }


def profession_mappings() -> list[dict[str, Any]]:
    source = _source_database()
    rows = db.session.execute(text(f"""
        SELECT S.CODIGO, S.DESCRICAO_FONTE, RTRIM(ISNULL(M.DESCRICAO, '')) AS DESCRICAO_MAPEADA
        FROM (
            SELECT LTRIM(RTRIM(ISNULL(CPROFISS, ''))) AS CODIGO,
                   MAX(LTRIM(RTRIM(ISNULL(CCPROFISS, '')))) AS DESCRICAO_FONTE
            FROM [{source}].dbo.PE
            WHERE LTRIM(RTRIM(ISNULL(CPROFISS, ''))) <> ''
            GROUP BY LTRIM(RTRIM(ISNULL(CPROFISS, '')))
        ) AS S
        LEFT JOIN dbo.GUESTSPA_EMPLOYEE_PROFESSION AS M
          ON M.CODIGO COLLATE SQL_Latin1_General_CP1_CI_AI
           = S.CODIGO COLLATE SQL_Latin1_General_CP1_CI_AI
        ORDER BY S.CODIGO
    """)).mappings().all()
    return [{
        "codigo": _clean(row["CODIGO"]),
        "descricao_fonte": _clean(row["DESCRICAO_FONTE"]),
        "descricao": _clean(row["DESCRICAO_MAPEADA"] or row["DESCRICAO_FONTE"]),
        "personalizada": bool(_clean(row["DESCRICAO_MAPEADA"])),
    } for row in rows]


def save_profession_mapping(code: str, description: str, user_login: str) -> None:
    clean_code, clean_description = _clean(code)[:20], _clean(description)[:200]
    if not clean_code or not clean_description:
        raise ValueError("O código e a descrição da profissão são obrigatórios.")
    db.session.execute(text("""
        MERGE dbo.GUESTSPA_EMPLOYEE_PROFESSION AS target
        USING (SELECT :code AS CODIGO) AS source ON target.CODIGO = source.CODIGO
        WHEN MATCHED THEN UPDATE SET DESCRICAO=:description, ATIVO=1,
            DTALTERACAO_UTC=SYSUTCDATETIME(), UTILIZADOR=:user
        WHEN NOT MATCHED THEN INSERT
            (PROFSTAMP, CODIGO, DESCRICAO, ATIVO, DTALTERACAO_UTC, UTILIZADOR)
            VALUES (:stamp, :code, :description, 1, SYSUTCDATETIME(), :user);
    """), {
        "stamp": uuid.uuid4().hex.upper()[:25], "code": clean_code,
        "description": clean_description, "user": _clean(user_login)[:60],
    })
    db.session.commit()


def _display_value(employee: dict[str, Any], key: str) -> Any:
    value = employee.get(key)
    if isinstance(value, Decimal):
        return float(value)
    return value


def build_employee_insurance_workbook(report: dict[str, Any], rows: list[dict[str, Any]], departures: list[dict[str, Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Mapa seguradora"
    dark_fill = PatternFill("solid", fgColor="18324F")
    green_fill = PatternFill("solid", fgColor="D9EAD3")
    red_fill = PatternFill("solid", fgColor="F4CCCC")
    white_font = Font(color="FFFFFF", bold=True)
    headers = ["Nome", "Nacionalidade", "NIF", "NISS", "Data de nascimento", "Salário base", "Subsídio de refeição", "Profissão (CPP/IEFP)"]
    keys = ["nome", "nacionalidade", "nif", "niss", "nascimento", "salario_base", "subsidio_refeicao", "profissao"]

    sheet["A1"] = "Mapa de funcionários para seguradora"
    sheet["A1"].font = Font(size=16, bold=True, color="18324F")
    sheet["A2"] = "Empresa"
    sheet["B2"] = "GuestSpaTur"
    sheet["A3"] = "Data de emissão"
    sheet["B3"] = report["gerado_em"]
    sheet["B3"].number_format = "dd/mm/yyyy hh:mm"
    sheet["A4"] = "Âmbito"
    sheet["B4"] = "Filtro visível" if report.get("ambito") == "visivel" else "Todos os funcionários atuais"

    def append_table(title: str, items: list[dict[str, Any]], title_fill: PatternFill, start_row: int, departure: bool = False) -> int:
        sheet.cell(start_row, 1, title)
        sheet.cell(start_row, 1).font = Font(bold=True, color="FFFFFF")
        for column in range(1, len(headers) + 1):
            sheet.cell(start_row, column).fill = title_fill
        header_row = start_row + 1
        for column, header in enumerate(headers, 1):
            cell = sheet.cell(header_row, column, header)
            cell.fill, cell.font, cell.alignment = dark_fill, white_font, Alignment(horizontal="center")
        for item in items:
            values = [_display_value(item, key) for key in keys]
            sheet.append(values)
            row_number = sheet.max_row
            if departure:
                for cell in sheet[row_number]:
                    cell.fill = red_fill
            elif item.get("novo"):
                for cell in sheet[row_number]:
                    cell.fill = green_fill
            sheet.cell(row_number, 5).number_format = "dd/mm/yyyy"
            sheet.cell(row_number, 6).number_format = '#,##0.00 [$€-pt-PT]'
            sheet.cell(row_number, 7).number_format = '#,##0.00 [$€-pt-PT]'
        return sheet.max_row + 2

    next_row = append_table("FUNCIONÁRIOS ATUAIS", rows, dark_fill, 6)
    append_table("SAÍDAS DESDE A ÚLTIMA EMISSÃO", departures, red_fill, next_row, departure=True)
    sheet.freeze_panes = "A8"
    sheet.auto_filter.ref = f"A7:H{max(7, 7 + len(rows))}"
    widths = [38, 18, 15, 18, 19, 16, 22, 58]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    sheet.sheet_view.showGridLines = False
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def record_issue(user_login: str, report: dict[str, Any], filters: dict[str, Any], scope: str) -> str:
    issue_stamp = uuid.uuid4().hex.upper()[:25]
    current = report["atuais_todos"]
    db.session.execute(text("""
        INSERT INTO dbo.GUESTSPA_EMPLOYEE_INSURANCE_ISSUE
            (ISSUESTAMP, UTILIZADOR, DTEMISSAO, AMBITO, FILTROS,
             TOTAL_ATUAIS, TOTAL_NOVOS, TOTAL_SAIDAS)
        VALUES
            (:stamp, :user, SYSUTCDATETIME(), :scope, :filters,
             :current, :new, :departed)
    """), {
        "stamp": issue_stamp, "user": _clean(user_login)[:60], "scope": scope,
        "filters": json.dumps(filters, ensure_ascii=False)[:1000],
        "current": len(current), "new": report["totais"]["novos"],
        "departed": report["totais"]["saidas"],
    })
    insert_sql = text("""
        INSERT INTO dbo.GUESTSPA_EMPLOYEE_INSURANCE_SNAPSHOT
            (SNAPSHOTSTAMP, ISSUESTAMP, PESTAMP, NUMERO, NOME, NACIONALIDADE,
             NIF, NISS, NASCIMENTO, ADMISSAO, SALARIO_BASE, SUBSIDIO_REFEICAO,
             PROFISSAO_CODIGO, PROFISSAO_DESCRICAO)
        VALUES
            (:snapshot, :issue, :pestamp, :number, :name, :nationality,
             :nif, :niss, :birth, :admission, :salary, :meal, :profession_code,
             :profession_description)
    """)
    for employee in current:
        db.session.execute(insert_sql, {
            "snapshot": uuid.uuid4().hex.upper()[:25], "issue": issue_stamp,
            "pestamp": employee["pestamp"], "number": employee["numero"],
            "name": employee["nome"], "nationality": employee["nacionalidade"],
            "nif": employee["nif"], "niss": employee["niss"],
            "birth": employee["nascimento"], "admission": employee["admissao"],
            "salary": employee["salario_base"], "meal": employee["subsidio_refeicao"],
            "profession_code": employee["profissao_codigo"],
            "profession_description": employee["profissao_descricao"],
        })
    _insert_audit(user_login, "EXPORTAR", filters)
    db.session.commit()
    return issue_stamp


def _insert_audit(user_login: str, action: str, filters: dict[str, Any]) -> None:
    db.session.execute(text("""
        INSERT INTO dbo.GUESTSPA_EMPLOYEE_INSURANCE_AUDIT
            (AUDITSTAMP, UTILIZADOR, ACAO, FILTROS, DTCRIACAO_UTC)
        VALUES (:stamp, :user, :action, :filters, SYSUTCDATETIME())
    """), {
        "stamp": uuid.uuid4().hex.upper()[:25], "user": _clean(user_login)[:60],
        "action": _clean(action)[:20], "filters": json.dumps(filters, ensure_ascii=False)[:1000],
    })


def audit_consultation(user_login: str, filters: dict[str, Any]) -> None:
    _insert_audit(user_login, "CONSULTAR", filters)
    db.session.commit()
