"""Static configuration for the Planeamento application."""
from dataclasses import dataclass
from pathlib import Path
import sys

try:
    from services.odbc_driver import get_sql_server_odbc_driver
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.odbc_driver import get_sql_server_odbc_driver


@dataclass(frozen=True)
class MSSQLConfig:
    driver: str = ""
    server: str = "10.0.1.12"
    database: str = "HSOLS_MASTER"
    username: str = "sa"
    password: str = "H$ols2020"

    def as_odbc_string(self) -> str:
        """Return a DSN-less ODBC connection string."""
        driver = self.driver or get_sql_server_odbc_driver()
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password}"
        )


def get_mssql_config() -> MSSQLConfig:
    """Expose the config via a single function for easy imports."""
    return MSSQLConfig()
