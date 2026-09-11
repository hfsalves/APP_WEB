"""Read-only tourist-tax reporting for GuestSpaTur reservations."""

from __future__ import annotations

import calendar
import io
import json
import os
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import text

from models import db


DEFAULT_MONTHLY_ACCOMMODATIONS = {
    "SUNNY", "BALCONY", "CASA DA PRAÇA", "CASA DO CRASTO", "GREEN HOUSE",
}
DEFAULT_NIGHT_LIMIT = 7
AMARANTE_NIGHT_LIMIT = 3


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _normalise(value: Any) -> str:
    return " ".join(_clean(value).upper().split())


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def tourist_tax_delivery_config() -> dict[str, str]:
    """Return the backend-owned delivery cadence by accommodation.

    Deployments may override the defaults with a JSON object in
    ``GUESTSPA_TOURIST_TAX_DELIVERY_CONFIG``.  The client never decides this.
    """
    config = {_normalise(name): "Mensal" for name in DEFAULT_MONTHLY_ACCOMMODATIONS}
    raw = os.environ.get("GUESTSPA_TOURIST_TAX_DELIVERY_CONFIG", "")
    if raw:
        try:
            supplied = json.loads(raw)
            if isinstance(supplied, dict):
                for name, cadence in supplied.items():
                    cadence = _clean(cadence).capitalize()
                    if cadence in {"Mensal", "Trimestral"}:
                        config[_normalise(name)] = cadence
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return config


def period_bounds(year: Any, period_type: Any, period_value: Any) -> tuple[date, date, str]:
    try:
        selected_year = int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ano inválido.") from exc
    if not 2000 <= selected_year <= 2100:
        raise ValueError("Ano inválido.")
    kind = _clean(period_type).lower()
    try:
        value = int(period_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Período inválido.") from exc
    if kind == "mensal":
        if not 1 <= value <= 12:
            raise ValueError("Mês inválido.")
        start = date(selected_year, value, 1)
        return start, date(selected_year, value, calendar.monthrange(selected_year, value)[1]), start.strftime("%Y-%m")
    if kind == "trimestral":
        if not 1 <= value <= 4:
            raise ValueError("Trimestre inválido.")
        start_month = ((value - 1) * 3) + 1
        return date(selected_year, start_month, 1), date(selected_year, start_month + 2, calendar.monthrange(selected_year, start_month + 2)[1]), f"{selected_year}-Q{value}"
    raise ValueError("Tipo de período inválido.")


def reservation_origin(reservation: Any) -> str | None:
    code = _clean(reservation).upper()
    if code.startswith("I"):
        return "Interna"
    if code.startswith("H"):
        return "Airbnb"
    if code[:1].isdigit():
        return "Booking"
    return None


def night_limit(accommodation: Any) -> int:
    return AMARANTE_NIGHT_LIMIT if _normalise(accommodation) == "CASA DO CRASTO" else DEFAULT_NIGHT_LIMIT


def build_tourist_tax_rows(rows: Iterable[dict[str, Any]], start: date, end: date) -> tuple[list[dict[str, Any]], list[str]]:
    """Apply the ticket's reporting rules to raw RS/AL records."""
    result: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw in rows:
        accommodation = _clean(raw.get("ALOJAMENTO"))
        mapped = bool(raw.get("ALSTAMP"))
        if not mapped:
            warnings.append(f"Alojamento sem correspondência em AL: {accommodation or '(vazio)'} ({_clean(raw.get('RESERVA')) or 'sem reserva'}).")
            continue
        origin = reservation_origin(raw.get("RESERVA"))
        if origin == "Interna":
            continue
        if origin is None:
            warnings.append(f"Reserva excluída por prefixo não reconhecido: {_clean(raw.get('RESERVA')) or '(vazia)'}.")
            continue
        checkin, checkout = _as_date(raw.get("DATAIN")), _as_date(raw.get("DATAOUT"))
        try:
            official_nights = int(raw.get("NOITES") or 0)
        except (TypeError, ValueError):
            official_nights = 0
        if not checkin or not checkout or checkout <= checkin or official_nights <= 0:
            warnings.append(f"Reserva excluída por datas/NOITES inválidas: {_clean(raw.get('RESERVA')) or '(sem código)'}.")
            continue
        real_nights = (checkout - checkin).days
        if real_nights != official_nights:
            warnings.append(f"NOITES incompatível em {_clean(raw.get('RESERVA'))}: oficial {official_nights}, datas {real_nights}; usado o valor oficial.")
        official_checkout = min(checkout, checkin + timedelta(days=official_nights))
        allocated_start, allocated_end = max(checkin, start), min(official_checkout, end + timedelta(days=1))
        nights_in_period = max(0, (allocated_end - allocated_start).days)
        if not nights_in_period:
            continue
        adults = max(0, int(raw.get("ADULTOS") or 0))
        children = max(0, int(raw.get("CRIANCAS") or 0))
        guests = adults + children
        limit = night_limit(accommodation)
        first_night_index = (allocated_start - checkin).days
        nights_above_limit = sum(1 for index in range(first_night_index, first_night_index + nights_in_period) if index >= limit)
        result.append({
            "reserva": _clean(raw.get("RESERVA")), "origem": origin, "alojamento": accommodation,
            "checkin": checkin, "checkout": checkout, "noites_oficiais": official_nights,
            "noites_periodo": nights_in_period, "adultos": adults, "criancas": children,
            "hospedes_total": guests, "dormidas_totais": guests * nights_in_period,
            "dormidas_acima_limite": guests * nights_above_limit, "limite_noites": limit,
        })
    return sorted(result, key=lambda row: (row["alojamento"], row["checkin"], row["reserva"])), warnings


def _summary(rows: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"reservas": 0, "dormidas_totais": 0, "dormidas_acima_limite": 0, "adultos": 0, "criancas": 0, "noites_periodo": 0})
    seen: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        bucket = grouped[row[key]]
        reservation = row["reserva"]
        if reservation not in seen[row[key]]:
            bucket["reservas"] += 1
            bucket["adultos"] += row["adultos"]
            bucket["criancas"] += row["criancas"]
            seen[row[key]].add(reservation)
        for field in ("dormidas_totais", "dormidas_acima_limite", "noites_periodo"):
            bucket[field] += row[field]
    return [{key: name, **values} for name, values in sorted(grouped.items())]


