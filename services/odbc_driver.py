from __future__ import annotations

import logging
import re
from functools import lru_cache
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit


SQL_SERVER_ODBC_DRIVER_18 = "ODBC Driver 18 for SQL Server"
SQL_SERVER_ODBC_DRIVER_17 = "ODBC Driver 17 for SQL Server"
SQL_SERVER_ODBC_DRIVER_CANDIDATES = (
    SQL_SERVER_ODBC_DRIVER_18,
    SQL_SERVER_ODBC_DRIVER_17,
)

logger = logging.getLogger("stationzero.odbc")


@lru_cache(maxsize=1)
def get_sql_server_odbc_driver() -> str:
    """Return the best installed Microsoft SQL Server ODBC driver.

    Driver 18 is preferred when available, which covers modern macOS installs.
    Driver 17 remains the fallback for existing Windows environments.
    """
    try:
        import pyodbc

        installed_drivers = set(pyodbc.drivers())
    except Exception as exc:
        logger.warning(
            "Nao foi possivel listar drivers ODBC via pyodbc.drivers(); "
            "a usar fallback '%s'. Erro: %s",
            SQL_SERVER_ODBC_DRIVER_17,
            exc,
        )
        return SQL_SERVER_ODBC_DRIVER_17

    for driver in SQL_SERVER_ODBC_DRIVER_CANDIDATES:
        if driver in installed_drivers:
            logger.info("Driver ODBC SQL Server escolhido: %s", driver)
            return driver

    logger.warning(
        "Nenhum driver ODBC SQL Server esperado encontrado em pyodbc.drivers(): %s. "
        "A usar fallback '%s'.",
        sorted(installed_drivers),
        SQL_SERVER_ODBC_DRIVER_17,
    )
    return SQL_SERVER_ODBC_DRIVER_17


def get_sqlalchemy_odbc_driver_value() -> str:
    """Return the URL-encoded driver value for SQLAlchemy mssql+pyodbc URLs."""
    return quote_plus(get_sql_server_odbc_driver())


def normalize_pyodbc_conn_str_driver(conn_str: str) -> str:
    """Replace or add DRIVER in a semicolon ODBC connection string."""
    value = str(conn_str or "").strip()
    if not value:
        return value
    driver = get_sql_server_odbc_driver()
    driver_part = f"DRIVER={{{driver}}}"
    if re.search(r"(^|;)DRIVER=\{?[^;{}]+\}?", value, flags=re.IGNORECASE):
        return re.sub(
            r"(^|;)DRIVER=\{?[^;{}]+\}?",
            lambda match: f"{match.group(1)}{driver_part}",
            value,
            count=1,
            flags=re.IGNORECASE,
        )
    separator = "" if value.endswith(";") else ";"
    return f"{driver_part};{value}{separator}"


def normalize_sqlalchemy_mssql_url_driver(url: str) -> str:
    """Replace or add the driver query parameter in a mssql+pyodbc URL."""
    value = str(url or "").strip()
    if not value or not value.lower().startswith("mssql+pyodbc://"):
        return value

    parts = urlsplit(value)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    driver_value = get_sql_server_odbc_driver()
    replaced = False
    normalized_query_items: list[tuple[str, str]] = []
    for key, item_value in query_items:
        if key.lower() == "driver":
            normalized_query_items.append((key, driver_value))
            replaced = True
        else:
            normalized_query_items.append((key, item_value))
    if not replaced:
        normalized_query_items.insert(0, ("driver", driver_value))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(normalized_query_items, doseq=True),
            parts.fragment,
        )
    )
