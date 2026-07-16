from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
import hashlib
import mimetypes
import ntpath
import os
import re
from typing import Any
from urllib.parse import quote

import pyodbc
from flask import current_app
from sqlalchemy import text

from models import db
from services.phc_user_import_service import _phc_conn_str


PHC_SYNC_USER = "PHC_SYNC"
PHC_ATTACHMENT_PATH_PREFIX = "/api/anexos/phc-va/"

# Apenas as bases de producao confirmadas. HSOLS_GE e HSOLS_MNT ficam
# intencionalmente excluidas desta lista.
PHC_VA_SOURCES: dict[str, tuple[str, ...]] = {
    "HSOLS_PT": (
        r"\\10.0.1.11\ged\HSOLS_PT\flotte\documentation_voitures",
    ),
    "HSOLS_DE": (
        r"\\10.0.1.11\ged\HSOLS_DE\flotte\documentation_voitures",
    ),
    "HSOLS_FR": (
        r"\\10.0.1.11\ged\HSOLS_FR\flotte\documentation_voitures",
    ),
    "INTERSOL": (
        r"\\10.0.1.11\ged\HSOLS_INTERSOL_AL\flotte",
        r"\\10.0.1.11\ged\HSOLS_INTERSOL_CH\flotte",
        r"\\10.0.1.11\ged\HSOLS_INTERSOL_LOR\flotte",
    ),
    "HSOLS_GRE": (
        r"\\10.0.1.11\ged\HSOLS_GR_EQP",
    ),
}

ORIGIN_TO_FEID = {
    "HSOLS FRANCE": 1,
    "HSOLS PORTUGAL": 2,
    "HSOLS ALLEMAGNE": 4,
    "HSOLS ESPAGNE": 6,
    "HSOLS MAROC": 7,
    "INTERSOL-ALSACE": 8,
}


class PhcVaAttachmentNotFound(FileNotFoundError):
    pass


@dataclass(frozen=True)
class PhcVaAttachmentFile:
    path: str
    download_name: str
    mimetype: str


def _clean(value: Any, max_length: int | None = None) -> str:
    clean_value = str(value or "").strip()
    return clean_value[:max_length] if max_length else clean_value


def _source_key(value: str) -> str:
    source = _clean(value).upper()
    if source not in PHC_VA_SOURCES:
        raise PhcVaAttachmentNotFound("Origem de anexo nao permitida.")
    return source


def _normalise_fullname(value: Any) -> str:
    path = _clean(value).strip('"')
    if not path:
        return ""
    path = path.replace("/", "\\")
    return re.sub(
        r"^\\\\(?:servidor|10\.0\.1\.11)\\ged(?=\\|$)",
        r"\\\\10.0.1.11\\ged",
        path,
        count=1,
        flags=re.IGNORECASE,
    )


def _extension(value: Any) -> str:
    return _clean(value).lower().lstrip(".")


def _candidate_paths(row: dict[str, Any]) -> list[str]:
    fullname = _normalise_fullname(row.get("FULLNAME"))
    fext = _extension(row.get("FEXT"))
    fname = _clean(row.get("FNAME"))
    candidates: list[str] = []

    if fullname:
        candidates.append(fullname)
        if fext and not ntpath.splitext(fullname)[1]:
            candidates.append(f"{fullname}.{fext}")
        if fname:
            logical_name = fname
            if fext and not ntpath.splitext(logical_name)[1]:
                logical_name = f"{logical_name}.{fext}"
            candidates.append(ntpath.join(ntpath.dirname(fullname), logical_name))

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.casefold()
        if candidate and key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _candidate_filenames(row: dict[str, Any]) -> list[str]:
    fext = _extension(row.get("FEXT"))
    names: list[str] = []
    fullname = _normalise_fullname(row.get("FULLNAME"))
    if fullname:
        names.append(ntpath.basename(fullname))
    fname = _clean(row.get("FNAME"))
    if fname:
        names.append(ntpath.basename(fname))

    expanded: list[str] = []
    for name in names:
        if not name:
            continue
        expanded.append(name)
        if fext and not ntpath.splitext(name)[1]:
            expanded.append(f"{name}.{fext}")

    unique: list[str] = []
    seen: set[str] = set()
    for name in expanded:
        key = name.casefold()
        if key not in seen:
            unique.append(name)
            seen.add(key)
    return unique


