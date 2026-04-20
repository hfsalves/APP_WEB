from datetime import date, datetime, timedelta
from typing import Iterable

from uuid import uuid4
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape as xml_escape
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Flask, g, jsonify, redirect, render_template, request, send_file, session, url_for

from database import database
from intersol_monthly import (
    ROLE_AIDE,
    ROLE_CHEF,
    ROLE_POLISSEUR,
    ROLE_SCIEUR,
    Task as IntersolTask,
    compute_monthly_sheet,
)
from i18n import DEFAULT_LANGUAGE, available_languages, get_translations, iter_languages, resolve_language
from markets import get_market, list_markets, market_filters

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"

LANGUAGE_CODES = tuple(iter_languages())

PLANNING_GROUP_ORDER = (
    "PORTUGAL",
    "FRANCE",
    "INTERSOL",
    "MAROC",
    "SOUS-TRAITANTS",
    "POMPES",
    "CENTRALS",
    "ATELIER",
    "MAINTENANCE",
)

TEAM_END_SENTINEL = date(1900, 1, 1)

INTERSOL_TEAM_CODES = {"IS ALSACE 01", "IS LORRAINE 01", "IS CHAMPAGNE 01"}
VALID_INTERSOL_ROLES = {ROLE_CHEF, ROLE_POLISSEUR, ROLE_AIDE, ROLE_SCIEUR}
INTERSOL_ROLE_LABELS = {
    ROLE_CHEF: "Chefe de equipa",
    ROLE_POLISSEUR: "Polisseur",
    ROLE_AIDE: "Aide-polisseur",
    ROLE_SCIEUR: "Scieur",
}
INTERSOL_PREPARATION_LITEMS = {"999"}
INTERSOL_REPARATION_LITEMS = {"997"}
INTERSOL_INTEMPERIE_LITEMS = {"980", "990"}
INTERSOL_LAVAGE_LITEMS = {"994"}
INTERSOL_OTHER_LITEMS = {"995"}
INTERSOL_DETAIL_PREPAID = Decimal("150.00")

MARKET_ACCESS_FIELDS = {
    "DE": "u_de",
    "ES": "u_es",
    "FR": "u_fr",
    "IA": "u_ia",
    "IC": "u_ic",
    "IL": "u_il",
    "MA": "u_ma",
    "PT": "u_pt",
}

# Team group access rules by market permissions
TEAM_GROUP_RULES = {
    "MAROC_ONLY": {"include": {"MAROC", "SOUS-TRAITANTS"}, "exclude": set()},
    "EUROPE_EXCEPT_MAROC": {"include": set(), "exclude": {"MAROC"}},
    "INTERSOL_SOUS_TRAITANTS": {"include": {"INTERSOL", "SOUS-TRAITANTS"}, "exclude": set()},
}

MARKET_PLANNING_GROUPS = {
    "PT": {"PORTUGAL"},
    "FR": {"FRANCE"},
    "IA": {"INTERSOL"},
    "IC": {"INTERSOL"},
    "IL": {"INTERSOL"},
    "MA": {"MAROC"},
}

GLOBAL_PLANNING_GROUPS = {"SOUS-TRAITANTS", "POMPES", "CENTRALS", "ATELIER", "MAINTENANCE"}


def _normalise_planning_group(raw_label: str) -> tuple[str, str]:
    """Collapse planning bucket names into canonical keys/labels."""
    upper_label = raw_label.upper()
    if upper_label.startswith("INTERSOL") or upper_label in {"ALSACE", "LORRAINE", "CHAMPAGNE"}:
        return "INTERSOL", "INTERSOL"
    normalised_key = upper_label or "OUTROS"
    return normalised_key, raw_label or normalised_key


def _normalise_membership_end(value: date | None) -> date | None:
    if value == TEAM_END_SENTINEL:
        return None
    return value


def _segments_overlap(start_a: date, end_a: date | None, start_b: date, end_b: date | None) -> bool:
    end_a = end_a or date.max
    end_b = end_b or date.max
    return start_a <= end_b and start_b <= end_a


def _xlsx_col_name(index: int) -> str:
    if index < 1:
        return "A"
    letters: list[str] = []
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _xlsx_safe_sheet_name(name: str) -> str:
    cleaned = "".join(ch for ch in (name or "") if ch not in '[]:*?/\\')
    cleaned = "".join(ch for ch in cleaned if _xml_char_allowed(ch))
    cleaned = cleaned.strip() or "Sheet1"
    return cleaned[:31]


def _xml_char_allowed(ch: str) -> bool:
    code = ord(ch)
    return code in (0x9, 0xA, 0xD) or (0x20 <= code <= 0xD7FF) or (0xE000 <= code <= 0xFFFD) or (0x10000 <= code <= 0x10FFFF)


def _xml_clean_text(value: str) -> str:
    return "".join(ch for ch in value if _xml_char_allowed(ch))


def _xlsx_inline_cell(cell_ref: str, value: str, style_id: int | None = None) -> str:
    clean_value = _xml_clean_text(value)
    text = xml_escape(clean_value)
    preserve = clean_value[:1].isspace() or clean_value[-1:].isspace() or "\n" in clean_value or "\t" in clean_value
    style_attr = f' s="{style_id}"' if style_id is not None else ""
    if preserve:
        return f'<c r="{cell_ref}" t="inlineStr"{style_attr}><is><t xml:space="preserve">{text}</t></is></c>'
    return f'<c r="{cell_ref}" t="inlineStr"{style_attr}><is><t>{text}</t></is></c>'


def _xlsx_number_string(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return f"{value:.15g}"
    return None


def _build_xlsx_sheet_xml(headers: list[str], rows: list[list[object]]) -> str:
    all_rows = [headers] + rows
    max_cols = max((len(r) for r in all_rows), default=1)
    last_col = _xlsx_col_name(max_cols)
    last_row = max(len(all_rows), 1)
    dimension = f"A1:{last_col}{last_row}"
    has_data_rows = len(all_rows) > 1
    total_row_index = len(all_rows)

    col_widths: list[float] = [8.0 for _ in range(max_cols)]
    for row in all_rows:
        for col_index in range(max_cols):
            value = row[col_index] if col_index < len(row) else ""
            value_text = _xml_clean_text("" if value is None else str(value))
            estimated_width = max(8.0, min(60.0, float(len(value_text) + 2)))
            if estimated_width > col_widths[col_index]:
                col_widths[col_index] = estimated_width

    row_xml: list[str] = []
    for row_index, row in enumerate(all_rows, start=1):
        cells: list[str] = []
        is_header_row = row_index == 1
        is_total_row = has_data_rows and row_index == total_row_index
        for col_index in range(1, max_cols + 1):
            value = row[col_index - 1] if col_index - 1 < len(row) else ""
            cell_ref = f"{_xlsx_col_name(col_index)}{row_index}"
            number_value = _xlsx_number_string(value)
            style_id = 1 if is_header_row else (2 if is_total_row else None)
            if number_value is not None:
                style_attr = f' s="{style_id}"' if style_id is not None else ""
                cells.append(f'<c r="{cell_ref}" t="n"{style_attr}><v>{number_value}</v></c>')
            else:
                cells.append(_xlsx_inline_cell(cell_ref, "" if value is None else str(value), style_id))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    cols_xml = "".join(
        f'<col min="{idx}" max="{idx}" width="{width:.2f}" customWidth="1"/>'
        for idx, width in enumerate(col_widths, start=1)
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        f"<cols>{cols_xml}</cols>"
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _xlsx_unique_sheet_name(name: str, used_names: set[str]) -> str:
    base_name = _xlsx_safe_sheet_name(name)
    candidate = base_name
    suffix = 2
    while candidate.lower() in used_names:
        suffix_text = f" ({suffix})"
        candidate = (base_name[: max(1, 31 - len(suffix_text))] + suffix_text).strip()
        suffix += 1
    used_names.add(candidate.lower())
    return candidate


def _build_simple_xlsx_workbook(sheets: list[dict[str, object]]) -> bytes:
    if not sheets:
        sheets = [{"name": "Sheet1", "headers": [], "rows": []}]

    normalized_sheets: list[dict[str, object]] = []
    used_names: set[str] = set()
    for sheet in sheets:
        normalized_sheets.append(
            {
                "name": _xlsx_unique_sheet_name(str(sheet.get("name") or "Sheet"), used_names),
                "headers": list(sheet.get("headers") or []),
                "rows": list(sheet.get("rows") or []),
            }
        )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + "".join(
            f'<sheet name="{xml_escape(str(sheet["name"]))}" sheetId="{idx}" r:id="rId{idx}"/>'
            for idx, sheet in enumerate(normalized_sheets, start=1)
        )
        + "</sheets>"
        "</workbook>"
    )
    style_rel_id = len(normalized_sheets) + 1
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
            for idx in range(1, len(normalized_sheets) + 1)
        )
        + f'<Relationship Id="rId{style_rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for idx in range(1, len(normalized_sheets) + 1)
        )
        +
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        "</fonts>"
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        for idx, sheet in enumerate(normalized_sheets, start=1):
            sheet_xml = _build_xlsx_sheet_xml(
                headers=list(sheet.get("headers") or []),
                rows=list(sheet.get("rows") or []),
            )
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml)
        zf.writestr("xl/styles.xml", styles_xml)
    return output.getvalue()


def _build_simple_xlsx(sheet_name: str, headers: list[str], rows: list[list[object]]) -> bytes:
    return _build_simple_xlsx_workbook([{"name": sheet_name, "headers": headers, "rows": rows}])


def _find_membership_covering(records: list[dict[str, object]], target_date: date) -> dict[str, object] | None:
    for record in records:
        start = record.get("start")
        end = record.get("end")
        if not isinstance(start, date):
            continue
        if start <= target_date and ((end is None) or (isinstance(end, date) and end >= target_date)):
            return record
    return None


def _plan_membership_split(record: dict[str, object], interval_start: date, interval_end: date | None) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    operations: list[dict[str, object]] = []
    trailing_record: dict[str, object] | None = None

    original_start: date = record["start"]  # type: ignore[assignment]
    original_end: date | None = record.get("end")

    before_exists = original_start < interval_start
    if before_exists:
        before_end = interval_start - timedelta(days=1)
        if original_end is not None and before_end < original_start:
            before_exists = False
    else:
        before_end = original_start

    after_exists = interval_end is not None and (
        original_end is None or (isinstance(original_end, date) and original_end > interval_end)
    )

    if before_exists and after_exists:
        operations.append({
            "type": "update_period",
            "stamp": record["stamp"],
            "start": original_start,
            "end": before_end,
        })
        trailing_record = dict(record)
        trailing_record["start"] = interval_end + timedelta(days=1)  # type: ignore[index]
        trailing_record["end"] = original_end
    elif before_exists:
        operations.append({
            "type": "update_period",
            "stamp": record["stamp"],
            "start": original_start,
            "end": before_end,
        })
    elif after_exists and interval_end is not None:
        operations.append({
            "type": "update_period",
            "stamp": record["stamp"],
            "start": interval_end + timedelta(days=1),
            "end": original_end,
        })
    else:
        operations.append({
            "type": "delete",
            "stamp": record["stamp"],
        })

    return operations, trailing_record


def _make_insert_operation(team_code: str, team_stamp: str | None, employee_number: str, employee_name: str, origin: str, start: date, end: date | None, chefe: bool) -> dict[str, object]:
    return {
        "type": "insert",
        "team_code": team_code,
        "team_stamp": team_stamp,
        "employee_number": employee_number,
        "employee_name": employee_name,
        "origin": origin,
        "start": start,
        "end": end,
        "chefe": chefe,
    }


def _membership_insert_from_record(record: dict[str, object], start: date | None = None, end: date | None = None, chefe: bool | None = None) -> dict[str, object]:
    actual_start = start or record["start"]
    actual_end = end if end is not None else record.get("end")
    actual_chefe = chefe if chefe is not None else bool(record.get("is_lead"))
    return _make_insert_operation(
        record.get("team_code") or "",
        record.get("team_stamp") or "",
        record.get("number") or record.get("employee_number") or "",
        record.get("name") or record.get("employee_name") or "",
        record.get("origin") or "",
        actual_start,
        actual_end,
        actual_chefe,
    )


