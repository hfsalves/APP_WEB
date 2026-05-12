from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import unicodedata
import uuid

from flask import Blueprint, Response, abort, jsonify, render_template, request, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import bindparam, text

from models import Acessos, db

from .service import (
    LEGACY_SCRIPT_FILES,
    LEGACY_STATIC_DIR,
    MONTHLY_SHEET_SCRIPT_FILES,
    MONTHLY_SHEET_INTERSOL_SCRIPT_FILES,
    build_planning_page,
    build_monthly_sheet_page,
    build_monthly_sheet_intersol_page,
    build_team_management_page,
    can_access_monitor,
    can_access_monthly_sheet,
    can_access_monthly_sheet_intersol,
    can_access_planning,
    can_access_team_management,
    fetch_gr_task_status_options,
    fetch_gr_monitor_tasks,
    get_api_access_scope,
    open_legacy_request,
    _parse_date_param,
    update_gr_task_status,
    TEAM_MANAGEMENT_SCRIPT_FILES,
)


bp = Blueprint(
    "gr_planning",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/gr_planning/static",
)


def _current_login_value() -> str:
    return (getattr(current_user, "LOGIN", "") or "").strip()


def _ensure_planning_access() -> dict:
    allowed, legacy_user = can_access_planning(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_team_management_access() -> dict:
    allowed, legacy_user = can_access_team_management(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monthly_sheet_access() -> dict:
    allowed, legacy_user = can_access_monthly_sheet(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monthly_sheet_intersol_access() -> dict:
    allowed, legacy_user = can_access_monthly_sheet_intersol(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monitor_access() -> dict:
    if _has_app_task_access("consultar"):
        return {}
    allowed, legacy_user = can_access_monitor(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monitor_edit_access() -> dict:
    if _has_app_task_access("editar"):
        return {}
    allowed, legacy_user = can_access_monitor(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _has_app_task_access(action: str = "consultar") -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    login = _current_login_value()
    if not login:
        return False
    row = Acessos.query.filter_by(utilizador=login, tabela="TAREFAS").first()
    return bool(row and getattr(row, action, False))


def _monitor_user_filter() -> str | None:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return None
    return _current_login_value()


def _parse_year_param(raw_value: str | None) -> int:
    today_year = date.today().year
    try:
        year = int(str(raw_value or today_year).strip())
    except (TypeError, ValueError):
        return today_year
    return max(2000, min(2099, year))


def _new_stamp_25() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _table_columns(table_name: str) -> set[str]:
    return {
        str(row[0] or "").upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
        """), {"table_name": table_name}).fetchall()
    }


def _to_decimal(value, default: str = "0") -> Decimal:
    raw = str(value if value is not None else "").strip().replace(",", ".")
    if not raw:
        raw = default
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError("Valor numerico invalido.")


def _to_money_float(value) -> float:
    return float(value or 0)


def _parse_date_value(value) -> date:
    raw = str(value or "").strip()
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Data invalida.")


def _normalize_time_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return datetime.strptime(raw[:5], "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError("Hora invalida.")


def _ascii_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper().strip()


def _concrete_record_from_row(row) -> dict:
    return {
        "stamp": str(row.get("RCENTRALSTAMP") or "").strip(),
        "processo": str(row.get("PROCESSO") or "").strip(),
        "servico": str(row.get("SERVICO") or "").strip(),
        "motorista": str(row.get("MOTORISTA") or "").strip(),
        "matricula": str(row.get("MATRICULA") or "").strip(),
        "data": str(row.get("DATA") or "").strip(),
        "horaini": str(row.get("HORAINI") or "").strip(),
        "horafim": str(row.get("HORAFIM") or "").strip(),
        "descricao": str(row.get("DESCRICAO") or "").strip(),
        "qtt": _to_money_float(row.get("QTT")),
        "cinicial": _to_money_float(row.get("CINICIAL")),
        "cfinal": _to_money_float(row.get("CFINAL")),
        "areia": _to_money_float(row.get("AREIA")),
        "brita": _to_money_float(row.get("BRITA")),
        "cimento": _to_money_float(row.get("CIMENTO")),
        "aditivo": _to_money_float(row.get("ADITIVO")),
        "refbetao": str(row.get("REFBETAO") or "").strip(),
    }


def _fetch_concrete_record(stamp: str) -> dict | None:
    normalized = str(stamp or "").strip()[:25]
    if not normalized or not _macro_table_exists("RCENTRAL"):
        return None
    row = db.session.execute(text("""
        SELECT
            RCENTRALSTAMP,
            PROCESSO,
            SERVICO,
            MOTORISTA,
            MATRICULA,
            CONVERT(varchar(10), DATA, 23) AS DATA,
            HORAINI,
            HORAFIM,
            DESCRICAO,
            QTT,
            CINICIAL,
            CFINAL,
            AREIA,
            BRITA,
            CIMENTO,
            ADITIVO,
            REFBETAO
        FROM dbo.RCENTRAL
        WHERE RCENTRALSTAMP = :stamp
    """), {"stamp": normalized}).mappings().first()
    return _concrete_record_from_row(row) if row else None


def _fetch_concrete_records(day: date) -> list[dict]:
    if not _macro_table_exists("RCENTRAL"):
        return []
    rows = db.session.execute(text("""
        SELECT
            RCENTRALSTAMP,
            PROCESSO,
            SERVICO,
            MOTORISTA,
            MATRICULA,
            CONVERT(varchar(10), DATA, 23) AS DATA,
            HORAINI,
            HORAFIM,
            DESCRICAO,
            QTT,
            CINICIAL,
            CFINAL,
            AREIA,
            BRITA,
            CIMENTO,
            ADITIVO,
            REFBETAO
        FROM dbo.RCENTRAL
        WHERE CAST(DATA AS date) = :day
        ORDER BY DATA DESC, HORAINI DESC, RCENTRALSTAMP DESC
    """), {"day": day}).mappings().all()
    return [_concrete_record_from_row(row) for row in rows]


def _fetch_concrete_vehicles(term: str = "", limit: int = 80) -> list[dict]:
    cols = _table_columns("VA")
    if not cols or "MATRICULA" not in cols:
        return []
    central_col = "CENTRABETAO" if "CENTRABETAO" in cols else ("CENTRALBETAO" if "CENTRALBETAO" in cols else "")
    if not central_col:
        return []
    safe_limit = max(1, min(int(limit or 80), 150))
    query = f"%{str(term or '').strip()}%"
    rows = db.session.execute(text(f"""
        SELECT TOP ({safe_limit})
            LTRIM(RTRIM(ISNULL(CAST(MATRICULA AS varchar(50)), ''))) AS matricula,
            LTRIM(RTRIM(ISNULL(CAST(MARCA AS varchar(50)), ''))) AS marca,
            LTRIM(RTRIM(ISNULL(CAST(MODELO AS varchar(50)), ''))) AS modelo,
            LTRIM(RTRIM(ISNULL(CAST(NOFROTA AS varchar(50)), ''))) AS nofrota
        FROM dbo.VA
        WHERE ISNULL([{central_col}], 0) = 1
          AND ISNULL(INATIVO, 0) = 0
          AND (
              :query = '%%'
              OR CAST(MATRICULA AS varchar(50)) LIKE :query
              OR CAST(MARCA AS varchar(50)) LIKE :query
              OR CAST(MODELO AS varchar(50)) LIKE :query
              OR CAST(NOFROTA AS varchar(50)) LIKE :query
          )
        ORDER BY LTRIM(RTRIM(ISNULL(CAST(MATRICULA AS varchar(50)), '')))
    """), {"query": query}).mappings().all()
    return [
        {
            "matricula": str(row.get("matricula") or "").strip(),
            "label": " ".join(part for part in (
                str(row.get("matricula") or "").strip(),
                str(row.get("marca") or "").strip(),
                str(row.get("modelo") or "").strip(),
                str(row.get("nofrota") or "").strip(),
            ) if part),
        }
        for row in rows
        if str(row.get("matricula") or "").strip()
    ]


def _save_concrete_record(payload: dict) -> dict:
    if not _macro_table_exists("RCENTRAL"):
        raise ValueError("Tabela RCENTRAL inexistente.")
    stamp = str(payload.get("stamp") or payload.get("rcentralstamp") or "").strip()[:25]
    processo = str(payload.get("processo") or "").strip()[:25]
    servico_raw = str(payload.get("servico") or "").strip()
    servico_key = _ascii_key(servico_raw)
    motorista = str(payload.get("motorista") or "").strip()[:60]
    matricula = str(payload.get("matricula") or "").strip()[:50]
    data_value = _parse_date_value(payload.get("data"))
    horaini = _normalize_time_value(str(payload.get("horaini") or ""))
    horafim = _normalize_time_value(str(payload.get("horafim") or ""))
    descricao = str(payload.get("descricao") or "").strip()[:250]
    refbetao = str(payload.get("refbetao") or "").strip()[:254]
    cinicial = _to_decimal(payload.get("cinicial"))
    cfinal = _to_decimal(payload.get("cfinal"))
    qtt = cfinal - cinicial
    areia = _to_decimal(payload.get("areia"))
    brita = _to_decimal(payload.get("brita"))
    cimento = _to_decimal(payload.get("cimento"))
    aditivo = _to_decimal(payload.get("aditivo"))
    service_map = {
        "MANUTENCAO": "MANUTENÇÃO",
        "MONTAGEM": "MONTAGEM",
        "DESMONTAGEM": "DESMONTAGEM",
        "PRODUCAO": "PRODUÇÃO",
    }
    servico = service_map.get(servico_key, "")[:18]
    if not servico:
        raise ValueError("Servico invalido.")
    if not processo:
        raise ValueError("Obra obrigatoria.")
    if not matricula:
        raise ValueError("Central/matricula obrigatoria.")
    if not motorista:
        raise ValueError("Motorista obrigatorio.")
    if not horaini:
        raise ValueError("Hora inicial obrigatoria.")
    if qtt < 0:
        raise ValueError("Contador final nao pode ser inferior ao inicial.")

    params = {
        "stamp": stamp or _new_stamp_25(),
        "processo": processo,
        "servico": servico,
        "motorista": motorista,
        "matricula": matricula,
        "data": datetime.combine(data_value, datetime.min.time()),
        "horaini": horaini,
        "horafim": horafim,
        "descricao": descricao,
        "qtt": qtt,
        "cinicial": cinicial,
        "cfinal": cfinal,
        "areia": areia,
        "brita": brita,
        "cimento": cimento,
        "aditivo": aditivo,
        "refbetao": refbetao,
    }
    if stamp:
        result = db.session.execute(text("""
            UPDATE dbo.RCENTRAL
            SET PROCESSO=:processo,
                SERVICO=:servico,
                MOTORISTA=:motorista,
                MATRICULA=:matricula,
                DATA=:data,
                HORAINI=:horaini,
                HORAFIM=:horafim,
                DESCRICAO=:descricao,
                QTT=:qtt,
                CINICIAL=:cinicial,
                CFINAL=:cfinal,
                AREIA=:areia,
                BRITA=:brita,
                CIMENTO=:cimento,
                ADITIVO=:aditivo,
                REFBETAO=:refbetao
            WHERE RCENTRALSTAMP=:stamp
        """), params)
        if result.rowcount == 0:
            raise ValueError("Registo nao encontrado.")
    else:
        db.session.execute(text("""
            INSERT INTO dbo.RCENTRAL
                (RCENTRALSTAMP, PROCESSO, SERVICO, MOTORISTA, MATRICULA, DATA, HORAINI, HORAFIM,
                 DESCRICAO, QTT, CINICIAL, CFINAL, AREIA, BRITA, CIMENTO, ADITIVO, REFBETAO)
            VALUES
                (:stamp, :processo, :servico, :motorista, :matricula, :data, :horaini, :horafim,
                 :descricao, :qtt, :cinicial, :cfinal, :areia, :brita, :cimento, :aditivo, :refbetao)
        """), params)
    db.session.commit()
    return {"ok": True, "stamp": params["stamp"], "qtt": float(qtt)}


def _search_macro_opc_rows(term: str, limit: int = 60) -> list[dict]:
    query = f"%{(term or '').strip()}%"
    safe_limit = max(1, min(int(limit or 60), 100))
    rows = db.session.execute(text(f"""
        SELECT TOP ({safe_limit})
            LTRIM(RTRIM(ISNULL(CAST(PROCESSO AS nvarchar(120)), ''))) AS processo,
            LTRIM(RTRIM(ISNULL(CAST(DESCRICAO AS nvarchar(255)), ''))) AS descricao
        FROM dbo.OPC
        WHERE
            (:query = '%%'
             OR CAST(PROCESSO AS nvarchar(120)) LIKE :query
             OR CAST(DESCRICAO AS nvarchar(255)) LIKE :query)
        ORDER BY
            LTRIM(RTRIM(ISNULL(CAST(PROCESSO AS nvarchar(120)), ''))),
            LTRIM(RTRIM(ISNULL(CAST(DESCRICAO AS nvarchar(255)), '')))
    """), {"query": query}).mappings().all()
    return [
        {
            "processo": str(row.get("processo") or "").strip(),
            "descricao": str(row.get("descricao") or "").strip(),
        }
        for row in rows
        if str(row.get("processo") or "").strip()
    ]


def _search_macro_team_rows(term: str, limit: int = 60) -> list[dict]:
    table_columns = {
        str(row[0] or "").upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'FREF'
        """)).fetchall()
    }
    if not table_columns:
        return []

    code_col = next((col for col in ("FERF", "FREF", "REF", "CODIGO", "COD") if col in table_columns), "")
    name_col = next((col for col in ("NMFREF", "NOME", "DESCRICAO", "DESCR") if col in table_columns), "")
    color_col = next((col for col in ("COR", "COLOR", "COLOUR") if col in table_columns), "")
    if not code_col:
        return []

    code_expr = f"CAST([{code_col}] AS nvarchar(120))"
    code_trim_expr = f"LTRIM(RTRIM(ISNULL({code_expr}, '')))"
    name_expr = f"CAST([{name_col}] AS nvarchar(255))" if name_col else "CAST('' AS nvarchar(255))"
    color_expr = f"CAST([{color_col}] AS nvarchar(60))" if color_col else "CAST('' AS nvarchar(60))"
    query = f"%{(term or '').strip()}%"
    safe_limit = max(1, min(int(limit or 60), 100))
    rows = db.session.execute(text(f"""
        SELECT TOP ({safe_limit})
            LTRIM(RTRIM(ISNULL({code_expr}, ''))) AS codigo,
            LTRIM(RTRIM(ISNULL({name_expr}, ''))) AS nome,
            LTRIM(RTRIM(ISNULL({color_expr}, ''))) AS cor
        FROM dbo.FREF
        WHERE
            LEFT({code_trim_expr}, 1) IN ('2', '3', '4', '6')
            AND (:query = '%%'
             OR {code_expr} LIKE :query
             OR {name_expr} LIKE :query)
        ORDER BY
            LTRIM(RTRIM(ISNULL({code_expr}, ''))),
            LTRIM(RTRIM(ISNULL({name_expr}, '')))
    """), {"query": query}).mappings().all()
    return [
        {
            "codigo": str(row.get("codigo") or "").strip(),
            "nome": str(row.get("nome") or "").strip(),
            "cor": str(row.get("cor") or "").strip() or "#d8dee8",
        }
        for row in rows
        if str(row.get("codigo") or "").strip()
    ]


def _search_macro_supervisor_rows(term: str, limit: int = 60) -> list[dict]:
    table_columns = {
        str(row[0] or "").upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CT'
        """)).fetchall()
    }
    if not table_columns or "NOME" not in table_columns:
        return []

    color_expr = "CAST([COR] AS nvarchar(60))" if "COR" in table_columns else "CAST('' AS nvarchar(60))"
    query = f"%{(term or '').strip()}%"
    safe_limit = max(1, min(int(limit or 60), 100))
    rows = db.session.execute(text(f"""
        SELECT TOP ({safe_limit})
            LTRIM(RTRIM(ISNULL(CAST([NOME] AS nvarchar(255)), ''))) AS nome,
            LTRIM(RTRIM(ISNULL({color_expr}, ''))) AS cor
        FROM dbo.CT
        WHERE
            (:query = '%%'
             OR CAST([NOME] AS nvarchar(255)) LIKE :query)
        ORDER BY LTRIM(RTRIM(ISNULL(CAST([NOME] AS nvarchar(255)), '')))
    """), {"query": query}).mappings().all()
    return [
        {
            "nome": str(row.get("nome") or "").strip(),
            "cor": str(row.get("cor") or "").strip() or "#d8dee8",
        }
        for row in rows
        if str(row.get("nome") or "").strip()
    ]


def _macro_text_color(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw.startswith("#"):
        return "#fff"
    hex_value = raw[1:]
    if len(hex_value) == 3:
        hex_value = "".join(ch + ch for ch in hex_value)
    if len(hex_value) != 6:
        return "#fff"
    try:
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
    except ValueError:
        return "#fff"
    return "#162033" if ((r * 299 + g * 587 + b * 114) / 1000) > 150 else "#fff"


def _macro_table_exists(table_name: str) -> bool:
    return db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
    """), {"table_name": table_name}).first() is not None


def _macro_team_color_map(team_codes: set[str]) -> dict[str, str]:
    cleaned = {str(code or "").strip() for code in team_codes if str(code or "").strip()}
    if not cleaned:
        return {}
    table_columns = {
        str(row[0] or "").upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'FREF'
        """)).fetchall()
    }
    code_col = next((col for col in ("FERF", "FREF", "REF", "CODIGO", "COD") if col in table_columns), "")
    color_col = next((col for col in ("COR", "COLOR", "COLOUR") if col in table_columns), "")
    if not code_col:
        return {}
    color_expr = f"CAST([{color_col}] AS nvarchar(60))" if color_col else "CAST('' AS nvarchar(60))"
    rows = db.session.execute(text(f"""
        SELECT
            LTRIM(RTRIM(ISNULL(CAST([{code_col}] AS nvarchar(120)), ''))) AS codigo,
            LTRIM(RTRIM(ISNULL({color_expr}, ''))) AS cor
        FROM dbo.FREF
        WHERE LTRIM(RTRIM(ISNULL(CAST([{code_col}] AS nvarchar(120)), ''))) IN :codes
    """).bindparams(bindparam("codes", expanding=True)), {"codes": list(cleaned)}).mappings().all()
    return {
        str(row.get("codigo") or "").strip(): str(row.get("cor") or "").strip() or "#d8dee8"
        for row in rows
    }


def _macro_supervisor_color_map(names: set[str]) -> dict[str, str]:
    cleaned = {str(name or "").strip() for name in names if str(name or "").strip()}
    if not cleaned:
        return {}
    if not _macro_table_exists("CT"):
        return {}
    table_columns = {
        str(row[0] or "").upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CT'
        """)).fetchall()
    }
    if "NOME" not in table_columns:
        return {}
    color_expr = "CAST([COR] AS nvarchar(60))" if "COR" in table_columns else "CAST('' AS nvarchar(60))"
    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(CAST([NOME] AS nvarchar(255)), ''))) AS nome,
            LTRIM(RTRIM(ISNULL({color_expr}, ''))) AS cor
        FROM dbo.CT
        WHERE LTRIM(RTRIM(ISNULL(CAST([NOME] AS nvarchar(255)), ''))) IN :names
    """.format(color_expr=color_expr)).bindparams(bindparam("names", expanding=True)), {"names": list(cleaned)}).mappings().all()
    return {
        str(row.get("nome") or "").strip(): str(row.get("cor") or "").strip() or "#d8dee8"
        for row in rows
    }


def _fetch_macro_planning_rows(year: int) -> list[dict]:
    if not _macro_table_exists("GR_MACRO_OBRA") or not _macro_table_exists("GR_MACRO_PLANEAMENTO"):
        return []

    obra_rows = db.session.execute(text("""
        SELECT
            ANO,
            PROCESSO,
            DESCRICAO,
            FREF,
            QTT,
            DURACAO,
            ORDEM
        FROM dbo.GR_MACRO_OBRA
        WHERE ANO = :year
        ORDER BY ISNULL(ORDEM, 2147483647), PROCESSO
    """), {"year": year}).mappings().all()
    if not obra_rows:
        return []

    plan_rows = db.session.execute(text("""
        SELECT PROCESSO, SEMANA, ENCARREGADO
        FROM dbo.GR_MACRO_PLANEAMENTO
        WHERE ANO = :year
        ORDER BY PROCESSO, SEMANA
    """), {"year": year}).mappings().all()

    process_plan: dict[str, list[dict]] = {}
    supervisor_names: set[str] = set()
    for row in plan_rows:
        processo = str(row.get("PROCESSO") or "").strip()
        encarregado = str(row.get("ENCARREGADO") or "").strip()
        if not processo or not encarregado:
            continue
        supervisor_names.add(encarregado)
        process_plan.setdefault(processo, []).append({
            "week": int(row.get("SEMANA") or 0),
            "supervisor": encarregado,
        })

    team_colors = _macro_team_color_map({
        str(row.get("FREF") or "").strip()
        for row in obra_rows
    })
    supervisor_colors = _macro_supervisor_color_map(supervisor_names)

    rows: list[dict] = []
    for row in obra_rows:
        processo = str(row.get("PROCESSO") or "").strip()
        fref = str(row.get("FREF") or "").strip()
        bars = []
        current = None
        for item in process_plan.get(processo, []):
            week = int(item["week"] or 0)
            supervisor = str(item["supervisor"] or "").strip()
            if not week or not supervisor:
                continue
            if current and current["label"] == supervisor and current["start"] + current["duration"] == week:
                current["duration"] += 1
            else:
                if current:
                    bars.append(current)
                color = supervisor_colors.get(supervisor, "#d8dee8")
                current = {
                    "label": supervisor,
                    "start": week,
                    "duration": 1,
                    "color": color,
                    "text_color": _macro_text_color(color),
                }
        if current:
            bars.append(current)
        team_color = team_colors.get(fref, "#d8dee8")
        qtt_value = row.get("QTT")
        duration = row.get("DURACAO")
        if duration is None:
            duration = sum(int(bar["duration"] or 0) for bar in bars)
        rows.append({
            "processo": processo,
            "obra": processo,
            "descricao": str(row.get("DESCRICAO") or "").strip(),
            "quantidade": "" if qtt_value is None else str(qtt_value),
            "equipa": fref or "-",
            "equipa_cor": team_color,
            "equipa_text_color": _macro_text_color(team_color),
            "duracao": int(duration or 0),
            "bars": bars,
        })
    return rows


def _normalize_macro_payload_rows(payload: dict, year: int) -> list[dict]:
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("payload_rows_invalid")
    normalized = []
    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        processo = str((row or {}).get("processo") or "").strip()
        if not processo:
            continue
        if processo in seen:
            raise ValueError(f"processo_duplicado:{processo}")
        seen.add(processo)
        week_assignments: dict[int, str] = {}
        for bar in (row or {}).get("bars") or []:
            encarregado = str((bar or {}).get("encarregado") or (bar or {}).get("label") or "").strip()
            if not encarregado:
                continue
            start = max(1, min(53, int((bar or {}).get("startWeek") or (bar or {}).get("start") or 1)))
            end = max(start, min(53, int((bar or {}).get("endWeek") or (bar or {}).get("end") or start)))
            for week in range(start, end + 1):
                if week in week_assignments:
                    raise ValueError(f"sobreposicao_planeamento:{processo}:S{week}")
                week_assignments[week] = encarregado
        normalized.append({
            "ano": year,
            "processo": processo,
            "descricao": str((row or {}).get("descricao") or "").strip()[:255],
            "fref": str((row or {}).get("fref") or "").strip()[:60],
            "qtt": (row or {}).get("qtt") if str((row or {}).get("qtt") or "").strip() else None,
            "duracao": len(week_assignments),
            "ordem": int((row or {}).get("ordem") or index + 1),
            "week_assignments": week_assignments,
        })
    return normalized


def _save_macro_planning(year: int, payload: dict, user_login: str) -> list[dict]:
    rows = _normalize_macro_payload_rows(payload, year)
    processos = [row["processo"] for row in rows]
    login = str(user_login or "").strip()[:80]

    if processos:
        db.session.execute(text("""
            DELETE FROM dbo.GR_MACRO_OBRA
            WHERE ANO = :year AND PROCESSO NOT IN :processos
        """).bindparams(bindparam("processos", expanding=True)), {
            "year": year,
            "processos": processos,
        })
    else:
        db.session.execute(text("DELETE FROM dbo.GR_MACRO_OBRA WHERE ANO = :year"), {"year": year})

    for row in rows:
        result = db.session.execute(text("""
            UPDATE dbo.GR_MACRO_OBRA
            SET
                DESCRICAO = :descricao,
                FREF = :fref,
                QTT = :qtt,
                DURACAO = :duracao,
                ORDEM = :ordem,
                ALTERADO_EM = SYSUTCDATETIME(),
                ALTERADO_POR = :user_login
            WHERE ANO = :ano AND PROCESSO = :processo
        """), {
            "ano": row["ano"],
            "processo": row["processo"],
            "descricao": row["descricao"],
            "fref": row["fref"] or None,
            "qtt": row["qtt"],
            "duracao": row["duracao"],
            "ordem": row["ordem"],
            "user_login": login,
        })
        if result.rowcount == 0:
            db.session.execute(text("""
                INSERT INTO dbo.GR_MACRO_OBRA
                    (ANO, PROCESSO, DESCRICAO, FREF, QTT, DURACAO, ORDEM, CRIADO_POR)
                VALUES
                    (:ano, :processo, :descricao, :fref, :qtt, :duracao, :ordem, :user_login)
            """), {
                "ano": row["ano"],
                "processo": row["processo"],
                "descricao": row["descricao"],
                "fref": row["fref"] or None,
                "qtt": row["qtt"],
                "duracao": row["duracao"],
                "ordem": row["ordem"],
                "user_login": login,
            })

        db.session.execute(text("""
            DELETE FROM dbo.GR_MACRO_PLANEAMENTO
            WHERE ANO = :ano AND PROCESSO = :processo
        """), {"ano": row["ano"], "processo": row["processo"]})

        for week, supervisor in sorted(row["week_assignments"].items()):
            db.session.execute(text("""
                INSERT INTO dbo.GR_MACRO_PLANEAMENTO
                    (ANO, PROCESSO, SEMANA, ENCARREGADO, CRIADO_POR)
                VALUES
                    (:ano, :processo, :semana, :encarregado, :user_login)
            """), {
                "ano": row["ano"],
                "processo": row["processo"],
                "semana": week,
                "encarregado": supervisor,
                "user_login": login,
            })

    db.session.commit()
    return _fetch_macro_planning_rows(year)


def _relay_legacy_response(legacy_response) -> Response:
    response = Response(
        legacy_response.get_data(),
        status=legacy_response.status_code,
        content_type=legacy_response.content_type,
    )
    for key, value in legacy_response.headers.items():
        lower = key.lower()
        if lower in {"content-length", "transfer-encoding", "content-type", "connection"}:
            continue
        response.headers[key] = value
    return response


@bp.route("/gr360_planning")
@bp.route("/gr_planning")
@login_required
def index():
    _ensure_planning_access()
    planning_html, page_meta = build_planning_page(_current_login_value())
    return render_template(
        "gr_planning/gr360_index.html",
        planning_html=planning_html,
        page_meta=page_meta,
        legacy_script_files=LEGACY_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/teams")
@bp.route("/gr_planning/teams")
@login_required
def team_management():
    legacy_user = _ensure_team_management_access()
    team_management_html, page_meta = build_team_management_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/team_management_index.html",
        team_management_html=team_management_html,
        page_meta=page_meta,
        legacy_script_files=TEAM_MANAGEMENT_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/folha-mensal")
@bp.route("/gr_planning/folha-mensal")
@bp.route("/gr360_planning/monthly_sheet_index")
@bp.route("/gr_planning/monthly_sheet_index")
@login_required
def monthly_sheet():
    legacy_user = _ensure_monthly_sheet_access()
    monthly_html, page_meta = build_monthly_sheet_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/monthly_sheet_index.html",
        monthly_html=monthly_html,
        page_meta=page_meta,
        legacy_script_files=MONTHLY_SHEET_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/intersol/folha-mensal")
@bp.route("/gr_planning/intersol/folha-mensal")
@bp.route("/gr360_planning/folha-mensal-intersol")
@bp.route("/gr_planning/folha-mensal-intersol")
@bp.route("/gr360_planning/folha_mensal_intersol")
@bp.route("/gr_planning/folha_mensal_intersol")
@bp.route("/gr360_planning/monthly_sheet_intersol_index")
@bp.route("/gr_planning/monthly_sheet_intersol_index")
@login_required
def monthly_sheet_intersol():
    legacy_user = _ensure_monthly_sheet_intersol_access()
    monthly_html, page_meta = build_monthly_sheet_intersol_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/monthly_sheet_intersol_index.html",
        monthly_html=monthly_html,
        page_meta=page_meta,
        legacy_script_files=MONTHLY_SHEET_INTERSOL_SCRIPT_FILES,
    )


@bp.route("/gr360_monitor")
@bp.route("/gr_monitor")
@bp.route("/gr_planning/monitor")
@login_required
def gr_monitor():
    _ensure_monitor_access()
    return render_template("gr_planning/gr_monitor.html")


@bp.route("/gr360_planning/centrais-betao", defaults={"stamp": ""})
@bp.route("/gr360_planning/centrais-betao/", defaults={"stamp": ""})
@bp.route("/gr360_planning/centrais-betao/<stamp>")
@bp.route("/gr_planning/centrais-betao", defaults={"stamp": ""})
@bp.route("/gr_planning/centrais-betao/", defaults={"stamp": ""})
@bp.route("/gr_planning/centrais-betao/<stamp>")
@bp.route("/gr_planning/rcentral", defaults={"stamp": ""})
@bp.route("/gr_planning/rcentral/", defaults={"stamp": ""})
@bp.route("/gr_planning/rcentral/<stamp>")
@login_required
def concrete_central_page(stamp: str = ""):
    _ensure_planning_access()
    requested_stamp = (stamp or request.args.get("stamp") or "").strip()
    record = _fetch_concrete_record(requested_stamp) if requested_stamp else None
    if requested_stamp and not record:
        abort(404)
    today = (record.get("data") if record else "") or date.today().isoformat()
    return_to = request.args.get("return_to") or "/generic/view/RCENTRAL/"
    return render_template(
        "gr_planning/concrete_central.html",
        today=today,
        record=record,
        return_to=return_to,
        services=["MANUTENÇÃO", "MONTAGEM", "DESMONTAGEM", "PRODUÇÃO"],
    )


@bp.route("/gr360_planning/macro")
@bp.route("/gr_planning/macro")
@bp.route("/gr_planning/planeamento-macro")
@login_required
def macro_planning():
    _ensure_planning_access()
    year = _parse_year_param(request.args.get("year"))
    weeks = list(range(1, 53))
    return render_template(
        "gr_planning/macro_planning.html",
        year=year,
        weeks=weeks,
        rows=_fetch_macro_planning_rows(year),
    )


@bp.route("/api/gr_planning/macro/opc")
@login_required
def macro_planning_opc():
    _ensure_planning_access()
    term = (request.args.get("q") or "").strip()
    try:
        return jsonify({"rows": _search_macro_opc_rows(term)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/macro/teams")
@login_required
def macro_planning_teams():
    _ensure_planning_access()
    term = (request.args.get("q") or "").strip()
    try:
        return jsonify({"rows": _search_macro_team_rows(term)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/macro/supervisors")
@login_required
def macro_planning_supervisors():
    _ensure_planning_access()
    term = (request.args.get("q") or "").strip()
    try:
        return jsonify({"rows": _search_macro_supervisor_rows(term)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/macro/plan", methods=["GET", "POST"])
@login_required
def macro_planning_plan():
    _ensure_planning_access()
    year = _parse_year_param(request.args.get("year"))
    if request.method == "GET":
        try:
            return jsonify({"rows": _fetch_macro_planning_rows(year)})
        except Exception as exc:
            return jsonify({"rows": [], "error": str(exc)}), 500

    payload = request.get_json(silent=True) or {}
    try:
        payload_year = _parse_year_param(str(payload.get("year") or year))
        rows = _save_macro_planning(payload_year, payload, _current_login_value())
        return jsonify({"ok": True, "rows": rows})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/api/gr_planning/centrais-betao/records")
@login_required
def concrete_central_records():
    _ensure_planning_access()
    try:
        day = _parse_date_value(request.args.get("date"))
        return jsonify({"rows": _fetch_concrete_records(day)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/centrais-betao/records", methods=["POST"])
@login_required
def concrete_central_save():
    _ensure_planning_access()
    payload = request.get_json(silent=True) or {}
    try:
        result = _save_concrete_record(payload)
        result["rows"] = _fetch_concrete_records(_parse_date_value(payload.get("data")))
        return jsonify(result)
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/api/gr_planning/centrais-betao/records/<stamp>", methods=["GET", "DELETE"])
@login_required
def concrete_central_record(stamp: str):
    _ensure_planning_access()
    normalized = str(stamp or "").strip()[:25]
    if not normalized:
        return jsonify({"ok": False, "error": "Registo invalido."}), 400
    if request.method == "GET":
        row = _fetch_concrete_record(normalized)
        if not row:
            return jsonify({"ok": False, "error": "Registo nao encontrado."}), 404
        return jsonify({"ok": True, "record": row})
    try:
        result = db.session.execute(
            text("DELETE FROM dbo.RCENTRAL WHERE RCENTRALSTAMP = :stamp"),
            {"stamp": normalized},
        )
        db.session.commit()
        return jsonify({"ok": True, "deleted": int(result.rowcount or 0)})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/api/gr_planning/centrais-betao/opc")
@login_required
def concrete_central_opc():
    _ensure_planning_access()
    term = (request.args.get("q") or "").strip()
    try:
        return jsonify({"rows": _search_macro_opc_rows(term)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/centrais-betao/vehicles")
@login_required
def concrete_central_vehicles():
    _ensure_planning_access()
    term = (request.args.get("q") or "").strip()
    try:
        return jsonify({"rows": _fetch_concrete_vehicles(term)})
    except Exception as exc:
        return jsonify({"rows": [], "error": str(exc)}), 500


@bp.route("/api/gr_planning/monitor/tasks")
@login_required
def gr_monitor_tasks():
    _ensure_monitor_access()
    today = date.today()
    start = _parse_date_param(request.args.get("start"), today - timedelta(days=30))
    end = _parse_date_param(request.args.get("end"), today + timedelta(days=60))
    return jsonify({
        "rows": fetch_gr_monitor_tasks(
            start_date=start,
            end_date=end,
            user_code=_monitor_user_filter(),
        ),
    })


@bp.route("/api/gr_planning/monitor/status-options")
@login_required
def gr_monitor_status_options():
    _ensure_monitor_access()
    return jsonify({"rows": fetch_gr_task_status_options()})


@bp.route("/api/gr_planning/monitor/tasks/<task_id>/status", methods=["POST"])
@login_required
def gr_monitor_task_status(task_id: str):
    _ensure_monitor_edit_access()
    body = request.get_json(silent=True) or {}
    try:
        status_code = int(body.get("status_code"))
        user_login = (getattr(current_user, "LOGIN", "") or "").strip()
        return jsonify(update_gr_task_status(
            task_id,
            status_code,
            user_login=user_login,
            restrict_user_code=_monitor_user_filter(),
        ))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/gr_planning/legacy-static/<path:filename>")
@login_required
def legacy_static(filename: str):
    safe_root = str(Path(LEGACY_STATIC_DIR).resolve())
    return send_from_directory(safe_root, filename)


@bp.route("/api/gr_planning/<path:legacy_path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@login_required
def legacy_api_proxy(legacy_path: str):
    api_scope = get_api_access_scope(legacy_path)
    if not api_scope:
        abort(404)
    if api_scope == "monthly_sheet":
        legacy_user = _ensure_monthly_sheet_access()
    elif api_scope == "monthly_sheet_intersol":
        legacy_user = _ensure_monthly_sheet_intersol_access()
    elif api_scope == "planning":
        legacy_user = _ensure_planning_access()
    elif api_scope == "team_management":
        legacy_user = _ensure_team_management_access()
    else:
        allowed, legacy_user = can_access_planning(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_monthly_sheet(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_monthly_sheet_intersol(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_team_management(_current_login_value())
        if not allowed or not legacy_user:
            abort(403)
    legacy_response = open_legacy_request(
        f"/api/{legacy_path}",
        login_value=_current_login_value(),
        method=request.method,
        query_string=request.args,
        data=request.get_data(),
        content_type=request.content_type,
        access_mode=api_scope,
        legacy_user=legacy_user,
    )
    return _relay_legacy_response(legacy_response)
