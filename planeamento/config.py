"""Static configuration for the Planeamento application."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MSSQLConfig:
    driver: str = "ODBC Driver 17 for SQL Server"
    server: str = "10.0.1.12"
    database: str = "HSOLS_MASTER"
    username: str = "sa"
    password: str = "H$ols2020"

    def as_odbc_string(self) -> str:
        """Return a DSN-less ODBC connection string."""
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password}"
        )


def get_mssql_config() -> MSSQLConfig:
    """Expose the config via a single function for easy imports."""
    return MSSQLConfig()