def _resolve_team_period(
    reference_date: date,
    period_type: str,
    custom_start: object,
    custom_end: object,
    specific_date: object | None = None,
) -> tuple[date, date | None]:
    period_type = (period_type or 'reference').lower()
    if period_type == 'reference':
        return reference_date, None
    if period_type == 'specific':
        chosen_date = _coerce_date(specific_date)
        if chosen_date is None:
            raise ValueError('missing_specific_date')
        return chosen_date, None
    if period_type == 'week':
        week_start = reference_date - timedelta(days=reference_date.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
    if period_type == 'custom':
        start_date = _coerce_date(custom_start)
        end_date = _coerce_date(custom_end)
        if start_date is None:
            raise ValueError('missing_custom_start')
        if end_date is not None and end_date < start_date:
            raise ValueError('invalid_custom_range')
        return start_date, end_date
    raise ValueError('invalid_period_type')

def _plan_lead_demotion(team_code: str, start_date: date, end_date: date | None, exclude_employee: str) -> list[dict[str, object]]:
    try:
        lead_rows = database.fetch_team_leads_for_period(team_code, start_date, end_date)
    except RuntimeError as exc:
        raise RuntimeError(f"fetch_leads_failed:{exc}") from exc

    operations: list[dict[str, object]] = []
    for row in lead_rows:
        employee_number = _normalize_code(row.get("no"))
        if not employee_number or employee_number == exclude_employee:
            continue
        employee_name = _coerce_text(row.get("nome")) or employee_number
        origin = _coerce_text(row.get("origem"))
        record_start = _coerce_date(row.get("dataini"))
        record_end = _coerce_date(row.get("datafim"))
        if record_end == TEAM_END_SENTINEL:
            record_end = None
        if not isinstance(record_start, date):
            continue
        if not _segments_overlap(record_start, record_end, start_date, end_date):
            continue
        membership_record = {
            "stamp": _coerce_text(row.get("u_teamstamp")),
            "team_code": _normalize_code(row.get("fref")),
            "team_stamp": _coerce_text(row.get("frefstamp")),
            "number": employee_number,
            "name": employee_name,
            "origin": origin,
            "is_lead": True,
            "start": record_start,
            "end": record_end,
        }
        split_ops, trailing = _plan_membership_split(membership_record, start_date, end_date)
        operations.extend(split_ops)

        if trailing is not None:
            operations.append(_membership_insert_from_record(trailing))

        # Add non-lead interval covering the requested period (bounded by original record)
        interval_end = end_date
        if record_end is not None and (interval_end is None or interval_end > record_end):
            interval_end = record_end
        operations.append(
            _make_insert_operation(
                membership_record["team_code"],
                membership_record["team_stamp"],
                employee_number,
                employee_name,
                origin,
                start_date,
                interval_end,
                chefe=False,
            )
        )
    return operations

def _resolve_week_bounds(week_str: str | None) -> tuple[str, date, date]:
    today = date.today()
    if week_str:
        try:
            year_str, week_part = week_str.split("-W", 1)
            iso_year = int(year_str)
            iso_week = int(week_part)
            start = date.fromisocalendar(iso_year, iso_week, 1)
        except ValueError:
            start = today - timedelta(days=today.weekday())
    else:
        start = today - timedelta(days=today.weekday())
    iso_year, iso_week, _ = start.isocalendar()
    start_of_week = start
    end_of_week = start_of_week + timedelta(days=6)
    resolved_week = f"{iso_year}-W{iso_week:02d}"
    return resolved_week, start_of_week, end_of_week



def _user_allowed_market_codes(user: dict[str, object], markets: list[object]) -> list[str]:
    """Determine which market codes the user can access."""
    if not user:
        return []
    allowed: list[str] = []
    for market in markets:
        field = MARKET_ACCESS_FIELDS.get(market.code)
        if field is None:
            allowed.append(market.code)
            continue
        if user.get(field):
            allowed.append(market.code)
    return allowed


def _user_team_group_filters(user: dict[str, object]) -> dict[str, set[str]]:
    """
    Determine which planning groups the user can see based on market permissions.

    Rules:
    - If has MA -> only MAROC and SOUS-TRAITANTS
    - If has PT or ES or FR or DE -> all except MAROC
    - If has IC or IA or IL -> INTERSOL and SOUS-TRAITANTS

    Combined inclusions are unioned; exclusions remove from final set.
    """
    include: set[str] = set()
    exclude: set[str] = set()
    allow_all = False

    has_ma = bool(user.get("u_ma"))
    has_eu = any(user.get(flag) for flag in ("u_pt", "u_es", "u_fr", "u_de"))
    has_inter = any(user.get(flag) for flag in ("u_ic", "u_ia", "u_il"))

    if has_ma:
        rule = TEAM_GROUP_RULES["MAROC_ONLY"]
        include.update(rule["include"])
        exclude.update(rule["exclude"])

    if has_eu:
        rule = TEAM_GROUP_RULES["EUROPE_EXCEPT_MAROC"]
        allow_all = True  # all groups allowed except the exclusions below
        exclude.update(rule["exclude"])

    if has_inter:
        rule = TEAM_GROUP_RULES["INTERSOL_SOUS_TRAITANTS"]
        include.update(rule["include"])
        exclude.update(rule["exclude"])

    return {"include": include, "exclude": exclude, "allow_all": allow_all}


def _selected_market_visible_planning_groups(selected_market_codes: Iterable[str]) -> set[str] | None:
    visible_groups = set(GLOBAL_PLANNING_GROUPS)
    has_market_specific_group = False
    for raw_code in selected_market_codes:
        code = _normalize_code(raw_code)
        groups = MARKET_PLANNING_GROUPS.get(code)
        if not groups:
            continue
        visible_groups.update(groups)
        has_market_specific_group = True
    return visible_groups if has_market_specific_group else None


def _planning_group_visible_for_selected_markets(group_key: str, selected_market_codes: Iterable[str]) -> bool:
    visible_groups = _selected_market_visible_planning_groups(selected_market_codes)
    if not visible_groups:
        return True
    normalized_group = _normalize_code(group_key)
    if not normalized_group:
        return True
    return normalized_group in visible_groups


def _project_visible_for_selected_markets(
    origin_market_code: str,
    is_external_planning: bool,
    selected_market_codes: Iterable[str],
) -> bool:
    normalized_selected_codes = {_normalize_code(code) for code in selected_market_codes if _normalize_code(code)}
    if not normalized_selected_codes:
        return True
    normalized_origin = _normalize_code(origin_market_code)
    if normalized_origin in normalized_selected_codes:
        return True
    if not is_external_planning:
        return False
    return any(code != "MA" for code in normalized_selected_codes)


def _normalize_code(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore').strip()
    return str(value).strip()


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore').strip()
    return str(value).strip()




def _coerce_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, 'date'):
        candidate = value.date()
        if isinstance(candidate, date):
            return candidate
    if isinstance(value, str):
        text_value = value.strip()
        if not text_value:
            return None
        try:
            return datetime.fromisoformat(text_value).date()
        except ValueError:
            pass
        for fmt in ('%d/%m/%Y', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%Y.%m.%d'):
            try:
                return datetime.strptime(text_value[:len(fmt)], fmt).date()
            except ValueError:
                continue
    return None



def _coerce_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        normalized = text.replace(',', '.')
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None
    return None


def _coerce_flag(value: object) -> bool:
    """Normalise DB flag values (int/str/bool) into a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text.isdigit():
            try:
                return int(text) != 0
            except ValueError:
                return False
        if text in {"true", "t", "yes", "y", "on"}:
            return True
        if text in {"false", "f", "no", "n", "off"}:
            return False
    return bool(value)


def _coerce_int(value: object) -> int | None:
    decimal_value = _coerce_decimal(value)
    if decimal_value is None:
        return None
    if decimal_value != decimal_value.to_integral_value():
        return None
    try:
        return int(decimal_value)
    except (OverflowError, ValueError):
        return None


def _can_access_team_management(user: dict[str, object] | None) -> bool:
    return bool(user and (user.get("u_teams") or user.get("u_admin")))


def _serialize_absence_row(row: dict[str, object], reference_date: date) -> dict[str, object]:
    start_date = _coerce_date(row.get("dataini"))
    end_date = _coerce_date(row.get("datafim"))
    employee_number = _normalize_code(row.get("no"))
    employee_name = _coerce_text(row.get("nome")) or employee_number
    is_current = bool(start_date and end_date and start_date <= reference_date <= end_date)
    return {
        "u_ausenciasstamp": _coerce_text(row.get("u_ausenciasstamp")).upper()[:25],
        "employee_number": employee_number,
        "employee_name": employee_name,
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "start_date_label": start_date.strftime("%d/%m/%Y") if start_date else "",
        "end_date_label": end_date.strftime("%d/%m/%Y") if end_date else "",
        "obs": _coerce_text(row.get("obs")),
        "marcada": _coerce_flag(row.get("marcada")),
        "is_current": is_current,
    }


def _format_employee_label(employee_number: object, employee_name: object) -> str:
    number = _normalize_code(employee_number)
    name = _coerce_text(employee_name)
    if number and name and name != number:
        return f"{name} ({number})"
    return name or number


def _build_employee_name_lookup(rows: Iterable[dict[str, object]]) -> dict[str, str]:
    names_by_number: dict[str, list[str]] = {}
    for row in rows:
        employee_number = _normalize_code(row.get("no"))
        employee_name = _coerce_text(row.get("cval4") or row.get("nome"))
        if not employee_number or not employee_name:
            continue
        bucket = names_by_number.setdefault(employee_number, [])
        if employee_name not in bucket:
            bucket.append(employee_name)
    lookup: dict[str, str] = {}
    for employee_number, names in names_by_number.items():
        if len(names) == 1:
            lookup[employee_number] = names[0]
        else:
            lookup[employee_number] = " / ".join(names)
    return lookup


def _serialize_intersol_role_row(
    row: dict[str, object],
    employee_name_lookup: dict[str, str] | None = None,
) -> dict[str, object]:
    employee_number = _normalize_code(row.get("no"))
    employee_name = _coerce_text(row.get("employee_name"))
    if not employee_name and employee_name_lookup:
        employee_name = employee_name_lookup.get(employee_number, "")
    employee_name = employee_name or employee_number
    role_value = _coerce_text(row.get("role")).upper()
    return {
        "employee_number": employee_number,
        "employee_name": employee_name,
        "employee_label": _format_employee_label(employee_number, employee_name),
        "role": role_value,
        "role_label": INTERSOL_ROLE_LABELS.get(role_value, role_value),
        "is_depot_manager": _coerce_flag(row.get("is_depot_manager")),
    }


def _serialize_intersol_regularization_row(row: dict[str, object]) -> dict[str, object]:
    year = _coerce_int(row.get("ano"))
    month = _coerce_int(row.get("mes"))
    employee_number = _normalize_code(row.get("no"))
    employee_name = _coerce_text(row.get("nome")) or employee_number
    value = _coerce_decimal(row.get("valor")) or Decimal("0")
    month_value = ""
    month_label = ""
    if year is not None and month is not None and 1 <= month <= 12:
        month_value = f"{year:04d}-{month:02d}"
        month_label = f"{month:02d}/{year:04d}"
    return {
        "u_intersol_regularizacoesstamp": _coerce_text(row.get("u_intersol_regularizacoesstamp")).upper()[:25],
        "year": year or 0,
        "month": month or 0,
        "month_value": month_value,
        "month_label": month_label,
        "employee_number": employee_number,
        "employee_name": employee_name,
        "employee_label": _format_employee_label(employee_number, employee_name),
        "obs": _coerce_text(row.get("obs")),
        "value": float(_quantize_money(value)),
    }


def _normalize_person_name(value: object) -> str:
    text_value = _coerce_text(value)
    if not text_value:
        return ""
    return " ".join(text_value.upper().split())


def _build_absence_lookup(rows: Iterable[dict[str, object]]) -> dict[str, dict[object, list[tuple[date, date]]]]:
    by_name: dict[str, list[tuple[date, date]]] = {}
    by_identity: dict[tuple[str, str], list[tuple[date, date]]] = {}
    for row in rows:
        start_date = _coerce_date(row.get("dataini"))
        end_date = _coerce_date(row.get("datafim"))
        employee_number = _normalize_code(row.get("no"))
        employee_name_key = _normalize_person_name(row.get("nome"))
        if not start_date or not end_date or not employee_name_key:
            continue
        interval = (start_date, end_date)
        by_name.setdefault(employee_name_key, []).append(interval)
        if employee_number:
            by_identity.setdefault((employee_number, employee_name_key), []).append(interval)
    return {"by_name": by_name, "by_identity": by_identity}


def _get_employee_absence_intervals(
    absence_lookup: dict[str, dict[object, list[tuple[date, date]]]] | None,
    employee_number: object,
    employee_name: object,
) -> list[tuple[date, date]]:
    if not absence_lookup:
        return []
    employee_number_key = _normalize_code(employee_number)
    employee_name_key = _normalize_person_name(employee_name)
    if not employee_name_key:
        return []
    by_identity = absence_lookup.get("by_identity") or {}
    by_name = absence_lookup.get("by_name") or {}
    if employee_number_key and (employee_number_key, employee_name_key) in by_identity:
        return by_identity.get((employee_number_key, employee_name_key), [])
    return by_name.get(employee_name_key, [])


def _date_in_absence_period(target_date: object, absence_intervals: Iterable[tuple[date, date]] | None) -> bool:
    if not isinstance(target_date, date):
        return False
    for start_date, end_date in absence_intervals or []:
        if start_date <= target_date <= end_date:
            return True
    return False


def _normalize_intersol_item_code(value: object) -> str:
    return (_coerce_text(value) or "").strip()


def _infer_intervention_type(row: dict[str, object]) -> str:
    raw_type = _coerce_text(row.get("tipo_intervencao") or row.get("intervencao") or row.get("u_tipo_intervencao"))
    if raw_type:
        return raw_type.lower()
    litem = _normalize_intersol_item_code(row.get("litem"))
    if litem in INTERSOL_INTEMPERIE_LITEMS:
        return "intemperie"
    if litem in INTERSOL_PREPARATION_LITEMS:
        return "prepa"
    if litem in INTERSOL_REPARATION_LITEMS:
        return "reparation"
    if litem in INTERSOL_LAVAGE_LITEMS:
        return "lavage"
    if litem in INTERSOL_OTHER_LITEMS:
        return "other"
    finish = (_coerce_text(row.get("acabamento")) or "").lower()
    if "intemp" in finish:
        return "intemperie"
    if "prepa" in finish or "prep" in finish:
        return "prepa"
    if "repar" in finish or "sav" in finish:
        return "reparation"
    if "autre" in finish:
        return "other"
    if "coul" in finish:
        return "coulage"
    if "lav" in finish:
        return "lavage"
    serragem = _coerce_decimal(row.get("aml_m2serragem")) or _coerce_decimal(row.get("am_m2serragem"))
    if serragem and serragem > 0:
        return "scie"
    return "coulage"


def _is_intemperie_row(row: dict[str, object]) -> bool:
    if _coerce_flag(row.get("intemperie") or row.get("u_intemperie")):
        return True
    litem = _normalize_intersol_item_code(row.get("litem"))
    if litem in INTERSOL_INTEMPERIE_LITEMS:
        return True
    finish = _coerce_text(row.get("acabamento")).lower()
    if "intemp" in finish:
        return True
    return False


def _extract_distance(row: dict[str, object]) -> float | None:
    distance_value = _coerce_decimal(
        row.get("distance_km")
        or row.get("distancia_km")
        or row.get("distance")
        or row.get("km_distance")
    )
    if distance_value is None:
        return None
    try:
        distance = float(distance_value)
    except (TypeError, InvalidOperation):
        return None
    return distance if distance >= 0 else None


def _extract_deplacement_type(row: dict[str, object]) -> str:
    return _coerce_text(
        row.get("u_tpdep")
        or row.get("tpdep")
        or row.get("tipo_deplacement")
        or row.get("deplacement_type")
    )


def _resolve_intersol_period(
    month_param: str | None,
    *,
    today: date | None = None,
    strict: bool = False,
) -> tuple[str, date, date, date, str, str]:
    current = today or date.today()
    normalized_param = _coerce_text(month_param)

    if normalized_param:
        try:
            year, month = [int(part) for part in normalized_param.split("-")[:2]]
            selected_month_start = date(year, month, 1)
        except Exception:
            if strict:
                raise ValueError("invalid_month_param")
            selected_month_start = current.replace(day=1)
    else:
        selected_month_start = current.replace(day=1)

    if selected_month_start.month == 1:
        previous_month_start = date(selected_month_start.year - 1, 12, 1)
    else:
        previous_month_start = date(selected_month_start.year, selected_month_start.month - 1, 1)

    period_start = previous_month_start.replace(day=22)
    period_end = selected_month_start.replace(day=21)
    selected_month_value = selected_month_start.strftime("%Y-%m")
    selected_month_label = selected_month_start.strftime("%m/%Y")
    period_label = f"Período: {period_start.strftime('%d/%m/%Y')} a {period_end.strftime('%d/%m/%Y')}"
    return selected_month_value, selected_month_start, period_start, period_end, selected_month_label, period_label


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _month_end(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1) - timedelta(days=1)
    return date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)


def _is_business_day(target_date: object) -> bool:
    return isinstance(target_date, date) and target_date.weekday() < 5


def _is_intersol_pending_period(entry_date: object, selected_month_start: date) -> bool:
    return isinstance(entry_date, date) and entry_date >= selected_month_start.replace(day=22)


def _intersol_detail_daily_rate(role: object = None) -> Decimal:
    role_key = _coerce_text(role).upper()
    if role_key == ROLE_AIDE:
        return Decimal("130.00")
    return INTERSOL_DETAIL_PREPAID


def _intersol_detail_paid_value(entry_date: object, selected_month_start: date, role: object = None) -> Decimal:
    if not _is_business_day(entry_date):
        return Decimal("0")
    if entry_date < selected_month_start:
        return _intersol_detail_daily_rate(role)
    return Decimal("0")


def _compute_intersol_panier_repas(
    detail_rows: Iterable[dict[str, object]],
    selected_month_start: date,
) -> int:
    month_start = selected_month_start
    month_end = _month_end(selected_month_start)
    counted_dates: set[date] = set()
    panier_repas = 0

    for row in detail_rows:
        row_date = _coerce_date((row or {}).get("date"))
        if not row_date or row_date < month_start or row_date > month_end:
            continue
        if row_date in counted_dates or not _is_business_day(row_date):
            continue
        if (row or {}).get("is_regularization"):
            continue
        if (row or {}).get("is_not_worked"):
            continue
        if _coerce_text((row or {}).get("finish_type")).upper() == "INTEMPERIE":
            continue
        counted_dates.add(row_date)
        panier_repas += 1

    return panier_repas


def _serialize_intersol_regularization_rows(
    rows: Iterable[dict[str, object]],
    selected_month_start: date,
) -> tuple[list[dict[str, object]], Decimal]:
    serialized: list[dict[str, object]] = []
    total_value = Decimal("0")
    period_label = selected_month_start.strftime("%m/%Y")

    for row in rows:
        value = _quantize_money(_coerce_decimal((row or {}).get("valor")) or Decimal("0"))
        total_value += value
        serialized.append(
            {
                "date": period_label,
                "chantier": "Regularização",
                "finish_type": _coerce_text((row or {}).get("obs")),
                "m2": 0.0,
                "chantier_total_m2": 0.0,
                "m2_scie": 0.0,
                "kg": 0.0,
                "base_value": 0.0,
                "finitions_value": 0.0,
                "scie_value": 0.0,
                "steel_value": 0.0,
                "prime_multiple": 0.0,
                "prime_effort": 0.0,
                "prime_effort_validated": 0.0,
                "prime_effort_pending": 0.0,
                "forfait_used": False,
                "paid_value": 0.0,
                "display_total": float(value),
                "total": float(value),
                "is_estimate": False,
                "is_pending_period": False,
                "is_not_worked": False,
                "is_regularization": True,
            }
        )

    return serialized, _quantize_money(total_value)


def _build_intersol_regularization_lookup(
    rows: Iterable[dict[str, object]],
) -> dict[tuple[str, str], list[dict[str, object]]]:
    lookup: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        employee_number = _normalize_code(row.get("no"))
        employee_name_key = _normalize_person_name(row.get("nome"))
        if not employee_number:
            continue
        lookup.setdefault((employee_number, employee_name_key), []).append(row)
    return lookup


def _serialize_intersol_detail_rows(
    daily_breakdown: Iterable[object],
    selected_month_start: date,
    absence_intervals: Iterable[tuple[date, date]] | None = None,
    role: object = None,
) -> tuple[list[dict[str, object]], Decimal, Decimal]:
    rows: list[dict[str, object]] = []
    paid_total = Decimal("0")
    display_total_sum = Decimal("0")
    daily_rate = _intersol_detail_daily_rate(role)
    previous_month_start = (
        date(selected_month_start.year - 1, 12, 1)
        if selected_month_start.month == 1
        else date(selected_month_start.year, selected_month_start.month - 1, 1)
    )
    previous_period_start = previous_month_start.replace(day=22)
    previous_period_end = selected_month_start - timedelta(days=1)
    recorded_dates: set[date] = set()
    for item in daily_breakdown:
        item_date = getattr(item, "date", None)
        if isinstance(item_date, date):
            recorded_dates.add(item_date)
        paid_value = _intersol_detail_paid_value(getattr(item, "date", None), selected_month_start, role=role)
        paid_total += paid_value
        total_value = _coerce_decimal(getattr(item, "total", None)) or Decimal("0")
        display_total = _quantize_money(total_value - paid_value)
        display_total_sum += display_total
        rows.append(
            {
                "date": getattr(item, "date").isoformat(),
                "chantier": getattr(item, "chantier", ""),
                "finish_type": getattr(item, "finish_type", ""),
                "m2": getattr(item, "sqm", 0),
                "chantier_total_m2": getattr(item, "chantier_total_sqm", 0),
                "m2_scie": getattr(item, "sqm_scie", 0),
                "kg": getattr(item, "kg_steel", 0),
                "base_value": getattr(item, "base_value", 0),
                "finitions_value": getattr(item, "finitions_value", 0),
                "scie_value": getattr(item, "scie_value", 0),
                "steel_value": getattr(item, "steel_value", 0),
                "prime_multiple": getattr(item, "prime_multiple", 0),
                "prime_effort": getattr(item, "prime_effort", 0),
                "prime_effort_validated": getattr(item, "prime_effort_validated", 0),
                "prime_effort_pending": getattr(item, "prime_effort_pending", 0),
                "forfait_used": getattr(item, "forfait_used", False),
                "paid_value": float(_quantize_money(paid_value)),
                "display_total": float(display_total),
                "total": getattr(item, "total", 0),
                "is_estimate": False,
                "is_pending_period": _is_intersol_pending_period(getattr(item, "date", None), selected_month_start),
                "is_not_worked": False,
                "is_regularization": False,
            }
        )

    missing_day = previous_period_start
    while missing_day <= previous_period_end:
        if (
            _is_business_day(missing_day)
            and missing_day not in recorded_dates
            and not _date_in_absence_period(missing_day, absence_intervals)
        ):
            paid_value = _intersol_detail_paid_value(missing_day, selected_month_start, role=role)
            total_value = Decimal("0")
            display_total = _quantize_money(total_value - paid_value)
            paid_total += paid_value
            display_total_sum += display_total
            rows.append(
                {
                    "date": missing_day.isoformat(),
                    "chantier": "Não trabalhou",
                    "finish_type": "",
                    "m2": 0.0,
                    "chantier_total_m2": 0.0,
                    "m2_scie": 0.0,
                    "kg": 0.0,
                    "base_value": 0.0,
                    "finitions_value": 0.0,
                    "scie_value": 0.0,
                    "steel_value": 0.0,
                    "prime_multiple": 0.0,
                    "prime_effort": 0.0,
                    "prime_effort_validated": 0.0,
                    "prime_effort_pending": 0.0,
                    "forfait_used": False,
                    "paid_value": float(_quantize_money(paid_value)),
                    "display_total": float(display_total),
                    "total": 0.0,
                    "is_estimate": False,
                    "is_pending_period": False,
                    "is_not_worked": True,
                    "is_regularization": False,
                }
            )
        missing_day += timedelta(days=1)

    estimate_date = selected_month_start.replace(day=22)
    estimate_end = _month_end(selected_month_start)
    while estimate_date <= estimate_end:
        if _is_business_day(estimate_date) and not _date_in_absence_period(estimate_date, absence_intervals):
            paid_value = _intersol_detail_paid_value(estimate_date, selected_month_start, role=role)
            total_value = daily_rate
            display_total = _quantize_money(total_value - paid_value)
            paid_total += paid_value
            display_total_sum += display_total
            rows.append(
                {
                    "date": estimate_date.isoformat(),
                    "chantier": "Estimativa",
                    "finish_type": "",
                    "m2": 0.0,
                    "chantier_total_m2": 0.0,
                    "m2_scie": 0.0,
                    "kg": 0.0,
                    "base_value": float(daily_rate),
                    "finitions_value": 0.0,
                    "scie_value": 0.0,
                    "steel_value": 0.0,
                    "prime_multiple": 0.0,
                    "prime_effort": 0.0,
                    "prime_effort_validated": 0.0,
                    "prime_effort_pending": 0.0,
                    "forfait_used": True,
                    "paid_value": float(_quantize_money(paid_value)),
                    "display_total": float(display_total),
                    "total": float(daily_rate),
                    "is_estimate": True,
                    "is_pending_period": True,
                    "is_not_worked": False,
                    "is_regularization": False,
                }
            )
        estimate_date += timedelta(days=1)

    rows.sort(key=lambda item: (item.get("date") or "", item.get("is_estimate", False)))
    return rows, _quantize_money(paid_total), _quantize_money(display_total_sum)


def _build_intersol_tasks(rows: list[dict[str, object]], selected_team_codes: list[str] | None = None) -> tuple[list[IntersolTask], dict[str, str]]:
    tasks: list[IntersolTask] = []
    role_hints: dict[str, str] = {}
    selected_team_codes = selected_team_codes or []
    chantier_totals_by_day: dict[tuple[date, str], Decimal] = {}
    seen_am_stamps_by_day: dict[tuple[date, str], set[str]] = {}

    for row in rows:
        task_date = _coerce_date(row.get("data"))
        chantier_code = _normalize_code(row.get("processo"))
        am_stamp = _normalize_code(row.get("u_amstamp"))
        if task_date is None or not chantier_code or not am_stamp:
            continue
        key = (task_date, chantier_code)
        seen_for_key = seen_am_stamps_by_day.setdefault(key, set())
        if am_stamp in seen_for_key:
            continue
        seen_for_key.add(am_stamp)
        chantier_totals_by_day[key] = chantier_totals_by_day.get(key, Decimal("0")) + (_coerce_decimal(row.get("am_qtt")) or Decimal("0"))

    for row in rows:
        team_code = _normalize_code(row.get("fref"))
        if selected_team_codes and team_code not in selected_team_codes:
            continue
        team_name = _coerce_text(row.get("fref_name")) or team_code
        task_date = _coerce_date(row.get("data"))
        if task_date is None:
            continue
        employee_number = _normalize_code(row.get("no"))
        if not employee_number:
            continue
        employee_name = _coerce_text(row.get("nome")) or employee_number
        finish_type = _coerce_text(row.get("acabamento"))
        sqm = _coerce_decimal(row.get("aml_qtt")) or Decimal("0")
        chantier_code = _normalize_code(row.get("processo"))
        sqm_total = chantier_totals_by_day.get((task_date, chantier_code), _coerce_decimal(row.get("am_qtt")) or Decimal("0"))
        sqm_scie = _coerce_decimal(row.get("aml_m2serragem")) or Decimal("0")
        kg_steel = _coerce_decimal(row.get("aml_kgferro")) or Decimal("0")
        effort_prime = _coerce_decimal(row.get("aml_prime") or row.get("u_prime") or row.get("prime")) or Decimal("0")
        effort_prime_validated = _coerce_flag(row.get("aml_validprime") or row.get("u_validprime") or row.get("validprime"))
        intervention_type = _infer_intervention_type(row)
        is_intemp = _is_intemperie_row(row)
        distance = _extract_distance(row)
        distance_dec = Decimal(str(distance)) if distance is not None else None
        deplacement_type = _extract_deplacement_type(row)

        tasks.append(
            IntersolTask(
                date=task_date,
                team_code=team_code,
                team_name=team_name,
                employee_number=employee_number,
                employee_name=employee_name,
                chantier=_coerce_text(row.get("processo")) or "",
                finish_type=finish_type,
                sqm=sqm,
                sqm_total_chantier=sqm_total,
                sqm_scie=sqm_scie,
                kg_steel=kg_steel,
                intervention_type=intervention_type,
                is_intemperie=is_intemp,
                distance_km=distance_dec,
                deplacement_type=deplacement_type,
                effort_prime=effort_prime,
                effort_prime_validated=effort_prime_validated,
                is_chief=_coerce_flag(row.get("chefe")),
            )
        )

    return tasks, role_hints


def _build_intersol_prime_records(
    rows: list[dict[str, object]],
    selected_team_codes: list[str] | None = None,
) -> list[dict[str, object]]:
    selected_team_codes = selected_team_codes or []
    records: list[dict[str, object]] = []

    for row in rows:
        team_code = _normalize_code(row.get("fref"))
        if selected_team_codes and team_code not in selected_team_codes:
            continue
        line_stamp = _normalize_code(row.get("u_amlstamp"))
        if not line_stamp:
            continue
        prime_value = _coerce_decimal(row.get("aml_prime") or row.get("u_prime") or row.get("prime"))
        if prime_value is None or prime_value == 0:
            continue
        task_date = _coerce_date(row.get("data"))
        records.append(
            {
                "u_amlstamp": line_stamp,
                "date": task_date.isoformat() if task_date else "",
                "date_label": task_date.strftime("%d/%m/%Y") if task_date else "",
                "team_code": team_code,
                "team_name": _coerce_text(row.get("fref_name")) or team_code,
                "chantier": _coerce_text(row.get("processo")) or "",
                "employee_number": _normalize_code(row.get("no")),
                "employee_name": _coerce_text(row.get("nome")) or _normalize_code(row.get("no")),
                "prime": float(_quantize_money(prime_value)),
                "validated": _coerce_flag(row.get("aml_validprime") or row.get("u_validprime") or row.get("validprime")),
            }
        )

    records.sort(
        key=lambda item: (
            item.get("date") or "",
            item.get("team_code") or "",
            (item.get("employee_name") or "").lower(),
            item.get("chantier") or "",
        )
    )
    return records


def _apply_intersol_role_hints(roles_by_employee: dict[str, str], role_hints: dict[str, str]) -> None:
    for num, hint in role_hints.items():
        if hint == ROLE_CHEF:
            roles_by_employee[num] = hint
            continue
        roles_by_employee.setdefault(num, hint)


def _serialize_intersol_summary_row(
    row: object,
    selected_month_start: date | None = None,
    absence_lookup: dict[str, dict[object, list[tuple[date, date]]]] | None = None,
) -> dict[str, object]:
    total_value = getattr(row, "total", 0)
    paid_total = 0.0
    panier_repas = getattr(row, "panier_repas", 0)
    if selected_month_start is not None:
        absence_intervals = _get_employee_absence_intervals(
            absence_lookup,
            getattr(row, "employee_number", ""),
            getattr(row, "employee_name", ""),
        )
        detail_rows, paid_total_dec, display_total_sum = _serialize_intersol_detail_rows(
            getattr(row, "daily_breakdown", []),
            selected_month_start,
            absence_intervals=absence_intervals,
            role=getattr(row, "role", None),
        )
        total_value = float(display_total_sum)
        paid_total = float(paid_total_dec)
        panier_repas = _compute_intersol_panier_repas(detail_rows, selected_month_start)
    return {
        "employee_number": getattr(row, "employee_number", ""),
        "employee_name": getattr(row, "employee_name", ""),
        "team_code": getattr(row, "team_code", ""),
        "worked_days": getattr(row, "worked_days", 0),
        "business_days": getattr(row, "business_days", 0),
        "m2_total": getattr(row, "m2_total", 0),
        "finitions_pay": getattr(row, "finitions_pay", 0),
        "scie_total_m2": getattr(row, "scie_total_m2", 0),
        "scie_pay": getattr(row, "scie_pay", 0),
        "kg_total": getattr(row, "kg_total", 0),
        "kg_pay": getattr(row, "kg_pay", 0),
        "prime_multiple": getattr(row, "prime_multiple", 0),
        "prime_chef": getattr(row, "prime_chef", 0),
        "prime_depot": getattr(row, "prime_depot", 0),
        "prime_effort": getattr(row, "prime_effort", 0),
        "prime_effort_validated": getattr(row, "prime_effort_validated", 0),
        "prime_effort_pending": getattr(row, "prime_effort_pending", 0),
        "intemperies_total": getattr(row, "intemperies_total", 0),
        "complement_minimum": getattr(row, "complement_minimum", 0),
        "panier_repas": panier_repas,
        "grand_deplacement": getattr(row, "grand_deplacement", 0),
        "zone_counts": getattr(row, "zone_counts", {}) or {},
        "paid_total": paid_total,
        "total": total_value,
    }


def _serialize_intersol_totals(
    totals: dict[str, object],
    summary_rows: Iterable[dict[str, object]],
) -> dict[str, object]:
    serialized = dict(totals or {})
    total_sum = Decimal("0")
    panier_repas_sum = 0
    for row in summary_rows:
        total_sum += _coerce_decimal((row or {}).get("total")) or Decimal("0")
        panier_repas_sum += int((row or {}).get("panier_repas") or 0)
    serialized["total"] = float(_quantize_money(total_sum))
    serialized["panier_repas"] = panier_repas_sum
    return serialized

@app.before_request
def configure_language() -> None:
    requested = request.args.get("lang")
    if requested:
        lang = resolve_language(requested)
        session["lang"] = lang
    else:
        lang = session.get("lang")
    if not lang:
        best_match = request.accept_languages.best_match(LANGUAGE_CODES) if request.accept_languages else None
        lang = resolve_language(best_match)
    g.language = lang
    g.translations = get_translations(lang)


@app.context_processor
def inject_i18n():
    translations = getattr(g, "translations", get_translations(DEFAULT_LANGUAGE))
    current_lang = getattr(g, "language", DEFAULT_LANGUAGE)
    return {
        "t": translations,
        "current_lang": current_lang,
        "languages": available_languages(),
    }


@app.route("/language/<lang_code>")
def change_language(lang_code: str):
    session["lang"] = resolve_language(lang_code)
    next_url = request.args.get("next") or request.referrer or url_for("index")
    return redirect(next_url)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    translations = g.translations
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error = translations["login_error_blank"]
        else:
            try:
                user_row = database.fetch_user_by_credentials(username, password)
            except RuntimeError as exc:
                error = translations["login_error_runtime"].format(error=str(exc))
            else:
                if user_row:
                    if not user_row.get("u_planning"):
                        error = translations["login_error_no_access"]
                    else:
                        session["user"] = {
                            "usercode": user_row["usercode"],
                            "username": user_row["username"],
                            "u_admin": 1 if _coerce_flag(user_row.get("u_admin")) else 0,
                            "u_adminis": 1 if _coerce_flag(user_row.get("u_adminis")) else 0,
                            "u_de": 1 if _coerce_flag(user_row.get("u_de")) else 0,
                            "u_es": 1 if _coerce_flag(user_row.get("u_es")) else 0,
                            "u_fr": 1 if _coerce_flag(user_row.get("u_fr")) else 0,
                            "u_ia": 1 if _coerce_flag(user_row.get("u_ia")) else 0,
                            "u_ic": 1 if _coerce_flag(user_row.get("u_ic")) else 0,
                            "u_il": 1 if _coerce_flag(user_row.get("u_il")) else 0,
                            "u_ma": 1 if _coerce_flag(user_row.get("u_ma")) else 0,
                            "u_pt": 1 if _coerce_flag(user_row.get("u_pt")) else 0,
                            "u_teams": 1 if _coerce_flag(user_row.get("u_teams")) else 0,
                        }
                        return redirect(url_for("index"))
                else:
                    error = translations["login_error_invalid"]
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/")
def index():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    translations = g.translations

    week_param = request.args.get("week")
    resolved_week, week_start, week_end = _resolve_week_bounds(week_param)

    available_markets = list_markets()
    allowed_market_codes = _user_allowed_market_codes(user, available_markets)
    available_markets = [market for market in available_markets if market.code in allowed_market_codes]
    selected_market_codes = request.args.getlist("markets")
    if not selected_market_codes:
        selected_market_codes = list(allowed_market_codes)
    else:
        selected_market_codes = [code for code in selected_market_codes if code in allowed_market_codes]
        if not selected_market_codes:
            selected_market_codes = list(allowed_market_codes)
    # Planning type filter: 'obra' and/or 'manutencao' (default both)
    selected_types = [t.lower() for t in request.args.getlist("types") if isinstance(t, str)]
    if not selected_types:
        selected_types = ["obra", "manutencao"]

    if not allowed_market_codes:
        project_rows = []
        assignment_rows = []
        assignment_error = None
        db_error = "Sem mercados autorizados para o utilizador."
    else:
        raw_market_filters = market_filters(selected_market_codes)
        include_external_planning = any(code != "MA" for code in selected_market_codes)
        try:
            project_rows = database.fetch_projects_for_week(
                week_start,
                week_end,
                raw_market_filters,
                include_external_planning=include_external_planning,
            )
            db_error = None
        except RuntimeError as exc:
            project_rows = []
            db_error = str(exc)

    filtered_project_rows: list[dict[str, object]] = []
    for row in project_rows:
        origin_market = get_market(_coerce_text(row.get("u_origem")))
        is_external_planning = _coerce_flag(row.get("u_planext"))
        if not _project_visible_for_selected_markets(origin_market.code, is_external_planning, selected_market_codes):
            continue
        filtered_project_rows.append(row)
    project_rows = filtered_project_rows

    project_codes: list[str] = []
    project_meta: dict[str, dict[str, str]] = {}
    project_opcstamp_by_code: dict[str, str] = {}
    project_opcstamps: set[str] = set()
    for row in project_rows:
        code = _normalize_code(row.get("processo"))
        row["processo"] = code
        if code:
            project_codes.append(code)
            project_meta[code] = {
                "name": _coerce_text(row.get("nome")) or "",
                "description": _coerce_text(row.get("descricao")) or "",
            }
            opcstamp = _coerce_text(row.get("opcstamp"))
            if opcstamp:
                opcstamp = opcstamp.upper()
                project_opcstamp_by_code[code] = opcstamp
                project_opcstamps.add(opcstamp)
    if allowed_market_codes:
        try:
            assignment_rows = database.fetch_assignments_for_projects(week_start, week_end, project_codes)
        except RuntimeError as exc:
            assignment_rows = []
            assignment_error = str(exc)
        else:
            assignment_error = None

    if assignment_error:
        db_error = f"{db_error}\n{assignment_error}" if db_error else assignment_error

    plan_stamps: set[str] = set()
    assignments_map: dict[tuple[str, date], list[dict[str, object]]] = {}
    for assignment in assignment_rows:
        project_code = _normalize_code(assignment.get("processo"))
        if not project_code:
            continue
        assignment_date = _coerce_date(assignment.get("data"))
        if assignment_date is None:
            continue
        key = (project_code, assignment_date)
        assignment_code = _normalize_code(assignment.get("fref"))
        assignment_name = _coerce_text(assignment.get("nmfref"))
        group_raw = _coerce_text(assignment.get("u_planning"))
        if not group_raw and assignment_code.upper() in INTERSOL_TEAM_CODES:
            group_raw = "INTERSOL"
        group_key, group_label = _normalise_planning_group(group_raw)
        group_key_upper = group_key.upper()
        if not _planning_group_visible_for_selected_markets(group_key_upper, selected_market_codes):
            continue
        plan_stamp_raw = _coerce_text(assignment.get("u_planostamp"))
        plan_stamp = plan_stamp_raw.upper()[:25] if plan_stamp_raw else ""
        plan_fixed = _coerce_decimal(assignment.get("fixo"))
        plan_bonus = _coerce_decimal(assignment.get("premio"))
        if plan_stamp:
            plan_stamps.add(plan_stamp)
        project_details = project_meta.get(project_code, {})
        item = {
            "code": assignment_code or (assignment_name or ""),
            "name": assignment_name,
            "group": group_key_upper,
            "group_label": group_label,
            "plan_stamp": plan_stamp,
            "plan_date": assignment_date.isoformat() if assignment_date else "",
            "plan_fref": assignment_code or "",
            "plan_processo": project_code or "",
            "plan_fref_name": assignment_name or "",
            "plan_processo_name": (project_details.get("description") or project_details.get("name") or ""),
            "has_lines": bool(assignment.get("has_lines")),
            "plan_fixo": float(plan_fixed) if isinstance(plan_fixed, Decimal) else (plan_fixed if plan_fixed is not None else None),
            "plan_premio": float(plan_bonus) if isinstance(plan_bonus, Decimal) else (plan_bonus if plan_bonus is not None else None),
        }
        assignments_map.setdefault(key, []).append(item)

    for key, items in assignments_map.items():
        assignments_map[key] = sorted(
            items,
            key=lambda entry: (str(entry.get("code") or ""), str(entry.get("name") or ""))
        )

    plan_line_map: dict[str, list[dict[str, object]]] = {}
    plan_line_error: str | None = None
    if plan_stamps:
        try:
            plan_line_map = database.fetch_plan_lines_for_plans(plan_stamps)
        except RuntimeError as exc:
            plan_line_error = str(exc)
        else:
            plan_line_error = None
    if plan_line_error:
        db_error = f"{db_error}\n{plan_line_error}" if db_error else plan_line_error

    for assignments in assignments_map.values():
        for assignment in assignments:
            stamp = assignment.get("plan_stamp")
            lines = plan_line_map.get(stamp, []) if stamp else []
            assignment["plan_lines"] = lines
            assignment["has_lines"] = bool(assignment.get("has_lines")) or bool(lines)

    # Determine maintenance flags for projects within the selected week
    maintenance_rows: list[dict[str, object]] = []
    try:
        if project_opcstamps:
            maintenance_rows = database.fetch_maintenance_for_projects(week_start, week_end, project_opcstamps)
    except RuntimeError as exc:
        db_error = f"{db_error}\n{str(exc)}" if db_error else str(exc)
        maintenance_rows = []

    maintenance_opcstamps: set[str] = set()
    maintenance_intervals: dict[str, list[tuple[date, date | None]]] = {}
    for mrow in maintenance_rows:
        stamp = _coerce_text(mrow.get("opcstamp"))
        if not stamp:
            continue
        stamp = stamp.upper()
        maintenance_opcstamps.add(stamp)
        mi = _coerce_date(mrow.get("dataini"))
        mf = _coerce_date(mrow.get("datafim"))
        maintenance_intervals.setdefault(stamp, []).append((mi or date.min, mf))

    week_days = [week_start + timedelta(days=offset) for offset in range(7)]
    planning_rows = []
    for row in project_rows:
        project_code = _normalize_code(row.get("processo"))
        market = get_market(_normalize_code(row.get("u_origem")))
        project_start = _coerce_date(row.get("datai"))
        project_end = _coerce_date(row.get("dataf"))
        project_name = _coerce_text(row.get("nome")) or None
        project_description = _coerce_text(row.get("descricao")) or None
        opcstamp = _coerce_text(row.get("opcstamp"))
        has_maintenance = False
        if opcstamp and opcstamp.upper() in maintenance_opcstamps:
            has_maintenance = True
        # Determine if project qualifies by OPC overlap with the selected week
        qualifies_by_opc = _segments_overlap(project_start or date.min, project_end, week_start, week_end)
        # Apply type filter (obra/manutencao)
        include_project = True
        only_obra = ("obra" in selected_types) and ("manutencao" not in selected_types)
        only_manut = ("manutencao" in selected_types) and ("obra" not in selected_types)
        if only_obra:
            include_project = qualifies_by_opc
        elif only_manut:
            include_project = has_maintenance
        elif not selected_types:
            include_project = True
        # else both selected -> include both
        if not include_project:
            continue
        day_states = []
        for day in week_days:
            active = True
            if project_start and project_start > day:
                active = False
            if project_end and project_end < day:
                active = False
            if not active and opcstamp:
                intervals = maintenance_intervals.get(opcstamp.upper(), [])
                for (mi, mf) in intervals:
                    end_bound = mf or date.max
                    if mi <= day <= end_bound:
                        active = True
                        break
            day_states.append({
                "date": day,
                "active": active,
                "assignments": assignments_map.get((project_code, day), []),
            })
        planning_rows.append(
            {
                "code": project_code,
                "name": project_name,
                "description": project_description,
                "market": market,
                "shared_planning": _coerce_flag(row.get("u_planext")),
                "origin_raw": _coerce_text(row.get("u_origem")),
                "start": project_start,
                "end": project_end,
                "maintenance": has_maintenance,
                "days": day_states,
            }
        )

    planning_rows.sort(key=lambda row: (row.get("code") or "", row.get("name") or ""))

    planning_teams: list[dict[str, object]] = []
    team_group_filters = _user_team_group_filters(user)
    include_groups = team_group_filters["include"]
    exclude_groups = team_group_filters["exclude"]
    allow_all_groups = team_group_filters.get("allow_all", False)
    try:
        team_rows = database.fetch_planning_teams()
    except RuntimeError as exc:
        team_rows = []
        team_error = str(exc)
    else:
        team_error = None

    if team_error:
        db_error = f"{db_error}\n{team_error}" if db_error else team_error

    seen_team_codes: set[str] = set()
    for team_row in team_rows:
        code = _normalize_code(team_row.get("fref"))
        if not code or code in seen_team_codes:
            continue
        seen_team_codes.add(code)
        name = _coerce_text(team_row.get("nmfref"))
        group_label_raw = _coerce_text(team_row.get("planning"))
        if not group_label_raw and code.upper() in INTERSOL_TEAM_CODES:
            group_label_raw = "INTERSOL"
        group_key, group_label = _normalise_planning_group(group_label_raw)
        group_key_upper = group_key.upper()
        # Apply group filtering rules
        if group_key_upper not in include_groups:
            if exclude_groups and group_key_upper in exclude_groups:
                continue
            if not allow_all_groups and include_groups and group_key_upper not in include_groups:
                continue
        if not _planning_group_visible_for_selected_markets(group_key_upper, selected_market_codes):
            continue
        planning_teams.append(
            {
                "code": code,
                "name": name,
                "group_key": group_key,
                "group_label": group_label,
            }
        )

    planning_teams.sort(
        key=lambda team: (
            PLANNING_GROUP_ORDER.index(team["group_key"])
            if team["group_key"] in PLANNING_GROUP_ORDER
            else len(PLANNING_GROUP_ORDER),
            team.get("name") or team.get("code") or "",
        )
    )

    planning_team_groups: list[dict[str, object]] = []
    for team in planning_teams:
        if not planning_team_groups or planning_team_groups[-1]["key"] != team["group_key"]:
            planning_team_groups.append(
                {
                    "key": team["group_key"],
                    "label": team["group_label"],
                    "teams": [],
                }
            )
        planning_team_groups[-1]["teams"].append(team)

    return render_template(
        "index.html",
        user=user,
        db_error=db_error,
        resolved_week=resolved_week,
        week_start=week_start,
        week_end=week_end,
        week_days=week_days,
        planning_rows=planning_rows,
        available_markets=available_markets,
        selected_market_codes=selected_market_codes,
        planning_teams=planning_teams,
        planning_team_groups=planning_team_groups,
        planning_group_order=list(PLANNING_GROUP_ORDER),
        selected_types=selected_types,
        translations=translations,
    )


@app.route("/api/planning-teams")
def api_planning_teams():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    user = session.get("user") or {}
    available_markets = list_markets()
    allowed_market_codes = _user_allowed_market_codes(user, available_markets)
    selected_market_codes = request.args.getlist("markets")
    if not selected_market_codes:
        selected_market_codes = list(allowed_market_codes)
    else:
        selected_market_codes = [code for code in selected_market_codes if code in allowed_market_codes]
        if not selected_market_codes:
            selected_market_codes = list(allowed_market_codes)

    try:
        team_rows = database.fetch_planning_teams()
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    planning_teams: list[dict[str, object]] = []
    team_group_filters = _user_team_group_filters(user)
    include_groups = team_group_filters["include"]
    exclude_groups = team_group_filters["exclude"]
    allow_all_groups = team_group_filters.get("allow_all", False)
    seen_team_codes: set[str] = set()
    for team_row in team_rows:
        code = _normalize_code(team_row.get("fref"))
        if not code or code in seen_team_codes:
            continue
        seen_team_codes.add(code)
        name = _coerce_text(team_row.get("nmfref"))
        group_label_raw = _coerce_text(team_row.get("planning"))
        if not group_label_raw and code.upper() in INTERSOL_TEAM_CODES:
            group_label_raw = "INTERSOL"
        group_key, group_label = _normalise_planning_group(group_label_raw)
        group_key_upper = group_key.upper()
        if group_key_upper not in include_groups:
            if exclude_groups and group_key_upper in exclude_groups:
                continue
            if not allow_all_groups and include_groups and group_key_upper not in include_groups:
                continue
        if not _planning_group_visible_for_selected_markets(group_key_upper, selected_market_codes):
            continue
        planning_teams.append(
            {
                "code": code,
                "name": name,
                "group_key": group_key,
                "group_label": group_label,
            }
        )

    planning_teams.sort(
        key=lambda team: (
            PLANNING_GROUP_ORDER.index(team["group_key"])
            if team["group_key"] in PLANNING_GROUP_ORDER
            else len(PLANNING_GROUP_ORDER),
            team.get("name") or team.get("code") or "",
        )
    )

    planning_team_groups: list[dict[str, object]] = []
    for team in planning_teams:
        if not planning_team_groups or planning_team_groups[-1]["key"] != team["group_key"]:
            planning_team_groups.append(
                {
                    "key": team["group_key"],
                    "label": team["group_label"],
                    "teams": [],
                }
            )
        planning_team_groups[-1]["teams"].append(team)

    return jsonify({"teams": planning_teams, "groups": planning_team_groups})


@app.route("/api/debug-user")
def api_debug_user():
    user = session.get("user")
    if not user:
        return jsonify({"error": "authentication_required"}), 401

    # Reload raw user row from SQL to mirror DB values
    try:
        db_user = database.fetch_user_by_code(user.get("usercode", ""))
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    # Compute allowed markets (based on session flags after coercion)
    available_markets = list_markets()
    allowed = _user_allowed_market_codes(user, available_markets)
    return jsonify({
        "session_user": user,
        "db_user": db_user,
        "allowed_market_codes": allowed,
        "available_markets": [market.code for market in available_markets],
    })


@app.route("/teams")
def team_management():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    if not _can_access_team_management(user):
        return redirect(url_for("index"))

    translations = g.translations

    date_param = request.args.get("date")
    reference_date = _coerce_date(date_param)
    if reference_date is None:
        reference_date = date.today()

    reference_value = reference_date.isoformat()
    reference_label = reference_date.strftime("%d/%m/%Y")

    week_start_date = reference_date - timedelta(days=reference_date.weekday())
    week_end_date = week_start_date + timedelta(days=6)

    try:
        team_rows = database.fetch_all_teams()
        member_rows = database.fetch_team_members_for_date(reference_date)
        unassigned_rows = database.fetch_unassigned_employees(reference_date)
        db_error = None
    except RuntimeError as exc:
        team_rows = []
        member_rows = []
        unassigned_rows = []
        db_error = str(exc)

    members_by_team: dict[str, list[dict[str, object]]] = {}
    for row in member_rows:
        team_code = _normalize_code(row.get("fref"))
        if not team_code:
            continue
        member_name = _coerce_text(row.get("nome"))
        if not member_name:
            member_name = _normalize_code(row.get("no"))
        start_date = _coerce_date(row.get("dataini"))
        end_date = _coerce_date(row.get("datafim"))
        if end_date == TEAM_END_SENTINEL:
            end_date = None
        member_record = {
            "number": _normalize_code(row.get("no")),
            "name": member_name,
            "origin": _normalize_code(row.get("origem")),
            "is_lead": bool(row.get("chefe")),
            "start": start_date,
            "end": end_date,
            "stamp": _coerce_text(row.get("u_teamstamp")),
            "team_stamp": _coerce_text(row.get("frefstamp")),
        }
        members_by_team.setdefault(team_code, []).append(member_record)

    for team_code, members in members_by_team.items():
        members.sort(key=lambda item: (not item["is_lead"], item["name"].lower() if item["name"] else "", item["number"]))

    group_map: dict[str, dict[str, object]] = {}
    for row in team_rows:
        team_code = _normalize_code(row.get("fref"))
        if not team_code:
            continue
        team_name = _coerce_text(row.get("nmfref")) or team_code
        raw_group = _coerce_text(row.get("u_planning"))
        order_key = raw_group.upper() if raw_group else ""
        group_id = order_key or "__none__"
        group_label = raw_group or translations.get("teams_group_uncategorised", "")
        group_entry = group_map.setdefault(group_id, {
            "key": order_key,
            "label": group_label,
            "teams": [],
        })
        group_entry["teams"].append({
            "code": team_code,
            "name": team_name,
            "stamp": _coerce_text(row.get("frefstamp")),
            "members": members_by_team.get(team_code, []),
        })

    def _group_sort_key(group: dict[str, object]) -> tuple[int, str]:
        key = str(group.get("key") or "")
        try:
            index = PLANNING_GROUP_ORDER.index(key) if key else len(PLANNING_GROUP_ORDER)
        except ValueError:
            index = len(PLANNING_GROUP_ORDER)
        label = str(group.get("label") or "")
        return (index, label.lower())

    team_groups = sorted(group_map.values(), key=_group_sort_key)
    for group in team_groups:
        group["teams"].sort(key=lambda team: team.get("code") or "")

    team_options: list[dict[str, str]] = []
    seen_team_codes: set[str] = set()
    for group in team_groups:
        for team in group["teams"]:
            code = team.get("code")
            if not code or code in seen_team_codes:
                continue
            seen_team_codes.add(code)
            team_options.append({
                "code": code,
                "name": team.get("name") or code,
                "stamp": team.get("stamp") or "",
            })

    unassigned_employees = []
    for row in unassigned_rows:
        number = _normalize_code(row.get("no"))
        name = _coerce_text(row.get("cval4"))
        if not number or not name:
            continue
        unassigned_employees.append({
            "number": number,
            "name": name,
            "origin": _normalize_code(row.get("bdados")),
        })
    unassigned_employees.sort(key=lambda employee: employee["name"].lower())

    return render_template("team_management.html",
                           user=user,
                           reference_date_value=reference_value,
                           reference_date_label=reference_label,
                           week_start_value=week_start_date.isoformat(),
                           week_end_value=week_end_date.isoformat(),
                           unassigned_employees=unassigned_employees,
                           team_groups=team_groups,
                           team_options=team_options,
                           db_error=db_error)


@app.route("/api/team-absences")
def list_team_absences():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    reference_date = _coerce_date(request.args.get("date"))
    if reference_date is None:
        reference_date = date.today()

    try:
        rows = database.fetch_absences_for_date(reference_date)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    serialised = [_serialize_absence_row(row, reference_date) for row in rows]
    return jsonify({"rows": serialised, "reference_date": reference_date.isoformat()})


@app.route("/api/team-absences", methods=["POST"])
def create_team_absence():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    employee_number = _normalize_code(payload.get("employee_number") or payload.get("no"))
    if not employee_number:
        return jsonify({"error": "missing_employee_number"}), 400

    employee_name = _coerce_text(payload.get("employee_name") or payload.get("nome"))
    if not employee_name:
        try:
            employee_row = database.fetch_employee_details(employee_number)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        employee_name = _coerce_text((employee_row or {}).get("cval4")) or employee_number

    start_date = _coerce_date(payload.get("start_date") or payload.get("dataini"))
    end_date = _coerce_date(payload.get("end_date") or payload.get("datafim"))
    obs_value = _coerce_text(payload.get("obs"))
    if start_date is None or end_date is None:
        return jsonify({"error": "missing_dates"}), 400
    if end_date < start_date:
        return jsonify({"error": "invalid_date_range"}), 400

    now = datetime.now()
    user_code = _coerce_text((user or {}).get("usercode")) or _coerce_text((user or {}).get("username")) or "WEB"
    absence_stamp = uuid4().hex.upper()[:25]
    record = {
        "u_ausenciasstamp": absence_stamp,
        "no": employee_number,
        "nome": employee_name,
        "dataini": start_date,
        "datafim": end_date,
        "obs": obs_value,
        "ousrinis": user_code,
        "ousrdata": now,
        "ousrhora": now.strftime("%H:%M:%S"),
        "usrinis": user_code,
        "usrdata": now,
        "usrhora": now.strftime("%H:%M:%S"),
        "marcada": 1 if _coerce_flag(payload.get("marcada")) else 0,
    }
    try:
        database.insert_absence(record)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({"status": "created", "row": _serialize_absence_row(record, start_date)}), 201


@app.route("/api/team-absences/<absence_stamp>", methods=["PUT"])
def update_team_absence(absence_stamp: str):
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(absence_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_u_ausenciasstamp"}), 400

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    employee_number = _normalize_code(payload.get("employee_number") or payload.get("no"))
    if not employee_number:
        return jsonify({"error": "missing_employee_number"}), 400

    employee_name = _coerce_text(payload.get("employee_name") or payload.get("nome"))
    if not employee_name:
        try:
            current_row = database.fetch_absence_by_stamp(normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if current_row is None:
            return jsonify({"error": "not_found"}), 404
        employee_name = _coerce_text(current_row.get("nome")) or employee_number

    start_date = _coerce_date(payload.get("start_date") or payload.get("dataini"))
    end_date = _coerce_date(payload.get("end_date") or payload.get("datafim"))
    obs_value = _coerce_text(payload.get("obs"))
    if start_date is None or end_date is None:
        return jsonify({"error": "missing_dates"}), 400
    if end_date < start_date:
        return jsonify({"error": "invalid_date_range"}), 400

    now = datetime.now()
    user_code = _coerce_text((user or {}).get("usercode")) or _coerce_text((user or {}).get("username")) or "WEB"
    updates = {
        "no": employee_number,
        "nome": employee_name,
        "dataini": start_date,
        "datafim": end_date,
        "obs": obs_value,
        "usrinis": user_code,
        "usrdata": now,
        "usrhora": now.strftime("%H:%M:%S"),
        "marcada": 1 if _coerce_flag(payload.get("marcada")) else 0,
    }
    try:
        updated = database.update_absence(normalized_stamp, updates)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not updated:
        return jsonify({"error": "not_found"}), 404

    response_row = {"u_ausenciasstamp": normalized_stamp, **updates}
    return jsonify({"status": "updated", "row": _serialize_absence_row(response_row, start_date)})


@app.route("/api/team-absences/<absence_stamp>", methods=["DELETE"])
def delete_team_absence(absence_stamp: str):
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(absence_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_u_ausenciasstamp"}), 400

    try:
        deleted = database.delete_absence(normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not deleted:
        return jsonify({"error": "not_found"}), 404

    return jsonify({"status": "deleted", "u_ausenciasstamp": normalized_stamp})


@app.route("/api/team-intersol-roles")
def list_team_intersol_roles():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    try:
        employees = database.fetch_employees_basic()
        roles = database.fetch_intersol_roles()
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    employee_name_lookup = _build_employee_name_lookup(employees)
    rows = [_serialize_intersol_role_row(row, employee_name_lookup) for row in roles]
    rows.sort(key=lambda row: ((row.get("employee_name") or "").lower(), row.get("employee_number") or ""))
    return jsonify({"rows": rows})


@app.route("/api/team-intersol-roles", methods=["POST"])
def save_team_intersol_role():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    employee_number_text = _normalize_code(payload.get("employee_number") or payload.get("no"))
    employee_number = _coerce_int(employee_number_text)
    if employee_number is None:
        return jsonify({"error": "missing_employee_number"}), 400

    role_value = _coerce_text(payload.get("role")).upper()
    if role_value not in VALID_INTERSOL_ROLES:
        return jsonify({"error": "invalid_role"}), 400

    employee_name = _coerce_text(payload.get("employee_name"))
    try:
        employees = database.fetch_employees_basic()
        current_roles = database.fetch_intersol_roles()
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    employee_name_lookup = _build_employee_name_lookup(employees)
    if not employee_name:
        employee_name = employee_name_lookup.get(employee_number_text, "") or employee_number_text

    current_by_number = {_normalize_code(row.get("no")): row for row in current_roles}
    if "is_depot_manager" in payload:
        is_depot_manager = _coerce_flag(payload.get("is_depot_manager"))
    else:
        is_depot_manager = _coerce_flag((current_by_number.get(employee_number_text) or {}).get("is_depot_manager"))

    try:
        database.upsert_intersol_role(employee_number, role_value, is_depot_manager)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    row = _serialize_intersol_role_row(
        {
            "no": employee_number_text,
            "employee_name": employee_name,
            "role": role_value,
            "is_depot_manager": is_depot_manager,
        },
        employee_name_lookup,
    )
    return jsonify({"status": "saved", "row": row})


@app.route("/api/team-intersol-roles/<employee_number>", methods=["DELETE"])
def delete_team_intersol_role(employee_number: str):
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    normalized_number = _normalize_code(employee_number)
    numeric_number = _coerce_int(normalized_number)
    if numeric_number is None:
        return jsonify({"error": "missing_employee_number"}), 400

    try:
        deleted = database.delete_intersol_role(numeric_number)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not deleted:
        return jsonify({"error": "not_found"}), 404

    return jsonify({"status": "deleted", "employee_number": normalized_number})


@app.route("/api/team-intersol-regularizations")
def list_team_intersol_regularizations():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    month_value = _coerce_text(request.args.get("month"))
    reference_date = _coerce_date(request.args.get("date"))
    if month_value:
        try:
            year, month = [int(part) for part in month_value.split("-")[:2]]
        except Exception:
            return jsonify({"error": "invalid_month"}), 400
    else:
        if reference_date is None:
            reference_date = date.today()
        year = reference_date.year
        month = reference_date.month

    try:
        rows = database.fetch_intersol_regularizations(year, month)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    serialized = [_serialize_intersol_regularization_row(row) for row in rows]
    return jsonify({"rows": serialized, "month": f"{year:04d}-{month:02d}"})


@app.route("/api/team-intersol-regularizations", methods=["POST"])
def create_team_intersol_regularization():
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    employee_number_text = _normalize_code(payload.get("employee_number") or payload.get("no"))
    employee_number = _coerce_int(employee_number_text)
    if employee_number is None:
        return jsonify({"error": "missing_employee_number"}), 400

    employee_name = _coerce_text(payload.get("employee_name") or payload.get("nome"))
    if not employee_name:
        try:
            employee_row = database.fetch_employee_details(employee_number_text)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        employee_name = _coerce_text((employee_row or {}).get("cval4")) or employee_number_text

    month_value = _coerce_text(payload.get("month"))
    try:
        year, month = [int(part) for part in month_value.split("-")[:2]]
    except Exception:
        return jsonify({"error": "invalid_month"}), 400
    if month < 1 or month > 12:
        return jsonify({"error": "invalid_month"}), 400

    value = _coerce_decimal(payload.get("value") or payload.get("valor"))
    if value is None:
        return jsonify({"error": "missing_value"}), 400
    obs_value = _coerce_text(payload.get("obs"))

    now = datetime.now()
    user_code = _coerce_text((user or {}).get("usercode")) or _coerce_text((user or {}).get("username")) or "WEB"
    regularization_stamp = uuid4().hex.upper()[:25]
    record = {
        "u_intersol_regularizacoesstamp": regularization_stamp,
        "ano": year,
        "mes": month,
        "no": employee_number,
        "nome": employee_name,
        "obs": obs_value,
        "valor": _quantize_money(value),
        "ousrinis": user_code,
        "ousrdata": now,
        "ousrhora": now.strftime("%H:%M:%S"),
        "usrinis": user_code,
        "usrdata": now,
        "usrhora": now.strftime("%H:%M:%S"),
    }
    try:
        database.insert_intersol_regularization(record)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({"status": "created", "row": _serialize_intersol_regularization_row(record)}), 201


@app.route("/api/team-intersol-regularizations/<regularization_stamp>", methods=["PUT"])
def update_team_intersol_regularization(regularization_stamp: str):
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(regularization_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_stamp"}), 400

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    employee_number_text = _normalize_code(payload.get("employee_number") or payload.get("no"))
    employee_number = _coerce_int(employee_number_text)
    if employee_number is None:
        return jsonify({"error": "missing_employee_number"}), 400

    employee_name = _coerce_text(payload.get("employee_name") or payload.get("nome"))
    if not employee_name:
        try:
            current_row = database.fetch_intersol_regularization_by_stamp(normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if current_row is None:
            return jsonify({"error": "not_found"}), 404
        employee_name = _coerce_text(current_row.get("nome")) or employee_number_text

    month_value = _coerce_text(payload.get("month"))
    try:
        year, month = [int(part) for part in month_value.split("-")[:2]]
    except Exception:
        return jsonify({"error": "invalid_month"}), 400
    if month < 1 or month > 12:
        return jsonify({"error": "invalid_month"}), 400

    value = _coerce_decimal(payload.get("value") or payload.get("valor"))
    if value is None:
        return jsonify({"error": "missing_value"}), 400

    now = datetime.now()
    user_code = _coerce_text((user or {}).get("usercode")) or _coerce_text((user or {}).get("username")) or "WEB"
    updates = {
        "ano": year,
        "mes": month,
        "no": employee_number,
        "nome": employee_name,
        "obs": _coerce_text(payload.get("obs")),
        "valor": _quantize_money(value),
        "usrinis": user_code,
        "usrdata": now,
        "usrhora": now.strftime("%H:%M:%S"),
    }
    try:
        updated = database.update_intersol_regularization(normalized_stamp, updates)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not updated:
        return jsonify({"error": "not_found"}), 404

    response_row = {"u_intersol_regularizacoesstamp": normalized_stamp, **updates}
    return jsonify({"status": "updated", "row": _serialize_intersol_regularization_row(response_row)})


@app.route("/api/team-intersol-regularizations/<regularization_stamp>", methods=["DELETE"])
def delete_team_intersol_regularization(regularization_stamp: str):
    user = session.get("user")
    if not _can_access_team_management(user):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(regularization_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_stamp"}), 400

    try:
        deleted = database.delete_intersol_regularization(normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not deleted:
        return jsonify({"error": "not_found"}), 404

    return jsonify({"status": "deleted", "u_intersol_regularizacoesstamp": normalized_stamp})


@app.route("/folha-mensal")
def folha_mensal():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    if not user.get("u_admin"):
        return redirect(url_for("index"))

    translations = g.translations
    month_param = request.args.get("month") or ""
    if not month_param:
        today = date.today()
        month_param = today.strftime("%Y-%m")

    try:
        year, month = [int(part) for part in month_param.split("-")[:2]]
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
    except Exception:
        month_start = date.today().replace(day=1)
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
        month_param = month_start.strftime("%Y-%m")

    monthly_error = None
    try:
        monthly_rows = database.fetch_monthly_production_rows(month_start, month_end)
    except RuntimeError as exc:
        monthly_rows = []
        monthly_error = str(exc)

    maintenance_map: dict[int, float] = {}
    try:
        maintenance_rows = database.fetch_maintenance_for_month(month_start.year, month_start.month)
        for mrow in maintenance_rows:
            num = _coerce_int(mrow.get("no"))
            val = _coerce_decimal(mrow.get("valor"))
            if num is None or val is None:
                continue
            maintenance_map[num] = float(val)
    except RuntimeError as exc:
        monthly_error = f"{monthly_error}\n{str(exc)}" if monthly_error else str(exc)

    # Build team options from all rows in the month (before filters are applied)
    team_options = []
    seen_team_codes: set[str] = set()
    for row in monthly_rows:
        code = _normalize_code(row.get("fref"))
        if not code or code in seen_team_codes:
            continue
        seen_team_codes.add(code)
        name = _coerce_text(row.get("fref_name")) or code
        team_options.append({"code": code, "name": name})
    team_options = sorted(team_options, key=lambda t: t.get("code") or "")

    selected_team_codes = request.args.getlist("teams")
    selected_team_codes = [_normalize_code(code) for code in selected_team_codes if _normalize_code(code)]
    prime_records = _build_intersol_prime_records(monthly_rows, selected_team_codes)
    if selected_team_codes:
        monthly_rows = [r for r in monthly_rows if _normalize_code(r.get("fref")) in selected_team_codes]

    summary: list[dict[str, object]] = []

    def key_for(row: dict[str, object]) -> tuple[str, str, str, str]:
        team_code = _normalize_code(row.get("fref")) or ""
        team_name = _coerce_text(row.get("fref_name")) or team_code
        employee_number = _normalize_code(row.get("no")) or ""
        employee_name = _coerce_text(row.get("nome")) or employee_number
        return (team_code, team_name, employee_number, employee_name)

    aggregates: dict[tuple[str, str, str, str], dict[str, object]] = {}

    for row in monthly_rows:
        team_code, team_name, employee_number, employee_name = key_for(row)
        entry = aggregates.setdefault(
            (team_code, team_name, employee_number, employee_name),
            {
                "team_code": team_code,
                "team_name": team_name,
                "employee_number": employee_number,
                "employee_name": employee_name,
                "m2_total": 0.0,
                "m2_pay": 0.0,
                "serragem_total": 0.0,
                "serragem_pay": 0.0,
                "kg_total": 0.0,
                "kg_pay": 0.0,
                "other_pay": 0.0,
                "maintenance": 80.0,
                "daily_pay": 0.0,
                "complement_pay": 0.0,
                "is_chief": False,
                "chief_pay": 0.0,
                "total_pay": 0.0,
            },
        )

        item_raw = _coerce_text(row.get("litem")) or ""
        item_code = item_raw.strip()
        aml_qtt = _coerce_decimal(row.get("aml_qtt")) or Decimal("0")
        aml_kg = _coerce_decimal(row.get("aml_kgferro")) or Decimal("0")
        aml_serragem = _coerce_decimal(row.get("aml_m2serragem")) or Decimal("0")
        unit_price = _coerce_decimal(row.get("epv5")) or Decimal("0")
        is_chief = bool(row.get("chefe"))
        maintenance_val = 80.0
        employee_number_int = _coerce_int(employee_number)
        if employee_number_int is not None:
            if employee_number_int in maintenance_map:
                maintenance_val = maintenance_map[employee_number_int]
            else:
                try:
                    database.insert_maintenance_record(employee_number_int, employee_name or employee_number, month_start.year, month_start.month, 80.0)
                    maintenance_map[employee_number_int] = 80.0
                except RuntimeError as exc:
                    monthly_error = f"{monthly_error}\n{str(exc)}" if monthly_error else str(exc)

        if item_code == "999" or item_code == "997":
            entry["other_pay"] += 150.0
        elif item_code == "980" or item_code == "990":
            entry["other_pay"] += 80.0
        elif item_code == "996":
            kg_val = float(aml_kg)
            entry["kg_total"] += kg_val
            entry["kg_pay"] += kg_val * 0.065
        else:
            try:
                item_num = int(item_code) if item_code else 0
            except ValueError:
                item_num = 0
            if item_num < 900:
                production_pay = 0.0
                daily_component = 80.0
                entry["daily_pay"] += daily_component
                m2_val = float(aml_qtt)
                if m2_val > 0:
                    entry["m2_total"] += m2_val
                    m2_component = float(unit_price) * m2_val
                    entry["m2_pay"] += m2_component
                    production_pay += m2_component
                kg_val = float(aml_kg)
                if kg_val > 0:
                    entry["kg_total"] += kg_val
                    kg_component = kg_val * 0.075
                    entry["kg_pay"] += kg_component
                    production_pay += kg_component
                serragem_val = float(aml_serragem)
                if serragem_val > 0:
                    entry["serragem_total"] += serragem_val
                    serragem_component = serragem_val * 0.15
                    entry["serragem_pay"] += serragem_component
                    production_pay += serragem_component
                daily_total = daily_component + production_pay
                if daily_total < 150.0:
                    entry["complement_pay"] += (150.0 - daily_total)

        if is_chief:
            entry["chief_pay"] = min(entry["chief_pay"] + 25.0, 500.0)
            entry["is_chief"] = True

        entry["maintenance"] = maintenance_val

        entry["total_pay"] = (
            entry["daily_pay"]
            + entry["m2_pay"]
            + entry["serragem_pay"]
            + entry["kg_pay"]
            + entry["other_pay"]
            + entry["complement_pay"]
            + entry["maintenance"]
            + entry["chief_pay"]
        )

    summary = list(aggregates.values())
    summary.sort(key=lambda x: (x["team_code"], 0 if x.get("is_chief") else 1, x["employee_name"].lower()))

    totals = {
        "team_code": translations.get("monthly_sheet_total", "Total"),
        "employee_name": "",
        "m2_total": sum(item["m2_total"] for item in summary),
        "m2_pay": sum(item["m2_pay"] for item in summary),
        "serragem_total": sum(item["serragem_total"] for item in summary),
        "serragem_pay": sum(item["serragem_pay"] for item in summary),
        "kg_total": sum(item["kg_total"] for item in summary),
        "kg_pay": sum(item["kg_pay"] for item in summary),
        "other_pay": sum(item["other_pay"] for item in summary),
        "daily_pay": sum(item.get("daily_pay", 0.0) for item in summary),
        "complement_pay": sum(item.get("complement_pay", 0.0) for item in summary),
        "maintenance": sum(item.get("maintenance", 0.0) for item in summary),
        "chief_pay": sum(item.get("chief_pay", 0.0) for item in summary),
        "total_pay": sum(item.get("total_pay", 0.0) for item in summary),
    }
    return render_template(
        "folha_mensal.html",
        user=user,
        selected_month=month_param,
        month_label=month_start.strftime("%m/%Y") if month_param else "",
        monthly_error=monthly_error,
        monthly_summary=summary,
        monthly_totals=totals,
        team_options=team_options,
        selected_team_codes=selected_team_codes,
        selected_year=month_start.year,
        selected_month_number=month_start.month,
        t=translations,
    )


@app.route("/intersol/folha-mensal")
@app.route("/folha-mensal-intersol")
def folha_mensal_intersol():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    if not user.get("u_adminis"):
        return redirect(url_for("index"))

    translations = g.translations
    month_param, selected_month_start, period_start, period_end, selected_month_label, period_label = _resolve_intersol_period(
        request.args.get("month")
    )

    monthly_error = None
    try:
        monthly_rows = database.fetch_monthly_production_rows(period_start, period_end)
    except RuntimeError as exc:
        monthly_rows = []
        monthly_error = str(exc)
    absence_lookup: dict[str, dict[object, list[tuple[date, date]]]] = {"by_name": {}, "by_identity": {}}
    try:
        absence_rows = database.fetch_absences_for_date(period_start)
        absence_lookup = _build_absence_lookup(absence_rows)
    except RuntimeError as exc:
        monthly_error = f"{monthly_error}\n{str(exc)}" if monthly_error else str(exc)

    team_options = []
    seen_team_codes: set[str] = set()
    for row in monthly_rows:
        code = _normalize_code(row.get("fref"))
        if not code or code in seen_team_codes:
            continue
        seen_team_codes.add(code)
        name = _coerce_text(row.get("fref_name")) or code
        team_options.append({"code": code, "name": name})
    team_options = sorted(team_options, key=lambda t: t.get("code") or "")

    selected_team_codes = request.args.getlist("teams")
    selected_team_codes = [_normalize_code(code) for code in selected_team_codes if _normalize_code(code)]
    prime_records = _build_intersol_prime_records(monthly_rows, selected_team_codes)

    roles_by_employee: dict[str, str] = {}
    depot_manager_numbers: set[str] = set()
    try:
        role_rows = database.fetch_intersol_roles()
        for rrow in role_rows:
            num = _normalize_code(rrow.get("no"))
            role_val = _coerce_text(rrow.get("role")).upper()
            if not num or not role_val:
                continue
            if role_val not in VALID_INTERSOL_ROLES:
                role_val = ROLE_POLISSEUR
            roles_by_employee[num] = role_val
            if _coerce_flag(rrow.get("is_depot_manager")):
                depot_manager_numbers.add(num)
    except RuntimeError as exc:
        monthly_error = f"{monthly_error}\n{str(exc)}" if monthly_error else str(exc)

    tasks, role_hints = _build_intersol_tasks(monthly_rows, selected_team_codes)
    _apply_intersol_role_hints(roles_by_employee, role_hints)

    monthly_summary, monthly_totals = compute_monthly_sheet(
        tasks,
        month_start=period_start,
        month_end=period_end,
        roles_by_employee=roles_by_employee,
        depot_manager_numbers=depot_manager_numbers,
    )
    serialized_summary = [
        _serialize_intersol_summary_row(row, selected_month_start, absence_lookup)
        for row in monthly_summary
    ]
    serialized_totals = _serialize_intersol_totals(monthly_totals, serialized_summary)

    return render_template(
        "folha_mensal_intersol.html",
        user=user,
        selected_month=month_param,
        month_label=selected_month_label,
        period_label=period_label,
        monthly_error=monthly_error,
        monthly_summary=serialized_summary,
        monthly_totals=serialized_totals,
        prime_records=prime_records,
        can_manage_primes=bool(user.get("u_admin")),
        team_options=team_options,
        selected_team_codes=selected_team_codes,
        selected_year=selected_month_start.year,
        selected_month_number=selected_month_start.month,
        t=translations,
    )


@app.route("/api/intersol/monthly-export")
def intersol_monthly_export():
    user = session.get("user")
    if not user or not user.get("u_adminis"):
        return jsonify({"error": "authentication_required"}), 401

    try:
        _, selected_month_start, period_start, period_end, _, _ = _resolve_intersol_period(
            request.args.get("month"),
            strict=True,
        )
    except ValueError:
        return jsonify({"error": "invalid_params"}), 400

    try:
        monthly_rows = database.fetch_monthly_production_rows(period_start, period_end)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    try:
        absence_rows = database.fetch_absences_for_date(period_start)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    absence_lookup = _build_absence_lookup(absence_rows)
    try:
        regularization_rows = database.fetch_intersol_regularizations(
            selected_month_start.year,
            selected_month_start.month,
        )
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    regularization_lookup = _build_intersol_regularization_lookup(regularization_rows)

    selected_team_codes = request.args.getlist("teams")
    selected_team_codes = [_normalize_code(code) for code in selected_team_codes if _normalize_code(code)]

    roles_by_employee: dict[str, str] = {}
    depot_manager_numbers: set[str] = set()
    try:
        role_rows = database.fetch_intersol_roles()
        for rrow in role_rows:
            num = _normalize_code(rrow.get("no"))
            role_val = _coerce_text(rrow.get("role")).upper()
            if not num or not role_val:
                continue
            if role_val not in VALID_INTERSOL_ROLES:
                role_val = ROLE_POLISSEUR
            roles_by_employee[num] = role_val
            if _coerce_flag(rrow.get("is_depot_manager")):
                depot_manager_numbers.add(num)
    except RuntimeError:
        pass

    tasks, role_hints = _build_intersol_tasks(monthly_rows, selected_team_codes)
    _apply_intersol_role_hints(roles_by_employee, role_hints)

    monthly_summary, monthly_totals = compute_monthly_sheet(
        tasks,
        month_start=period_start,
        month_end=period_end,
        roles_by_employee=roles_by_employee,
        depot_manager_numbers=depot_manager_numbers,
    )
    serialized_summary = [
        _serialize_intersol_summary_row(row, selected_month_start, absence_lookup)
        for row in monthly_summary
    ]
    serialized_totals = _serialize_intersol_totals(monthly_totals, serialized_summary)

    headers = [
        "Equipa",
        "Colaborador",
        "Dias trab.",
        "Dias uteis",
        "M2 finitions",
        "Total finitions EUR",
        "M2 scie",
        "Total scie EUR",
        "Kg ferro",
        "Total ferro EUR",
        "Prime chantier",
        "Prime chef",
        "Prime depot",
        "Prime d'effort",
        "Intemperies",
        "Compl. minimo",
        "Panier",
        "GD",
        "Z1",
        "Z2",
        "Z3",
        "Z4",
        "Z5",
        "TOTAL EUR",
    ]

    rows: list[list[object]] = []
    for row in serialized_summary:
        rows.append([
            row["team_code"],
            row["employee_name"],
            row["worked_days"],
            row["business_days"],
            row["m2_total"],
            row["finitions_pay"],
            row["scie_total_m2"],
            row["scie_pay"],
            row["kg_total"],
            row["kg_pay"],
            row["prime_multiple"],
            row["prime_chef"],
            row["prime_depot"],
            row["prime_effort"],
            row["intemperies_total"],
            row["complement_minimum"],
            row["panier_repas"],
            row["grand_deplacement"],
            row["zone_counts"].get("z1", 0),
            row["zone_counts"].get("z2", 0),
            row["zone_counts"].get("z3", 0),
            row["zone_counts"].get("z4", 0),
            row["zone_counts"].get("z5", 0),
            row["total"],
        ])

    rows.append([
        serialized_totals.get("team_code", "Total"),
        "Total",
        serialized_totals.get("worked_days", 0),
        serialized_totals.get("business_days", 0),
        serialized_totals.get("m2_total", 0),
        serialized_totals.get("finitions_pay", 0),
        serialized_totals.get("scie_total", 0),
        serialized_totals.get("scie_pay", 0),
        serialized_totals.get("kg_total", 0),
        serialized_totals.get("kg_pay", 0),
        serialized_totals.get("prime_multiple", 0),
        serialized_totals.get("prime_chef", 0),
        serialized_totals.get("prime_depot", 0),
        serialized_totals.get("prime_effort", 0),
        serialized_totals.get("intemperies_total", 0),
        serialized_totals.get("complement_minimum", 0),
        serialized_totals.get("panier_repas", 0),
        serialized_totals.get("gd", 0),
        serialized_totals.get("z1", 0),
        serialized_totals.get("z2", 0),
        serialized_totals.get("z3", 0),
        serialized_totals.get("z4", 0),
        serialized_totals.get("z5", 0),
        serialized_totals.get("total", 0),
    ])

    sheets: list[dict[str, object]] = [
        {
            "name": f"Intersol {selected_month_start.strftime('%Y-%m')}",
            "headers": headers,
            "rows": rows,
        }
    ]

    detail_headers = [
        "Data",
        "Chantier",
        "Acabamento",
        "M2",
        "M2 total chantier",
        "Valor finitions",
        "M2 scie",
        "Valor scie",
        "Kg",
        "Valor kg",
        "Prime chantier",
        "Base/forfait",
        "Pago",
        "Total dia",
    ]

    for employee in monthly_summary:
        detail_rows: list[list[object]] = []
        absence_intervals = _get_employee_absence_intervals(absence_lookup, employee.employee_number, employee.employee_name)
        serialized_rows, paid_total, display_total_sum = _serialize_intersol_detail_rows(
            employee.daily_breakdown,
            selected_month_start,
            absence_intervals=absence_intervals,
            role=employee.role,
        )
        employee_regularizations = regularization_lookup.get(
            (
                _normalize_code(employee.employee_number),
                _normalize_person_name(employee.employee_name),
            ),
            [],
        )
        serialized_regularizations, regularizations_total = _serialize_intersol_regularization_rows(
            employee_regularizations,
            selected_month_start,
        )
        for item in serialized_rows:
            base_label = f"{float(item['base_value'] or 0):.2f}"
            detail_rows.append(
                [
                    item["date"],
                    item["chantier"],
                    item["finish_type"],
                    item["m2"],
                    item["chantier_total_m2"],
                    item["finitions_value"],
                    item["m2_scie"],
                    item["scie_value"],
                    item["kg"],
                    item["steel_value"],
                    item["prime_multiple"],
                    base_label,
                    item["paid_value"],
                    item["display_total"],
                ]
            )
        for item in serialized_regularizations:
            detail_rows.append(
                [
                    item["date"],
                    item["chantier"],
                    item["finish_type"],
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    item["display_total"],
                ]
            )

        detail_rows.append(
            [
                "TOTAL",
                "",
                "",
                employee.m2_total,
                "",
                employee.finitions_pay,
                employee.scie_total_m2,
                employee.scie_pay,
                employee.kg_total,
                employee.kg_pay,
                employee.prime_multiple,
                "",
                float(paid_total),
                float(_quantize_money(display_total_sum + regularizations_total)),
            ]
        )

        sheets.append(
            {
                "name": employee.employee_number or employee.employee_name or "Funcionario",
                "headers": detail_headers,
                "rows": detail_rows,
            }
        )

    xlsx_data = _build_simple_xlsx_workbook(sheets)
    filename = f"mapa-mensal-intersol-{selected_month_start.strftime('%Y-%m')}.xlsx"
    return send_file(
        BytesIO(xlsx_data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/monthly-detail")
def monthly_detail():
    user = session.get("user")
    if not user or not user.get("u_admin"):
        return jsonify({"error": "authentication_required"}), 401

    year = _coerce_int(request.args.get("year"))
    month = _coerce_int(request.args.get("month"))
    employee_number = _coerce_int(request.args.get("employee_number"))
    if year is None or month is None or employee_number is None:
        return jsonify({"error": "invalid_params"}), 400
    try:
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
    except Exception:
        return jsonify({"error": "invalid_params"}), 400

    try:
        rows = database.fetch_monthly_production_rows(month_start, month_end)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    rows = [r for r in rows if _coerce_int(r.get("no")) == employee_number]
    maintenance_map = {}
    try:
        maintenance_rows = database.fetch_maintenance_for_month(year, month)
        for mrow in maintenance_rows:
            num = _coerce_int(mrow.get("no"))
            val = _coerce_decimal(mrow.get("valor"))
            if num is None or val is None:
                continue
            maintenance_map[num] = float(val)
    except RuntimeError:
        maintenance_map = {}

    details = []
    totals = {"m2": 0.0, "m2_pay": 0.0, "serragem": 0.0, "serragem_pay": 0.0, "kg": 0.0, "kg_pay": 0.0, "daily": 0.0, "other": 0.0, "complement": 0.0, "chief": 0.0, "maintenance": 0.0, "total": 0.0}

    for r in rows:
        item_code = (_coerce_text(r.get("litem")) or "").strip()
        aml_qtt = _coerce_decimal(r.get("aml_qtt")) or Decimal("0")
        aml_kg = _coerce_decimal(r.get("aml_kgferro")) or Decimal("0")
        aml_serragem = _coerce_decimal(r.get("aml_m2serragem")) or Decimal("0")
        unit_price = _coerce_decimal(r.get("epv5")) or Decimal("0")
        is_chief = bool(r.get("chefe"))
        maintenance_val = maintenance_map.get(employee_number, 80.0)

        daily_component = 0.0
        m2_pay = kg_pay = serr_pay = other_pay = complement = 0.0
        m2_val = float(aml_qtt)
        kg_val = float(aml_kg)
        serr_val = float(aml_serragem)

        if item_code in {"999", "997"}:
            other_pay += 150.0
        elif item_code in {"980", "990"}:
            other_pay += 80.0
        elif item_code == "996":
            kg_pay += kg_val * 0.065
        else:
            try:
                item_num = int(item_code) if item_code else 0
            except ValueError:
                item_num = 0
            if item_num < 900:
                daily_component += 80.0
                if m2_val > 0:
                    m2_pay += float(unit_price) * m2_val
                if kg_val > 0:
                    kg_pay += kg_val * 0.075
                if serr_val > 0:
                    serr_pay += serr_val * 0.15
                prod_total = daily_component + m2_pay + kg_pay + serr_pay
                if prod_total < 150.0:
                    complement += (150.0 - prod_total)

        day_total = daily_component + m2_pay + kg_pay + serr_pay + other_pay + complement + maintenance_val
        if is_chief:
            day_total += 25.0
            totals["chief"] += 25.0

        details.append({
            "date": r.get("data").strftime("%Y-%m-%d") if hasattr(r.get("data"), "strftime") else r.get("data"),
            "project": _coerce_text(r.get("processo")) or "",
            "item": item_code,
            "acabamento": _coerce_text(r.get("acabamento")) or "",
            "m2": m2_val,
            "m2_pay": m2_pay,
            "serragem": serr_val,
            "serragem_pay": serr_pay,
            "kg": kg_val,
            "kg_pay": kg_pay,
            "daily": daily_component,
            "other": other_pay,
            "complement": complement,
            "maintenance": maintenance_val,
            "chief": 25.0 if is_chief else 0.0,
            "total": day_total
        })

        totals["m2"] += m2_val
        totals["m2_pay"] += m2_pay
        totals["serragem"] += serr_val
        totals["serragem_pay"] += serr_pay
        totals["kg"] += kg_val
        totals["kg_pay"] += kg_pay
        totals["daily"] += daily_component
        totals["other"] += other_pay
        totals["complement"] += complement
        totals["maintenance"] += maintenance_val
        totals["total"] += day_total

    details.sort(key=lambda d: d.get("date") or "")
    return jsonify({"rows": details, "totals": totals})


@app.route("/api/intersol/monthly-detail")
def intersol_monthly_detail():
    user = session.get("user")
    if not user or not user.get("u_adminis"):
        return jsonify({"error": "authentication_required"}), 401

    year = _coerce_int(request.args.get("year"))
    month = _coerce_int(request.args.get("month"))
    employee_number = _normalize_code(request.args.get("employee_number"))
    if year is None or month is None or not employee_number:
        return jsonify({"error": "invalid_params"}), 400
    month_param = f"{year:04d}-{month:02d}"
    try:
        _, selected_month_start, period_start, period_end, _, _ = _resolve_intersol_period(month_param, strict=True)
    except ValueError:
        return jsonify({"error": "invalid_params"}), 400

    try:
        monthly_rows = database.fetch_monthly_production_rows(period_start, period_end)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    try:
        absence_rows = database.fetch_absences_for_date(period_start)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    absence_lookup = _build_absence_lookup(absence_rows)

    roles_by_employee: dict[str, str] = {}
    depot_manager_numbers: set[str] = set()
    try:
        role_rows = database.fetch_intersol_roles()
        for rrow in role_rows:
            num = _normalize_code(rrow.get("no"))
            role_val = _coerce_text(rrow.get("role")).upper()
            if not num or not role_val:
                continue
            if role_val not in VALID_INTERSOL_ROLES:
                role_val = ROLE_POLISSEUR
            roles_by_employee[num] = role_val
            if _coerce_flag(rrow.get("is_depot_manager")):
                depot_manager_numbers.add(num)
    except RuntimeError:
        pass

    tasks, role_hints = _build_intersol_tasks(monthly_rows)
    _apply_intersol_role_hints(roles_by_employee, role_hints)

    monthly_summary, _ = compute_monthly_sheet(
        tasks,
        month_start=period_start,
        month_end=period_end,
        roles_by_employee=roles_by_employee,
        depot_manager_numbers=depot_manager_numbers,
    )

    target = next((row for row in monthly_summary if _normalize_code(row.employee_number) == employee_number), None)
    if not target:
        return jsonify({"error": "not_found"}), 404

    absence_intervals = _get_employee_absence_intervals(absence_lookup, target.employee_number, target.employee_name)
    detail_rows, paid_total, display_total_sum = _serialize_intersol_detail_rows(
        target.daily_breakdown,
        selected_month_start,
        absence_intervals=absence_intervals,
        role=target.role,
    )
    try:
        regularization_rows = database.fetch_intersol_regularizations(
            selected_month_start.year,
            selected_month_start.month,
            employee_number=target.employee_number,
            employee_name=target.employee_name,
        )
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    serialized_regularizations, regularizations_total = _serialize_intersol_regularization_rows(
        regularization_rows,
        selected_month_start,
    )
    if serialized_regularizations:
        detail_rows.extend(serialized_regularizations)
        display_total_sum = _quantize_money(display_total_sum + regularizations_total)

    totals = {
        "m2": target.m2_total,
        "finitions_pay": target.finitions_pay,
        "scie_m2": target.scie_total_m2,
        "scie_pay": target.scie_pay,
        "kg": target.kg_total,
        "kg_pay": target.kg_pay,
        "prime_multiple": target.prime_multiple,
        "prime_chef": target.prime_chef,
        "prime_depot": target.prime_depot,
        "prime_effort": target.prime_effort,
        "prime_effort_validated": target.prime_effort_validated,
        "prime_effort_pending": target.prime_effort_pending,
        "intemperies_total": target.intemperies_total,
        "complement_minimum": target.complement_minimum,
        "worked_days": target.worked_days,
        "business_days": target.business_days,
        "panier_repas": _compute_intersol_panier_repas(detail_rows, selected_month_start),
        "gd": target.grand_deplacement,
        "zones": target.zone_counts,
        "regularizations_total": float(regularizations_total),
        "paid_total": float(paid_total),
        "gross_total": target.total,
        "total": float(display_total_sum),
        "role": target.role,
    }
    return jsonify({"rows": detail_rows, "totals": totals})


@app.route("/api/intersol/prime-records/<line_stamp>/validation", methods=["POST"])
def intersol_prime_record_validation(line_stamp: str):
    user = session.get("user")
    if not user or not user.get("u_admin"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(line_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_u_amlstamp"}), 400

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    month_param = _coerce_text(payload.get("month"))
    try:
        _, selected_month_start, period_start, period_end, _, _ = _resolve_intersol_period(month_param, strict=True)
    except ValueError:
        return jsonify({"error": "invalid_month"}), 400

    raw_teams = payload.get("teams") or []
    if isinstance(raw_teams, (str, int)):
        raw_teams = [raw_teams]
    if not isinstance(raw_teams, list):
        return jsonify({"error": "invalid_teams"}), 400
    selected_team_codes = [_normalize_code(code) for code in raw_teams if _normalize_code(code)]

    validated = 1 if _coerce_flag(payload.get("validated")) else 0
    try:
        updated = database.update_production_line({"validprime": validated}, am_line_stamp=normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not updated:
        return jsonify({"error": "not_found"}), 404

    try:
        monthly_rows = database.fetch_monthly_production_rows(period_start, period_end)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    try:
        absence_rows = database.fetch_absences_for_date(period_start)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    absence_lookup = _build_absence_lookup(absence_rows)

    roles_by_employee: dict[str, str] = {}
    depot_manager_numbers: set[str] = set()
    try:
        role_rows = database.fetch_intersol_roles()
        for rrow in role_rows:
            num = _normalize_code(rrow.get("no"))
            role_val = _coerce_text(rrow.get("role")).upper()
            if not num or not role_val:
                continue
            if role_val not in VALID_INTERSOL_ROLES:
                role_val = ROLE_POLISSEUR
            roles_by_employee[num] = role_val
            if _coerce_flag(rrow.get("is_depot_manager")):
                depot_manager_numbers.add(num)
    except RuntimeError:
        pass

    tasks, role_hints = _build_intersol_tasks(monthly_rows, selected_team_codes)
    _apply_intersol_role_hints(roles_by_employee, role_hints)
    monthly_summary, monthly_totals = compute_monthly_sheet(
        tasks,
        month_start=period_start,
        month_end=period_end,
        roles_by_employee=roles_by_employee,
        depot_manager_numbers=depot_manager_numbers,
    )

    prime_records = _build_intersol_prime_records(monthly_rows, selected_team_codes)
    line_record = next((record for record in prime_records if record.get("u_amlstamp") == normalized_stamp), None)
    if line_record is None:
        fallback_row = next(
            (
                row
                for row in monthly_rows
                if _normalize_code(row.get("u_amlstamp")) == normalized_stamp
            ),
            None,
        )
        line_record = {
            "u_amlstamp": normalized_stamp,
            "validated": bool(validated),
            "employee_number": _normalize_code(fallback_row.get("no")) if fallback_row else "",
            "prime": float(_quantize_money(_coerce_decimal((fallback_row or {}).get("aml_prime")) or Decimal("0"))),
        }

    employee_number = _normalize_code(line_record.get("employee_number"))
    employee_summary = next(
        (row for row in monthly_summary if _normalize_code(row.employee_number) == employee_number),
        None,
    )

    serialized_summary = [
        _serialize_intersol_summary_row(row, selected_month_start, absence_lookup)
        for row in monthly_summary
    ]
    serialized_totals = _serialize_intersol_totals(monthly_totals, serialized_summary)
    serialized_employee = next(
        (
            row
            for row in serialized_summary
            if _normalize_code(row.get("employee_number")) == employee_number
        ),
        None,
    )

    return jsonify(
        {
            "status": "updated",
            "line": line_record,
            "employee": serialized_employee,
            "totals": serialized_totals,
        }
    )

@app.route("/api/maintenance", methods=["POST"])
def update_maintenance():
    user = session.get("user")
    if not user or not user.get("u_admin"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    year = _coerce_int(payload.get("year"))
    month = _coerce_int(payload.get("month"))
    items = payload.get("items")
    if year is None or month is None or not isinstance(items, list):
        return jsonify({"error": "invalid_payload"}), 400

    updated = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        num = _coerce_int(item.get("employee_number"))
        name = _coerce_text(item.get("employee_name")) or ""
        val = _coerce_decimal(item.get("value"))
        if num is None or val is None:
            continue
        try:
            val = val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            continue
        try:
            affected = database.update_maintenance_record(num, year, month, val)
            if affected == 0:
                database.insert_maintenance_record(num, name, year, month, val)
            updated += 1
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({"status": "ok", "updated": updated})


@app.route("/api/team-memberships", methods=["POST"])
def manage_team_memberships():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    action = _coerce_text(payload.get("action")).lower()
    if action not in {"assign", "transfer", "remove", "lead"}:
        return jsonify({"error": "invalid_action"}), 400

    employee_number = _normalize_code(payload.get("employee_number"))
    if not employee_number:
        return jsonify({"error": "missing_employee_number"}), 400
    employee_origin = _normalize_code(payload.get("employee_origin"))

    reference_date = _coerce_date(payload.get("reference_date"))
    if reference_date is None:
        reference_date = date.today()

    period_type = _coerce_text(payload.get("period_type")).lower() or "reference"
    try:
        start_date, end_date = _resolve_team_period(
            reference_date,
            period_type,
            payload.get("custom_start"),
            payload.get("custom_end"),
            payload.get("specific_date"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    make_lead = bool(payload.get("make_lead"))
    target_team_code = _normalize_code(payload.get("target_team"))

    # Fetch membership rows first; some employees may not exist in v_pe
    # (e.g., different origin/database or archived) but still have u_team records.
    try:
        membership_rows = database.fetch_employee_memberships(employee_number, employee_origin)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    # Try to fetch basic employee details; for remove/transfer we can proceed
    # even if this lookup fails, using membership data as fallback.
    try:
        employee_row = database.fetch_employee_details(employee_number, employee_origin)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    employee_name = _coerce_text(employee_row.get("cval4")) if employee_row else ""
    if employee_row:
        db_origin = _normalize_code(employee_row.get("bdados"))
        if db_origin:
            employee_origin = db_origin
    if not employee_name:
        employee_name = employee_number

    membership_records: list[dict[str, object]] = []
    for row in membership_rows:
        start_value = _coerce_date(row.get("dataini"))
        end_value = _coerce_date(row.get("datafim"))
        if start_value is None:
            continue
        if end_value == TEAM_END_SENTINEL:
            end_value = None
        membership_records.append({
            "stamp": _coerce_text(row.get("u_teamstamp")),
            "team_code": _normalize_code(row.get("fref")),
            "team_stamp": _coerce_text(row.get("frefstamp")),
            "number": employee_number,
            "name": _coerce_text(row.get("nome")) or employee_name,
            "origin": _coerce_text(row.get("origem")) or employee_origin,
            "is_lead": bool(row.get("chefe")),
            "start": start_value,
            "end": end_value,
        })

    membership_records.sort(key=lambda item: item["start"])
    current_record = _find_membership_covering(membership_records, start_date)

    effective_action = action
    if action == "lead":
        make_lead = True
        if current_record is None:
            effective_action = "assign"
        else:
            effective_action = "transfer"

    operations: list[dict[str, object]] = []

    def _fetch_team_or_error(team_code: str):
        try:
            return database.fetch_team_by_code(team_code)
        except RuntimeError as exc:
            raise RuntimeError(str(exc))

    if effective_action == "assign":
        # For new assignments we require employee details to exist in v_pe
        if not employee_row:
            return jsonify({"error": "employee_not_found"}), 404
        if not target_team_code:
            return jsonify({"error": "missing_target_team"}), 400
        try:
            team_row = _fetch_team_or_error(target_team_code)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if not team_row:
            return jsonify({"error": "team_not_found"}), 404
        target_code = _normalize_code(team_row.get("fref"))
        team_stamp = _coerce_text(team_row.get("frefstamp"))
        if not target_code or not team_stamp:
            return jsonify({"error": "team_incomplete"}), 500
        overlap_exists = any(
            _segments_overlap(record["start"], record.get("end"), start_date, end_date)
            for record in membership_records
        )
        if overlap_exists:
            return jsonify({"error": "employee_already_assigned"}), 409
        operations.append(
            _make_insert_operation(
                target_code,
                team_stamp,
                employee_number,
                employee_name,
                employee_origin,
                start_date,
                end_date,
                chefe=make_lead,
            )
        )
        if make_lead:
            try:
                operations.extend(_plan_lead_demotion(target_code, start_date, end_date, employee_number))
            except RuntimeError as exc:
                return jsonify({"error": "database_error", "details": str(exc)}), 500

    elif effective_action == "remove":
        if current_record is None:
            return jsonify({"error": "employee_not_assigned"}), 400
        # For removal, close the current membership by setting datafim to the chosen date
        # when a specific date is selected (or to end_date if provided).
        end_at = end_date or start_date
        operations.append({
            "type": "update_period",
            "stamp": current_record["stamp"],
            "start": current_record["start"],
            "end": end_at,
        })

    elif effective_action == "transfer":
        if current_record is None:
            return jsonify({"error": "employee_not_assigned"}), 400
        original_team_code = current_record.get("team_code")
        if not target_team_code:
            if action == "lead" and isinstance(original_team_code, str):
                target_team_code = original_team_code
            else:
                return jsonify({"error": "missing_target_team"}), 400
        try:
            team_row = _fetch_team_or_error(target_team_code)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if not team_row:
            return jsonify({"error": "team_not_found"}), 404
        target_code = _normalize_code(team_row.get("fref"))
        team_stamp = _coerce_text(team_row.get("frefstamp"))
        if not target_code or not team_stamp:
            return jsonify({"error": "team_incomplete"}), 500
        if target_code == original_team_code and not make_lead:
            return jsonify({"error": "no_team_change"}), 400
        split_ops, trailing_record = _plan_membership_split(current_record, start_date, end_date)
        operations.extend(split_ops)
        if trailing_record is not None:
            operations.append(_membership_insert_from_record(trailing_record))
        origin_value = current_record.get("origin") or employee_origin
        operations.append(
            _make_insert_operation(
                target_code,
                team_stamp,
                employee_number,
                employee_name,
                origin_value,
                start_date,
                end_date,
                chefe=make_lead,
            )
        )
        if make_lead:
            try:
                operations.extend(_plan_lead_demotion(target_code, start_date, end_date, employee_number))
            except RuntimeError as exc:
                return jsonify({"error": "database_error", "details": str(exc)}), 500

    else:
        return jsonify({"error": "invalid_action"}), 400

    if not operations:
        return jsonify({"error": "no_operations_generated"}), 400

    try:
        database.apply_team_membership_operations(operations)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({"status": "ok", "operations": len(operations)})




@app.route("/api/employees")
def list_employees():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401
    try:
        rows = database.fetch_employees_basic()
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    return jsonify(rows)


@app.route("/api/production-finitions")
def list_production_finitions():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401
    try:
        rows = database.fetch_finishing_refs()
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    return jsonify(rows)


@app.route("/api/plans", methods=["POST"])
def create_plan():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    def _payload_first(keys: tuple[str, ...]) -> object | None:
        for key in keys:
            if key in payload:
                return payload.get(key)
        return None

    raw_stamp = _payload_first(("u_planostamp", "stamp"))
    plano_stamp = (_coerce_text(raw_stamp) or uuid4().hex).upper()[:25]
    raw_date = payload.get("data") or payload.get("date")
    assignment_date = _coerce_date(raw_date)
    if assignment_date is None:
        return jsonify({"error": "invalid_date"}), 400

    team_code = _normalize_code(payload.get("fref"))
    if not team_code:
        return jsonify({"error": "missing_fref"}), 400

    project_code = _normalize_code(payload.get("processo"))
    if not project_code:
        return jsonify({"error": "missing_processo"}), 400

    fixed_raw = _payload_first(("fixo", "fixed", "fixed_value", "fixedValue"))
    bonus_raw = _payload_first(("premio", "bonus", "bonus_value", "bonusValue"))

    fixed_value = _coerce_decimal(fixed_raw) if fixed_raw is not None else Decimal("0")
    if fixed_value is None:
        return jsonify({"error": "invalid_fixo"}), 400
    bonus_value = _coerce_decimal(bonus_raw) if bonus_raw is not None else Decimal("0")
    if bonus_value is None:
        return jsonify({"error": "invalid_premio"}), 400

    try:
        fixed_value = fixed_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        bonus_value = bonus_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return jsonify({"error": "invalid_values"}), 400

    try:
        database.insert_planning_assignment(plano_stamp, assignment_date, team_code, project_code, fixed_value, bonus_value)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({
        "u_planostamp": plano_stamp,
        "data": assignment_date.isoformat(),
        "fref": team_code,
        "processo": project_code,
        "fixo": float(fixed_value),
        "premio": float(bonus_value),
        "rep": 0,
    }), 201


@app.route("/api/plans/<plan_stamp>", methods=["GET", "PUT"])
def plan_details(plan_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(plan_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "missing_u_planostamp"}), 400

    if request.method == "GET":
        try:
            plan_row = database.fetch_plan_by_stamp(normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if not plan_row:
            return jsonify({"error": "not_found"}), 404
        def _json_value(value: object) -> object:
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            return value
        return jsonify({key: _json_value(value) for key, value in plan_row.items()})

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    def _payload_first(keys: tuple[str, ...]) -> object | None:
        for key in keys:
            if key in payload:
                return payload.get(key)
        return None

    fixed_raw = _payload_first(("fixo", "fixed", "fixed_value", "fixedValue"))
    bonus_raw = _payload_first(("premio", "bonus", "bonus_value", "bonusValue"))
    if fixed_raw is None and bonus_raw is None:
        return jsonify({"error": "missing_values"}), 400

    fixed_value = None
    bonus_value = None
    if fixed_raw is not None:
        fixed_value = _coerce_decimal(fixed_raw)
        if fixed_value is None:
            return jsonify({"error": "invalid_fixo"}), 400
        try:
            fixed_value = fixed_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return jsonify({"error": "invalid_fixo"}), 400

    if bonus_raw is not None:
        bonus_value = _coerce_decimal(bonus_raw)
        if bonus_value is None:
            return jsonify({"error": "invalid_premio"}), 400
        try:
            bonus_value = bonus_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return jsonify({"error": "invalid_premio"}), 400

    try:
        updated = database.update_plan_values(normalized_stamp, fixed_value=fixed_value, bonus_value=bonus_value)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not updated:
        # Allow upsert if we have enough context
        raw_date = payload.get("data") or payload.get("date")
        raw_team = payload.get("fref") or payload.get("team_code") or payload.get("teamCode")
        raw_project = payload.get("processo") or payload.get("project_code") or payload.get("projectCode")
        assignment_date = _coerce_date(raw_date)
        if assignment_date is None:
            return jsonify({"error": "invalid_date"}), 400
        team_code = _normalize_code(raw_team)
        if not team_code:
            return jsonify({"error": "missing_fref"}), 400
        project_code = _normalize_code(raw_project)
        if not project_code:
            return jsonify({"error": "missing_processo"}), 400
        try:
            database.insert_planning_assignment(
                normalized_stamp,
                assignment_date,
                team_code,
                project_code,
                fixed_value,
                bonus_value,
            )
            updated = 1
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({
        "u_planostamp": normalized_stamp,
        "fixo": float(fixed_value) if fixed_value is not None else None,
        "premio": float(bonus_value) if bonus_value is not None else None,
    })


@app.route("/api/plans/<plan_stamp>/values", methods=["PATCH", "PUT"])
def plan_values(plan_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(plan_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "missing_u_planostamp"}), 400

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    def _payload_first(keys: tuple[str, ...]) -> object | None:
        for key in keys:
            if key in payload:
                return payload.get(key)
        return None

    fixed_raw = _payload_first(("fixo", "fixed", "fixed_value", "fixedValue"))
    bonus_raw = _payload_first(("premio", "bonus", "bonus_value", "bonusValue"))
    if fixed_raw is None and bonus_raw is None:
        return jsonify({"error": "missing_values"}), 400

    fixed_value = None
    bonus_value = None
    if fixed_raw is not None:
        fixed_value = _coerce_decimal(fixed_raw)
        if fixed_value is None:
            return jsonify({"error": "invalid_fixo"}), 400
        try:
            fixed_value = fixed_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return jsonify({"error": "invalid_fixo"}), 400

    if bonus_raw is not None:
        bonus_value = _coerce_decimal(bonus_raw)
        if bonus_value is None:
            return jsonify({"error": "invalid_premio"}), 400
        try:
            bonus_value = bonus_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return jsonify({"error": "invalid_premio"}), 400

    try:
        updated = database.update_plan_values(normalized_stamp, fixed_value=fixed_value, bonus_value=bonus_value)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500
    if not updated:
        return jsonify({"error": "not_found"}), 404

    return jsonify({
        "u_planostamp": normalized_stamp,
        "fixo": float(fixed_value) if fixed_value is not None else None,
        "premio": float(bonus_value) if bonus_value is not None else None,
    })

@app.route("/api/plan-lines", methods=["POST"])
def create_plan_line():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    raw_plan_stamp = payload.get("u_planostamp") or payload.get("plan_stamp") or payload.get("planStamp")
    plan_stamp = _coerce_text(raw_plan_stamp).upper()[:25]
    if not plan_stamp:
        return jsonify({"error": "missing_u_planostamp"}), 400

    bi_stamp = _coerce_text(payload.get("bistamp") or payload.get("bi_stamp") or payload.get("biStamp"))
    if not bi_stamp:
        return jsonify({"error": "missing_bistamp"}), 400

    line_item_raw = payload.get("litem")
    if line_item_raw is None:
        line_item_raw = payload.get("line_item") or payload.get("lineItem")
    line_item = _coerce_int(line_item_raw)
    if line_item is None:
        return jsonify({"error": "invalid_litem"}), 400

    description = _coerce_text(payload.get("dgeral") or payload.get("description"))
    if not description:
        return jsonify({"error": "missing_dgeral"}), 400

    team_code = _normalize_code(payload.get("fref") or payload.get("team_code") or payload.get("teamCode"))
    if not team_code:
        return jsonify({"error": "missing_fref"}), 400

    project_code = _normalize_code(payload.get("processo") or payload.get("project_code") or payload.get("projectCode"))
    if not project_code:
        return jsonify({"error": "missing_processo"}), 400

    assignment_date = _coerce_date(payload.get("data") or payload.get("date"))
    if assignment_date is None:
        return jsonify({"error": "invalid_date"}), 400

    fixed_raw = payload.get("fixo")
    if fixed_raw is None:
        fixed_raw = payload.get("fixed") or payload.get("fixed_value") or payload.get("fixedValue")

    fixed_value = _coerce_decimal(fixed_raw)
    if fixed_value is None:
        return jsonify({"error": "invalid_fixo"}), 400

    try:
        fixed_value = fixed_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return jsonify({"error": "invalid_fixo"}), 400

    try:
        line_stamp = database.insert_plan_line(
            plan_stamp,
            bi_stamp,
            line_item,
            description,
            team_code,
            project_code,
            assignment_date,
            fixed_value,
        )
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({
        "u_lplanostamp": line_stamp,
        "u_planostamp": plan_stamp,
        "bistamp": bi_stamp,
        "litem": line_item,
        "dgeral": description,
        "fref": team_code,
        "processo": project_code,
        "data": assignment_date.isoformat(),
        "fixo": float(fixed_value),
    }), 201


@app.route("/api/plan-lines/<line_stamp>", methods=["DELETE"])
def delete_plan_line(line_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(line_stamp)
    if not normalized_stamp:
        return jsonify({"error": "missing_u_lplanostamp"}), 400

    try:
        database.delete_plan_line(normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return ("", 204)

@app.route("/api/plans/<plan_stamp>/plan-lines")
def list_plan_lines(plan_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(plan_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify([])

    try:
        lines = database.fetch_plan_lines(normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    def _json_value(value: object) -> object:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    serialised = [{key: _json_value(value) for key, value in line.items()} for line in lines]
    return jsonify(serialised)

@app.route("/api/production-records/<am_stamp>", methods=["PUT"])
def update_production_record_handler(am_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(am_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_am_stamp"}), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    updates: dict[str, object] = {}
    field_errors: dict[str, str] = {}

    if "fref" in payload:
        raw_fref = payload.get("fref")
        code_value = _normalize_code(raw_fref)
        if code_value:
            updates["fref"] = code_value
        elif raw_fref in (None, "", b""):
            updates["fref"] = ''
        else:
            field_errors["fref"] = "invalid"

    if "processo" in payload:
        raw_project = payload.get("processo")
        project_value = _normalize_code(raw_project)
        if project_value:
            updates["processo"] = project_value
        elif raw_project in (None, "", b""):
            updates["processo"] = ''
        else:
            field_errors["processo"] = "invalid"

    if "data" in payload:
        raw_date = payload.get("data")
        if raw_date in (None, ""):
            updates["data"] = None
        else:
            coerced_date = _coerce_date(raw_date)
            if coerced_date is None:
                field_errors["data"] = "invalid"
            else:
                updates["data"] = coerced_date

    if "litem" in payload:
        raw_litem = payload.get("litem")
        if raw_litem in (None, ""):
            updates["litem"] = None
        else:
            coerced_litem = _coerce_int(raw_litem)
            if coerced_litem is None:
                field_errors["litem"] = "invalid"
            else:
                updates["litem"] = coerced_litem

    if "dgeral" in payload:
        updates["dgeral"] = _coerce_text(payload.get("dgeral"))
    if "acabamento" in payload:
        raw_finish = payload.get("acabamento")
        if raw_finish in (None, "", b""):
            updates["acabamento"] = None
        else:
            finish_value = _normalize_code(raw_finish)
            if finish_value:
                updates["acabamento"] = finish_value
            else:
                field_errors["acabamento"] = "invalid"
    if "fechado" in payload:
        raw_closed = payload.get("fechado")
        closed_val = None
        if isinstance(raw_closed, bool):
            closed_val = 1 if raw_closed else 0
        elif isinstance(raw_closed, (int, float)):
            closed_val = 1 if int(raw_closed) != 0 else 0
        elif isinstance(raw_closed, str):
            closed_val = 1 if raw_closed.strip().lower() in ("1", "true", "on", "yes") else 0
        if closed_val is not None:
            updates["fechado"] = closed_val


    decimal_fields = ("qtt", "kgferro", "m2serragem", "m3bomba", "m3betao")
    for field in decimal_fields:
        if field not in payload:
            continue
        raw_value = payload.get(field)
        if raw_value in (None, "", b""):
            updates[field] = None
            continue
        coerced_decimal = _coerce_decimal(raw_value)
        if coerced_decimal is None:
            field_errors[field] = "invalid"
        else:
            updates[field] = coerced_decimal

        # New u_aml lines to insert
    new_lines = payload.get("new_lines") or payload.get("newLines")
    new_line_specs: list[dict[str, object]] = []
    quantize_three = Decimal('0.001')
    quantize_two = Decimal('0.01')
    if new_lines is not None:
        if not isinstance(new_lines, list):
            return jsonify({"error": "invalid_new_lines"}), 400
        for idx, item in enumerate(new_lines):
            if not isinstance(item, dict):
                field_errors.setdefault("new_lines", "invalid")
                continue
            no_val = item.get('no')
            nome_val = item.get('nome')
            if no_val in (None, "") or nome_val in (None, ""):
                # require both
                continue
            new_line_specs.append({
                'no': str(no_val).strip(),
                'nome': str(nome_val).strip(),
                'qtt': (_coerce_decimal(item.get('qtt') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP),
                'kgferro': (_coerce_decimal(item.get('kgferro') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP),
                'm2serragem': (_coerce_decimal(item.get('m2serragem') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP),
                'u_prime': (_coerce_decimal(item.get('u_prime') or item.get('prime') or 0) or Decimal("0")).quantize(quantize_two, rounding=ROUND_HALF_UP),
            })

    line_updates: list[tuple[str, dict[str, object]]] = []
    line_field_errors: dict[int, dict[str, str]] = {}
    raw_lines = payload.get("lines")
    if raw_lines is not None:
        if not isinstance(raw_lines, list):
            return jsonify({"error": "invalid_lines"}), 400
        for index, raw_line in enumerate(raw_lines):
            if not isinstance(raw_line, dict):
                line_field_errors[index] = {'_': 'invalid'}
                continue
            raw_stamp = raw_line.get('u_amlstamp') or raw_line.get('uAmlstamp') or raw_line.get('line_stamp')
            stamp_text = _coerce_text(raw_stamp)
            stamp = stamp_text.upper()[:25] if stamp_text else ''
            if not stamp:
                line_field_errors.setdefault(index, {})['u_amlstamp'] = 'missing'
                continue
            line_values: dict[str, object] = {}
            for field in ("qtt", "kgferro", "m2serragem", "u_prime"):
                if field not in raw_line:
                    continue
                raw_line_value = raw_line.get(field)
                if raw_line_value in (None, "", b""):
                    line_values[field] = None
                    continue
                coerced_line_decimal = _coerce_decimal(raw_line_value)
                if coerced_line_decimal is None:
                    line_field_errors.setdefault(index, {})[field] = 'invalid'
                    continue
                quantize_target = quantize_two if field == "u_prime" else quantize_three
                line_values[field] = coerced_line_decimal.quantize(quantize_target, rounding=ROUND_HALF_UP)
            if line_values:
                line_updates.append((stamp, line_values))

    if field_errors or line_field_errors:
        response: dict[str, object] = {"error": "invalid_fields"}
        if field_errors:
            response["fields"] = field_errors
        if line_field_errors:
            response["line_fields"] = line_field_errors
        return jsonify(response), 400

    if not updates and not line_updates and not new_line_specs:
        return jsonify({"error": "no_updates"}), 400

    record_snapshot: dict[str, object] | None = None
    if updates:
        try:
            updated = database.update_production_record(updates, am_stamp=normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500

        if not updated:
            return jsonify({"error": "not_found"}), 404
    else:
        try:
            existing_records = database.fetch_production_records(am_stamp=normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500

        if not existing_records:
            return jsonify({"error": "not_found"}), 404

        record_snapshot = existing_records[0]

    
    # Insert new u_aml lines if requested
    if new_line_specs:
        # Ensure we have parent record data
        parent_record = None
        try:
            parent_rows = database.fetch_production_records(am_stamp=normalized_stamp)
            parent_record = parent_rows[0] if parent_rows else None
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500
        if not parent_record:
            return jsonify({"error": "not_found"}), 404
        # Defaults
        from datetime import datetime as _dt
        now = _dt.now()
        def _stamp():
            return uuid4().hex.upper()[:25]
        base = {
            'u_amstamp': normalized_stamp,
            'fref': parent_record.get('fref') or '',
            'processo': parent_record.get('processo') or '',
            'data': parent_record.get('data') or now,
            'litem': parent_record.get('litem') or '',
            'falta': '',
            'preparacao': 0,
            'preprep': 0,
            'ousrinis': (session.get('user') or {}).get('usercode', 'WEB'),
            'ousrdata': now,
            'ousrhora': now.strftime('%H:%M:%S'),
            'usrinis': (session.get('user') or {}).get('usercode', 'WEB'),
            'usrdata': now,
            'usrhora': now.strftime('%H:%M:%S'),
            'marcada': 0,
            'outros': '',
            'presente': 0,
            'disponivel': 1,
        }
        for spec in new_line_specs:
            record = dict(base)
            record['u_amlstamp'] = _stamp()
            record['no'] = int(_coerce_int(spec.get('no')) or 0)
            record['nome'] = spec.get('nome') or ''
            record['qtt'] = (_coerce_decimal(spec.get('qtt') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP)
            record['kgferro'] = (_coerce_decimal(spec.get('kgferro') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP)
            record['m2serragem'] = (_coerce_decimal(spec.get('m2serragem') or 0) or Decimal("0")).quantize(quantize_three, rounding=ROUND_HALF_UP)
            record['u_prime'] = (_coerce_decimal(spec.get('u_prime') or spec.get('prime') or 0) or Decimal("0")).quantize(quantize_two, rounding=ROUND_HALF_UP)
            try:
                database.insert_production_line(record)
            except RuntimeError as exc:
                return jsonify({"error": "database_error", "details": str(exc)}), 500

    if line_updates:
        line_not_found: list[str] = []
        for stamp, line_values in line_updates:
            try:
                line_updated = database.update_production_line(line_values, am_line_stamp=stamp)
            except RuntimeError as exc:
                return jsonify({"error": "database_error", "details": str(exc)}), 500

            if not line_updated:
                line_not_found.append(stamp)

        if line_not_found:
            return jsonify({"error": "line_not_found", "lines": line_not_found}), 404

    if record_snapshot is None:
        try:
            refreshed = database.fetch_production_records(am_stamp=normalized_stamp)
        except RuntimeError as exc:
            return jsonify({"error": "database_error", "details": str(exc)}), 500

        record: dict[str, object] | None
        if refreshed:
            record = refreshed[0]
        else:
            record = None
    else:
        record = record_snapshot

    if record is None:
        return jsonify({"status": "updated"}), 200

    def _json_value(value: object) -> object:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    serialised = {key: _json_value(value) for key, value in record.items()}
    return jsonify(serialised)


@app.route("/api/plans/<plan_stamp>/production-records")
def list_production_records(plan_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(plan_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify([])

    try:
        records = database.fetch_production_records(plan_stamp=normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    def _json_value(value: object) -> object:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    serialised = [{key: _json_value(value) for key, value in record.items()} for record in records]
    return jsonify(serialised)


@app.route("/api/production/close-week", methods=["POST"])
def close_production_week():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True) or {}
    week_start = _coerce_date(payload.get("week_start"))
    week_end = _coerce_date(payload.get("week_end"))
    if week_start is None or week_end is None:
        return jsonify({"error": "invalid_week_range"}), 400
    if week_end < week_start:
        week_start, week_end = week_end, week_start

    try:
        closed_count, plan_stamps = database.close_fulfilled_production_records(week_start, week_end)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return jsonify({"status": "ok", "closed": closed_count, "plans": plan_stamps})


@app.route("/api/production-records/<am_stamp>/lines")
def list_production_record_lines(am_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(am_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify([])

    try:
        lines = database.fetch_production_line_records(am_stamp=normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    def _json_value(value: object) -> object:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    serialised = [{key: _json_value(value) for key, value in line.items()} for line in lines]
    return jsonify(serialised)


@app.route("/api/production-lines/<line_stamp>", methods=["DELETE"])
def delete_production_line_handler(line_stamp: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_stamp = _coerce_text(line_stamp).upper()[:25]
    if not normalized_stamp:
        return jsonify({"error": "invalid_u_amlstamp"}), 400

    try:
        deleted = database.delete_production_line(am_line_stamp=normalized_stamp)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    if not deleted:
        return jsonify({"error": "not_found"}), 404

    return ("", 204)


@app.route("/api/plans", methods=["DELETE"])
def delete_plan():
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload"}), 400

    raw_date = payload.get("data") or payload.get("date")
    assignment_date = _coerce_date(raw_date)
    if assignment_date is None:
        return jsonify({"error": "invalid_date"}), 400

    team_code = _normalize_code(payload.get("fref"))
    if not team_code:
        return jsonify({"error": "missing_fref"}), 400

    project_code = _normalize_code(payload.get("processo"))
    if not project_code:
        return jsonify({"error": "missing_processo"}), 400

    try:
        database.delete_planning_assignment(assignment_date, team_code, project_code)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    return ("", 204)


@app.route("/api/projects/<project_code>/budget-items")
def project_budget_items(project_code: str):
    if not session.get("user"):
        return jsonify({"error": "authentication_required"}), 401

    normalized_code = _normalize_code(project_code)
    if not normalized_code:
        return jsonify([])

    try:
        items = database.fetch_project_budget_items(normalized_code)
    except RuntimeError as exc:
        return jsonify({"error": "database_error", "details": str(exc)}), 500

    def _coerce_value(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    serialised = []
    for item in items:
        serialised.append({key: _coerce_value(value) for key, value in item.items()})

    return jsonify(serialised)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
