from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

import pyodbc


def execute_read_query(
    connection_string: str,
    sql: str,
    params: Iterable[Any] = (),
    *,
    connection_timeout: int = 10,
    query_timeout: int = 25,
    lock_timeout_ms: int = 10_000,
) -> list[dict[str, Any]]:
    """Execute a dashboard read without waiting indefinitely on PHC writes."""
    with pyodbc.connect(
        connection_string,
        timeout=connection_timeout,
        autocommit=True,
    ) as conn:
        conn.timeout = query_timeout
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        cursor.execute(f"SET LOCK_TIMEOUT {int(lock_timeout_ms)}")
        cursor.execute(sql, *list(params))
        columns = [column[0] for column in cursor.description or []]
        return [
            {
                column: _json_value(value)
                for column, value in zip(columns, row)
            }
            for row in cursor.fetchall()
        ]


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return value