def tourist_tax_report(year: Any, period_type: Any, period_value: Any, feid: int = 2) -> dict[str, Any]:
    start, end, label = period_bounds(year, period_type, period_value)
    raw_rows = db.session.execute(text("""
        SELECT RS.RESERVA, RS.ALOJAMENTO, CAST(RS.DATAIN AS date) AS DATAIN,
               CAST(RS.DATAOUT AS date) AS DATAOUT, RS.NOITES, RS.ADULTOS, RS.CRIANCAS,
               AL.ALSTAMP
        FROM dbo.RS RS
        LEFT JOIN dbo.AL AL
          ON LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
           = LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
         AND ISNULL(AL.FEID, 0) = :feid
        WHERE ISNULL(RS.FEID, 0) = :feid
          AND ISNULL(RS.CANCELADA, 0) = 0
          AND CAST(RS.DATAIN AS date) < DATEADD(day, 1, :end_date)
          AND CAST(RS.DATAOUT AS date) > :start_date
    """), {"feid": int(feid), "start_date": start, "end_date": end}).mappings().all()
    rows, warnings = build_tourist_tax_rows([dict(row) for row in raw_rows], start, end)
    delivery = tourist_tax_delivery_config()
    return {
        "periodo": {"inicio": start.isoformat(), "fim": end.isoformat(), "rotulo": label, "tipo": _clean(period_type).capitalize()},
        "linhas": rows, "resumo_alojamento": _summary(rows, "alojamento"), "resumo_origem": _summary(rows, "origem"),
        "avisos": warnings, "entrega": [{"alojamento": name, "tipo": delivery.get(_normalise(name), "Trimestral")} for name in sorted({row["alojamento"] for row in rows})],
    }


