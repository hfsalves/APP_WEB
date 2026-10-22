#!/usr/bin/env python3
"""Repair four confirmed missing PHC positions; dry-run unless --apply is used."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import pyodbc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planeamento.config import get_mssql_config


# Position numbers follow the existing commercial line order in each dossier.
REPAIRS = (
    ("IS2344", "SRF26081450381,432000001", "1"),
    ("IS2412", "SF26100151695,487000001", "1"),
    ("IS2412", "SF26100152025,140000003", "2"),
    ("IS2413", "SF26100152233,869000001", "1"),
)
PROJECTS = ("HS2344", "HS2412", "HS2413", "HS2357")


def clean(value):
    return str(value or "").strip()


def rows(cursor, query, params=()):
    cursor.execute(query, params)
    names = [column[0].lower() for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def snapshot(cursor, *, lock=False):
    hints = "WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    return rows(cursor, f"""
        SELECT I.*, B2.PROCESSO AS source_process
        FROM INTERSOL.dbo.BI I {hints}
        JOIN INTERSOL.dbo.BO2 B2 ON B2.BO2STAMP=I.BOSTAMP
        WHERE B2.PROCESSO IN ('IS2344','IS2412','IS2413') AND I.NDOS=122
        ORDER BY B2.PROCESSO,I.LORDEM,I.BISTAMP
    """)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    connection = pyodbc.connect(
        get_mssql_config().as_odbc_string() + ";TrustServerCertificate=Yes;", timeout=5
    )
    connection.timeout = 30
    try:
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 10000")
        before = snapshot(cursor, lock=args.apply)
        by_stamp = {clean(row["bistamp"]): row for row in before}
        changes = []
        for process, stamp, position in REPAIRS:
            row = by_stamp.get(stamp)
            if not row or clean(row["source_process"]) != process or not clean(row["design"]):
                raise RuntimeError(f"Source line no longer matches: {stamp}")
            if clean(row["litem"]) == position and clean(row["dgeral"]):
                continue
            if clean(row["litem"]) or clean(row["dgeral"]):
                raise RuntimeError(f"Line changed since diagnosis: {stamp}")
            if any(clean(other["litem"]) == position
                   and clean(other["source_process"]) == process for other in before):
                raise RuntimeError(f"Position {position} already exists in {process}")
            changes.append({"process": process, "bistamp": stamp, "litem": position,
                            "description": row["design"], "quantity": row["qtt"]})
        if not args.apply:
            print(json.dumps({"dry_run": True, "changes": changes}, ensure_ascii=False, default=str, indent=2))
            return
        if not changes:
            print("Already repaired; no changes.")
            return

        backup = ROOT / "backups" / now.strftime("planning_juliana_%Y%m%d_%H%M%S")
        backup.mkdir(parents=True, exist_ok=False)
        operational = {}
        for table in ("u_plano", "u_lplano", "u_am", "u_aml"):
            operational[table] = rows(cursor, f"SELECT * FROM dbo.{table} WHERE PROCESSO IN (?,?,?,?)", PROJECTS)
        payload = {"time": now.isoformat(), "source": "INTERSOL.dbo.BI", "changes": changes,
                   "before": before, "operational_before": operational}
        (backup / "before.json").write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2))
        for change in changes:
            cursor.execute("""
                UPDATE INTERSOL.dbo.BI
                SET LITEM=?, DGERAL=DESIGN, USRINIS='CDX', USRDATA=?, USRHORA=?
                WHERE BISTAMP=? AND NDOS=122
                  AND NULLIF(LTRIM(RTRIM(LITEM)),'') IS NULL
                  AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(max),DGERAL))),'') IS NULL
            """, (change["litem"], now.date(), now.strftime("%H:%M:%S"), change["bistamp"]))
            if cursor.rowcount != 1:
                raise RuntimeError(f"Expected one updated row: {change['bistamp']}")
        after = snapshot(cursor)
        after_by_stamp = {clean(row["bistamp"]): row for row in after}
        if set(after_by_stamp) != set(by_stamp):
            raise RuntimeError("Source line set changed")
        changed_stamps = {change["bistamp"] for change in changes}
        expected = {change["bistamp"]: change for change in changes}
        allowed = {"litem", "dgeral", "usrinis", "usrdata", "usrhora"}
        for stamp, original in by_stamp.items():
            actual = after_by_stamp[stamp]
            for field, value in original.items():
                if stamp in changed_stamps and field in allowed:
                    continue
                if actual[field] != value:
                    raise RuntimeError(f"Unexpected change to {stamp}.{field}")
            if stamp in changed_stamps and (clean(actual["litem"]) != expected[stamp]["litem"]
                    or actual["dgeral"] != original["design"]):
                raise RuntimeError(f"Repair did not match expected result: {stamp}")
        for table, original in operational.items():
            actual = rows(cursor, f"SELECT * FROM dbo.{table} WHERE PROCESSO IN (?,?,?,?)", PROJECTS)
            if actual != original:
                raise RuntimeError(f"Operational records changed: {table}")
        connection.commit()
        # Read again after COMMIT so the report confirms persisted data.
        persisted = snapshot(cursor)
        if persisted != after:
            raise RuntimeError("Post-commit verification differs")
        (backup / "after.json").write_text(json.dumps({"committed": True, "after": persisted}, ensure_ascii=False, default=str, indent=2))
        print(json.dumps({"committed": True, "updated_lines": len(changes), "backup": str(backup)}, indent=2))
    finally:
        connection.rollback()
        connection.close()


if __name__ == "__main__":
    main()