@lru_cache(maxsize=len(PHC_VA_SOURCES))
def _filename_index(source: str) -> dict[str, tuple[str, ...]]:
    source = _source_key(source)
    index: dict[str, list[str]] = {}
    for root in PHC_VA_SOURCES[source]:
        for directory, _subdirectories, filenames in os.walk(root):
            for filename in filenames:
                index.setdefault(filename.casefold(), []).append(os.path.join(directory, filename))
    return {key: tuple(sorted(values, key=str.casefold)) for key, values in index.items()}


def clear_path_cache() -> None:
    _filename_index.cache_clear()


def _compact_path_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def resolve_attachment_path(source: str, row: dict[str, Any]) -> str | None:
    source = _source_key(source)
    for candidate in _candidate_paths(row):
        if os.path.isfile(candidate):
            return candidate

    matches: set[str] = set()
    index = _filename_index(source)
    for filename in _candidate_filenames(row):
        matches.update(index.get(filename.casefold(), ()))

    valid_matches = sorted((path for path in matches if os.path.isfile(path)), key=str.casefold)
    if len(valid_matches) == 1:
        return valid_matches[0]
    if not valid_matches:
        return None

    plate = _compact_path_token(row.get("MATRICULA"))
    if plate:
        plate_matches = [path for path in valid_matches if plate in _compact_path_token(path)]
        if len(plate_matches) == 1:
            return plate_matches[0]
    return None