def build_tourist_tax_workbook(report: dict[str, Any]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    header_fill, header_font = PatternFill("solid", fgColor="1F4E78"), Font(color="FFFFFF", bold=True)
    used_sheet_names: set[str] = set()

    def add_sheet(name: str, headers: list[str], data: list[list[Any]]) -> None:
        base_name = _clean(name)[:31] or "Mapa"
        sheet_name, suffix = base_name, 2
        while sheet_name.lower() in used_sheet_names:
            marker = f" ({suffix})"
            sheet_name = f"{base_name[:31 - len(marker)]}{marker}"
            suffix += 1
        used_sheet_names.add(sheet_name.lower())
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)
        for cell in sheet[1]: cell.fill, cell.font = header_fill, header_font
        for item in data: sheet.append(item)
        sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(36, max(12, max(len(str(cell.value or "")) for cell in column) + 2))

    rows = report["linhas"]
    detail_headers = ["N.º reserva", "Origem", "Check-in", "Check-out", "Noites no período", "Hóspedes adultos", "Hóspedes crianças", "Hóspedes total", "Dormidas totais", "Dormidas acima limite", "Limite noites"]
    def detail(row): return [row["reserva"], row["origem"], row["checkin"], row["checkout"], row["noites_periodo"], row["adultos"], row["criancas"], row["hospedes_total"], row["dormidas_totais"], row["dormidas_acima_limite"], row["limite_noites"]]
    summary_rows = [[row["alojamento"], row["reservas"], row["dormidas_totais"], row["dormidas_acima_limite"], row["adultos"], row["criancas"], row["noites_periodo"]] for row in report["resumo_alojamento"]]
    if summary_rows: summary_rows.append(["Total", *[sum(row[index] for row in summary_rows) for index in range(1, 7)]])
    add_sheet("Resumo", ["Alojamento", "Reservas", "Dormidas totais", "Dormidas acima limite", "Hóspedes adultos", "Hóspedes crianças", "Noites no período"], summary_rows)
    for accommodation in sorted({row["alojamento"] for row in rows}):
        accommodation_rows = [detail(row) for row in rows if row["alojamento"] == accommodation]
        if accommodation_rows: accommodation_rows.append(["Total", "", "", "", sum(row[4] for row in accommodation_rows), sum(row[5] for row in accommodation_rows), sum(row[6] for row in accommodation_rows), sum(row[7] for row in accommodation_rows), sum(row[8] for row in accommodation_rows), sum(row[9] for row in accommodation_rows), ""])
        add_sheet(accommodation, detail_headers, accommodation_rows)
    detail_rows = [detail(row) for row in rows]
    if detail_rows: detail_rows.append(["Total", "", "", "", sum(row[4] for row in detail_rows), sum(row[5] for row in detail_rows), sum(row[6] for row in detail_rows), sum(row[7] for row in detail_rows), sum(row[8] for row in detail_rows), sum(row[9] for row in detail_rows), ""])
    add_sheet("Detalhe", detail_headers, detail_rows)
    origin_rows = [[row["origem"], row["reservas"], row["dormidas_totais"], row["dormidas_acima_limite"], row["adultos"], row["criancas"], row["noites_periodo"]] for row in report["resumo_origem"]]
    if origin_rows: origin_rows.append(["Total", *[sum(row[index] for row in origin_rows) for index in range(1, 7)]])
    add_sheet("Resumo por origem", ["Origem", "Reservas", "Dormidas totais", "Dormidas acima limite", "Hóspedes adultos", "Hóspedes crianças", "Noites no período"], origin_rows)
    add_sheet("Notas e metodologia", ["Nota"], [[f"Período: {report['periodo']['rotulo']}"], ["Origem: H = Airbnb; prefixo numérico = Booking; I e formatos desconhecidos são excluídos."], ["As noites usam a interseção do período com NOITES oficial; o limite é incremental desde o check-in."], *[[warning] for warning in report["avisos"]]])
    output = io.BytesIO(); workbook.save(output); return output.getvalue()


def audit_tourist_tax_access(user_login: str, report: dict[str, Any], exported: bool = False) -> None:
    """Record only the user, period and action—never credentials or reservation data."""
    db.session.execute(text("""
        IF OBJECT_ID('dbo.GUESTSPA_TOURIST_TAX_AUDIT', 'U') IS NULL
        CREATE TABLE dbo.GUESTSPA_TOURIST_TAX_AUDIT (
            AUDITSTAMP varchar(25) NOT NULL PRIMARY KEY, UTILIZADOR varchar(60) NOT NULL DEFAULT '',
            PERIODO varchar(20) NOT NULL DEFAULT '', ACAO varchar(20) NOT NULL DEFAULT '', DTCRIACAO_UTC datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
        )
    """))
    db.session.execute(text("INSERT INTO dbo.GUESTSPA_TOURIST_TAX_AUDIT (AUDITSTAMP, UTILIZADOR, PERIODO, ACAO) VALUES (:stamp, :user, :period, :action)"), {"stamp": uuid.uuid4().hex.upper()[:25], "user": _clean(user_login)[:60], "period": report["periodo"]["rotulo"], "action": "EXPORTAR" if exported else "CONSULTAR"})
    db.session.commit()