def _source_attachment_rows(source: str, attachment_stamp: str = "") -> list[dict[str, Any]]:
    source = _source_key(source)
    stamp = _clean(attachment_stamp)
    where_stamp = " AND LTRIM(RTRIM(CONVERT(varchar(25), a.ANEXOSSTAMP))) = ?" if stamp else ""
    query = f"""
        SELECT
            LTRIM(RTRIM(CONVERT(varchar(25), a.ANEXOSSTAMP))) AS ANEXOSSTAMP,
            LTRIM(RTRIM(CONVERT(varchar(25), a.RECSTAMP))) AS RECSTAMP,
            CONVERT(varchar(200), a.DESCRICAO) AS DESCRICAO,
            CONVERT(varchar(2048), a.FULLNAME) AS FULLNAME,
            CONVERT(varchar(150), a.FNAME) AS FNAME,
            CONVERT(varchar(30), a.FEXT) AS FEXT,
            a.FLEN AS FLEN,
            LTRIM(RTRIM(CONVERT(varchar(80), v.MATRICULA))) AS MATRICULA,
            COALESCE(a.USRDATA, a.AUSRDATA, a.EUSRDATA, a.OUSRDATA) AS DATA_ANEXO
        FROM dbo.ANEXOS a
        INNER JOIN dbo.VA v
            ON LTRIM(RTRIM(CONVERT(varchar(25), v.VASTAMP))) = LTRIM(RTRIM(CONVERT(varchar(25), a.RECSTAMP)))
        WHERE UPPER(LTRIM(RTRIM(CONVERT(varchar(80), a.ORITABLE)))) = 'VA'
          AND ISNULL(a.INVISIVEL, 0) = 0
          AND ISNULL(a.PRIVADO, 0) = 0
          {where_stamp}
        ORDER BY a.ANEXOSSTAMP
    """
    with pyodbc.connect(_phc_conn_str(source), timeout=15) as connection:
        cursor = connection.cursor()
        cursor.execute(query, stamp) if stamp else cursor.execute(query)
        columns = [str(column[0]).upper() for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _local_vehicles() -> dict[str, dict[str, Any]]:
    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(VASTAMP, ''))) AS VASTAMP,
            LTRIM(RTRIM(ISNULL(ORIGEM, ''))) AS ORIGEM,
            LTRIM(RTRIM(ISNULL(MATRICULA, ''))) AS MATRICULA
        FROM dbo.VA
        WHERE LTRIM(RTRIM(ISNULL(VASTAMP, ''))) <> ''
    """)).mappings().all()
    return {_clean(row.get("VASTAMP")): dict(row) for row in rows}


def _deterministic_local_stamp(source: str, source_stamp: str) -> str:
    identity = f"PHCVA|{_source_key(source)}|{_clean(source_stamp)}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest().upper()[:25]


def _truncate_filename(filename: str, max_length: int = 100) -> str:
    clean_name = _clean(filename)
    if len(clean_name) <= max_length:
        return clean_name
    stem, extension = ntpath.splitext(clean_name)
    if not extension or len(extension) >= max_length:
        return clean_name[:max_length]
    return f"{stem[:max_length - len(extension)]}{extension}"


def _source_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.today()


def _attachment_values(
    source: str,
    row: dict[str, Any],
    local_vehicle: dict[str, Any],
    resolved_path: str,
) -> dict[str, Any]:
    source_stamp = _clean(row.get("ANEXOSSTAMP"))
    resolved_name = ntpath.basename(resolved_path) or _clean(row.get("FNAME")) or source_stamp
    file_name = _truncate_filename(resolved_name)
    file_type = _extension(ntpath.splitext(resolved_name)[1] or row.get("FEXT"))[:25]
    description = _clean(row.get("DESCRICAO")) or _clean(row.get("FNAME")) or file_name
    origin = _clean(local_vehicle.get("ORIGEM")).upper()
    return {
        "ANEXOSSTAMP": _deterministic_local_stamp(source, source_stamp),
        "TABELA": "VA",
        "RECSTAMP": _clean(row.get("RECSTAMP"), 25),
        "DESCRICAO": description[:200],
        "FICHEIRO": file_name,
        "CAMINHO": f"{PHC_ATTACHMENT_PATH_PREFIX}{source}/{quote(source_stamp, safe='')}",
        "TIPO": file_type,
        "DATA": _source_date(row.get("DATA_ANEXO")),
        "UTILIZADOR": PHC_SYNC_USER,
        "USSTAMP": "",
        "FEID": ORIGIN_TO_FEID.get(origin, 0),
    }


def _same_local_attachment(existing: dict[str, Any], target: dict[str, Any]) -> bool:
    text_fields = (
        "TABELA", "RECSTAMP", "DESCRICAO", "FICHEIRO", "CAMINHO",
        "TIPO", "UTILIZADOR", "USSTAMP",
    )
    if any(_clean(existing.get(field)) != _clean(target.get(field)) for field in text_fields):
        return False
    existing_date = existing.get("DATA")
    if isinstance(existing_date, datetime):
        existing_date = existing_date.date()
    return existing_date == target.get("DATA") and int(existing.get("FEID") or 0) == int(target.get("FEID") or 0)


def _assert_roots_available() -> None:
    unavailable = [
        root
        for roots in PHC_VA_SOURCES.values()
        for root in roots
        if not os.path.isdir(root)
    ]
    if unavailable:
        raise RuntimeError(
            "Nao foi possivel aceder a todas as raizes GED configuradas; "
            "a sincronizacao foi cancelada sem escrever na base de dados."
        )


def collect_phc_va_attachments() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _assert_roots_available()
    clear_path_cache()
    local_vehicles = _local_vehicles()
    targets: list[dict[str, Any]] = []
    source_counts: dict[str, dict[str, int]] = {}

    for source in PHC_VA_SOURCES:
        source_rows = _source_attachment_rows(source)
        counts = {"phc": len(source_rows), "vehicle_in_app": 0, "existing_file": 0, "missing_file": 0}
        for row in source_rows:
            recstamp = _clean(row.get("RECSTAMP"))
            local_vehicle = local_vehicles.get(recstamp)
            if not local_vehicle:
                continue
            counts["vehicle_in_app"] += 1
            resolved_path = resolve_attachment_path(source, row)
            if not resolved_path:
                counts["missing_file"] += 1
                continue
            counts["existing_file"] += 1
            targets.append(_attachment_values(source, row, local_vehicle, resolved_path))
        source_counts[source] = counts

    stamps = [target["ANEXOSSTAMP"] for target in targets]
    if len(stamps) != len(set(stamps)):
        raise RuntimeError("Foram gerados identificadores locais duplicados para anexos PHC.")

    return targets, {
        "sources": source_counts,
        "vehicles_in_app": len(local_vehicles),
        "eligible": sum(item["vehicle_in_app"] for item in source_counts.values()),
        "existing_files": len(targets),
        "missing_files": sum(item["missing_file"] for item in source_counts.values()),
    }


def sync_phc_va_attachments(*, execute: bool = False) -> dict[str, Any]:
    database_name = _clean(db.session.execute(text("SELECT DB_NAME()" )).scalar()).upper()
    if database_name != "GR360_CORE":
        raise RuntimeError(f"Base local inesperada: {database_name or '(desconhecida)'}.")

    targets, result = collect_phc_va_attachments()
    existing_rows = db.session.execute(text("""
        SELECT
            ANEXOSSTAMP, TABELA, RECSTAMP, DESCRICAO, FICHEIRO, CAMINHO,
            TIPO, DATA, UTILIZADOR, USSTAMP, FEID
        FROM dbo.ANEXOS
    """)).mappings().all()
    existing_by_stamp = {_clean(row.get("ANEXOSSTAMP")): dict(row) for row in existing_rows}

    inserts: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    for target in targets:
        existing = existing_by_stamp.get(target["ANEXOSSTAMP"])
        if not existing:
            inserts.append(target)
            continue
        is_our_record = (
            _clean(existing.get("UTILIZADOR")).upper() == PHC_SYNC_USER
            and _clean(existing.get("CAMINHO")).startswith(PHC_ATTACHMENT_PATH_PREFIX)
        )
        if not is_our_record:
            raise RuntimeError(f"Colisao de ANEXOSSTAMP: {target['ANEXOSSTAMP']}.")
        if not _same_local_attachment(existing, target):
            updates.append(target)

    result.update({
        "mode": "execute" if execute else "dry-run",
        "inserted": len(inserts),
        "updated": len(updates),
        "unchanged": len(targets) - len(inserts) - len(updates),
    })
    if not execute:
        db.session.rollback()
        return result

    insert_sql = text("""
        INSERT INTO dbo.ANEXOS
            (ANEXOSSTAMP, TABELA, RECSTAMP, DESCRICAO, FICHEIRO, CAMINHO,
             TIPO, DATA, UTILIZADOR, USSTAMP, FEID)
        VALUES
            (:ANEXOSSTAMP, :TABELA, :RECSTAMP, :DESCRICAO, :FICHEIRO, :CAMINHO,
             :TIPO, :DATA, :UTILIZADOR, :USSTAMP, :FEID)
    """)
    update_sql = text("""
        UPDATE dbo.ANEXOS
           SET TABELA = :TABELA,
               RECSTAMP = :RECSTAMP,
               DESCRICAO = :DESCRICAO,
               FICHEIRO = :FICHEIRO,
               CAMINHO = :CAMINHO,
               TIPO = :TIPO,
               DATA = :DATA,
               UTILIZADOR = :UTILIZADOR,
               USSTAMP = :USSTAMP,
               FEID = :FEID
         WHERE ANEXOSSTAMP = :ANEXOSSTAMP
           AND UTILIZADOR = 'PHC_SYNC'
           AND CAMINHO LIKE '/api/anexos/phc-va/%'
    """)
    try:
        if inserts:
            db.session.execute(insert_sql, inserts)
        if updates:
            db.session.execute(update_sql, updates)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return result


def get_phc_va_attachment_file(source: str, attachment_stamp: str) -> PhcVaAttachmentFile:
    source = _source_key(source)
    stamp = _clean(attachment_stamp)
    if not stamp or len(stamp) > 25:
        raise PhcVaAttachmentNotFound("Anexo PHC invalido.")

    rows = _source_attachment_rows(source, stamp)
    if len(rows) != 1:
        raise PhcVaAttachmentNotFound("Anexo PHC nao encontrado.")
    row = rows[0]

    local_vehicle = db.session.execute(text("""
        SELECT TOP 1 VASTAMP
        FROM dbo.VA
        WHERE LTRIM(RTRIM(ISNULL(VASTAMP, ''))) = :stamp
    """), {"stamp": _clean(row.get("RECSTAMP"))}).first()
    if not local_vehicle:
        raise PhcVaAttachmentNotFound("A viatura do anexo nao existe na aplicacao.")

    resolved_path = resolve_attachment_path(source, row)
    if not resolved_path:
        raise PhcVaAttachmentNotFound("O ficheiro do anexo ja nao existe no GED.")

    download_name = ntpath.basename(resolved_path) or _clean(row.get("FNAME")) or "anexo"
    mimetype = mimetypes.guess_type(download_name)[0] or "application/octet-stream"
    return PhcVaAttachmentFile(
        path=resolved_path,
        download_name=download_name,
        mimetype=mimetype,
    )
