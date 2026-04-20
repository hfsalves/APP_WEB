"""Utilities to interact with the MS SQL Server instance."""
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import Dict, Iterable, Iterator, Optional, TYPE_CHECKING, List

try:
    import pyodbc
except ImportError as exc:  # pragma: no cover - simplifies local dev without pyodbc
    pyodbc = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from config import get_mssql_config, MSSQLConfig

if TYPE_CHECKING:  # pragma: no cover
    from pyodbc import Connection


class Database:
    """Wrap pyodbc connection management."""

    def __init__(self, config: Optional[MSSQLConfig] = None) -> None:
        self._config = config or get_mssql_config()
        self._column_cache: Dict[tuple[str, str], bool] = {}

    @contextmanager
    def connect(self) -> Iterator["Connection"]:
        if pyodbc is None:
            raise RuntimeError(
                "pyodbc is not available. Install it in the environment to connect to SQL Server"
            ) from _IMPORT_ERROR
        connection = pyodbc.connect(self._config.as_odbc_string(), timeout=5)
        try:
            yield connection
        finally:
            connection.close()

    def ping(self) -> tuple[bool, Optional[str]]:
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # pragma: no cover
            return False, str(exc)
        return True, None

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        cache_key = (table_name.lower(), column_name.lower())
        if cache_key in self._column_cache:
            return self._column_cache[cache_key]
        query = (
            "SELECT 1 "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? AND COLUMN_NAME = ?"
        )
        exists = False
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (table_name, column_name))
                exists = cursor.fetchone() is not None
        except Exception:
            exists = False
        self._column_cache[cache_key] = exists
        return exists

    def _production_line_prime_column(self) -> Optional[str]:
        if self._column_exists("u_aml", "u_prime"):
            return "u_prime"
        if self._column_exists("u_aml", "prime"):
            return "prime"
        return None

    def _production_line_validprime_column(self) -> Optional[str]:
        if self._column_exists("u_aml", "u_validprime"):
            return "u_validprime"
        if self._column_exists("u_aml", "validprime"):
            return "validprime"
        return None

    def _ensure_intersol_regularizations_table(self) -> None:
        """Create u_intersol_regularizacoes table if it does not exist."""
        ddl = (
            "IF OBJECT_ID('dbo.u_intersol_regularizacoes', 'U') IS NULL "
            "BEGIN "
            "CREATE TABLE dbo.u_intersol_regularizacoes ("
            "    u_intersol_regularizacoesstamp CHAR(25) NOT NULL PRIMARY KEY,"
            "    ano INT NOT NULL,"
            "    mes INT NOT NULL,"
            "    no INT NOT NULL,"
            "    nome NVARCHAR(60) NOT NULL,"
            "    obs NVARCHAR(250) NOT NULL DEFAULT(''),"
            "    valor DECIMAL(18, 2) NOT NULL,"
            "    ousrinis NVARCHAR(30) NULL,"
            "    ousrdata DATETIME NULL,"
            "    ousrhora NVARCHAR(8) NULL,"
            "    usrinis NVARCHAR(30) NULL,"
            "    usrdata DATETIME NULL,"
            "    usrhora NVARCHAR(8) NULL"
            "); "
            "CREATE INDEX IX_u_intersol_regularizacoes_periodo "
            "ON dbo.u_intersol_regularizacoes (ano, mes, no); "
            "END"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(ddl)
                conn.commit()
        except Exception:
            return

    def fetch_user_by_credentials(self, username: str, password: str) -> Optional[Dict[str, str]]:
        """Return the user row if credentials match, otherwise None."""
        query = (
            "SELECT usercode, username, u_planning, u_admin, U_ADMINIS AS u_adminis, U_TEAMS AS u_teams, "
            "U_DE AS u_de, U_ES AS u_es, U_FR AS u_fr, U_IA AS u_ia, U_IC AS u_ic, U_IL AS u_il, U_MA AS u_ma, U_PT AS u_pt "
            "FROM US "
            "WHERE usercode = ? AND aextpw = ?"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (username, password))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_user_by_code(self, username: str) -> Optional[Dict[str, str]]:
        """Return the user row by code if it exists."""
        query = (
            "SELECT usercode, username, u_planning, u_admin, U_ADMINIS AS u_adminis, U_TEAMS AS u_teams, "
            "U_DE AS u_de, U_ES AS u_es, U_FR AS u_fr, U_IA AS u_ia, U_IC AS u_ic, U_IL AS u_il, U_MA AS u_ma, U_PT AS u_pt "
            "FROM US "
            "WHERE usercode = ?"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (username,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc



    def fetch_assignments_for_projects(
        self,
        start_date: date,
        end_date: date,
        project_codes: Iterable[str],
    ) -> list[Dict[str, object]]:
        """Return planning assignments for the provided projects within the date range."""
        codes = [code for code in project_codes if code]
        if not codes:
            return []
        placeholders = ", ".join(["?"] * len(codes))
        query = (
            "SELECT plano.u_planostamp, plano.processo, plano.data, plano.fref, plano.fixo, plano.premio, plano.rep, "
            "fref.nmfref, fref.u_planning, "
            "CASE WHEN EXISTS (SELECT 1 FROM u_lplano AS linhas WHERE linhas.u_planostamp = plano.u_planostamp) "
            "THEN 1 ELSE 0 END AS has_lines "
            "FROM u_plano AS plano "
            "LEFT JOIN fref ON fref.fref = plano.fref "
            "WHERE (COALESCE(TRY_CONVERT(date, plano.data), TRY_CONVERT(date, plano.data, 104), TRY_CONVERT(date, plano.data, 103)) BETWEEN ? AND ?) "
            f"AND plano.processo IN ({placeholders})"
        )
        params: list[object] = [start_date, end_date, *codes]
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_production_records(
        self,
        am_stamp: str | None = None,
        plan_stamp: str | None = None,
        team_code: str | None = None,
        project_code: str | None = None,
        assignment_date: date | None = None,
    ) -> list[dict[str, object]]:
        """Fetch production records from u_am."""
        base_select = (
            "SELECT u_amstamp, fref, processo, data, dgeral, qtt, chefe, confirmado, fechado, "
            "kgferro, preparacao, obs, m3bomba, m2serragem, preparacao2, m3betao, litem, valor, "
            "ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada, pastilha, valorfixo, "
            "premio, acabamento, valorun, planostamp, "
            "ISNULL((SELECT SUM(ISNULL(qtt, 0)) FROM u_aml WHERE u_aml.u_amstamp = u_am.u_amstamp), 0) AS lines_qtt_total, "
            "ISNULL((SELECT SUM(ISNULL(kgferro, 0)) FROM u_aml WHERE u_aml.u_amstamp = u_am.u_amstamp), 0) AS lines_kgferro_total, "
            "ISNULL((SELECT SUM(ISNULL(m2serragem, 0)) FROM u_aml WHERE u_aml.u_amstamp = u_am.u_amstamp), 0) AS lines_m2serragem_total "
            "FROM u_am "
        )
        if am_stamp:
            query = base_select + "WHERE u_amstamp = ?"
            params = (am_stamp,)
        elif plan_stamp:
            query = base_select + "WHERE planostamp = ?"
            params = (plan_stamp,)
        elif team_code and project_code and assignment_date is not None:
            query = (
                base_select
                + "WHERE fref = ? AND processo = ? AND COALESCE(TRY_CONVERT(date, data), TRY_CONVERT(date, data, 104), TRY_CONVERT(date, data, 103)) = ?"
            )
            params = (team_code, project_code, assignment_date)
        else:
            raise ValueError('Provide am_stamp, plan_stamp or team_code, project_code and assignment_date')
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_finishing_refs(self) -> list[str]:
        """Return available finishing refs from V_FINITIONS."""
        query = (
            "SELECT DISTINCT LTRIM(RTRIM(REF)) AS ref "
            "FROM V_FINITIONS "
            "WHERE REF IS NOT NULL AND LTRIM(RTRIM(REF)) <> '' "
            "ORDER BY LTRIM(RTRIM(REF))"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                if not rows:
                    return []
                values: list[str] = []
                for row in rows:
                    value = str(row[0]).strip() if row and row[0] is not None else ""
                    if value:
                        values.append(value)
                return values
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_plan_by_stamp(self, plan_stamp: str) -> Optional[Dict[str, object]]:
        """Return a single u_plano row by its stamp."""
        query = (
            "SELECT plano.u_planostamp, plano.data, plano.fref, plano.processo, plano.fixo, plano.premio, plano.rep, "
            "fref.nmfref AS fref_name "
            "FROM u_plano AS plano "
            "LEFT JOIN fref ON fref.fref = plano.fref "
            "WHERE plano.u_planostamp = ?"
        )
        normalized = plan_stamp.upper()
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (normalized,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_maintenance_for_month(self, year: int, month: int) -> list[Dict[str, object]]:
        """Fetch maintenance rows for a given year/month."""
        query = "SELECT u_manstamp, no, nome, ano, mes, valor FROM u_man WHERE ano = ? AND mes = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (year, month))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_maintenance_record(self, employee_number: int, employee_name: str, year: int, month: int, value: Decimal | float | int) -> None:
        """Insert a maintenance record into u_man."""
        stamp = uuid.uuid4().hex.upper()[:25]
        query = "INSERT INTO u_man (u_manstamp, no, nome, ano, mes, valor) VALUES (?, ?, ?, ?, ?, ?)"
        params = (stamp, employee_number, employee_name, year, month, float(value))
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_maintenance_record(self, employee_number: int, year: int, month: int, value: Decimal | float | int) -> int:
        """Update maintenance value; returns affected rows."""
        query = "UPDATE u_man SET valor = ? WHERE no = ? AND ano = ? AND mes = ?"
        params = (float(value), employee_number, year, month)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                affected = cursor.rowcount
                if affected:
                    conn.commit()
                return affected
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_monthly_production_rows(self, start_date: date, end_date: date) -> list[Dict[str, object]]:
        """Fetch closed production records and their lines within a month."""
        prime_column = self._production_line_prime_column()
        validprime_column = self._production_line_validprime_column()
        prime_select = f"aml.[{prime_column}] AS aml_prime, " if prime_column else "CAST(0 AS decimal(18,2)) AS aml_prime, "
        validprime_select = f"aml.[{validprime_column}] AS aml_validprime, " if validprime_column else "CAST(0 AS bit) AS aml_validprime, "
        query = (
            "SELECT am.u_amstamp, am.fref, fref.nmfref AS fref_name, am.processo, am.data, am.qtt AS am_qtt, "
            "am.kgferro AS am_kgferro, am.m2serragem AS am_m2serragem, am.valorfixo, am.premio, am.litem, am.acabamento, am.fechado, "
            "aml.u_amlstamp, aml.no, aml.nome, aml.qtt AS aml_qtt, aml.kgferro AS aml_kgferro, aml.m2serragem AS aml_m2serragem, "
            f"{prime_select}{validprime_select}"
            "st.epv5, COALESCE(ve.chefe, ut.chefe, 0) AS chefe, opc.u_tpdep "
            "FROM u_am AS am "
            "JOIN u_aml AS aml ON aml.u_amstamp = am.u_amstamp "
            "LEFT JOIN st ON st.ref = am.acabamento "
            "LEFT JOIN fref ON fref.fref = am.fref "
            "LEFT JOIN OPC AS opc ON opc.processo = am.processo "
            "LEFT JOIN v_equipas AS ve ON ve.fref = am.fref AND ve.no = aml.no "
            "    AND COALESCE(TRY_CONVERT(date, ve.data), TRY_CONVERT(date, ve.data, 104), TRY_CONVERT(date, ve.data, 103)) = "
            "        COALESCE(TRY_CONVERT(date, am.data), TRY_CONVERT(date, am.data, 104), TRY_CONVERT(date, am.data, 103)) "
            "OUTER APPLY ("
            "    SELECT TOP 1 u_team.chefe "
            "    FROM u_team "
            "    WHERE u_team.fref = am.fref "
            "      AND u_team.no = aml.no "
            "      AND CAST(u_team.dataini AS DATE) <= COALESCE(TRY_CONVERT(date, am.data), TRY_CONVERT(date, am.data, 104), TRY_CONVERT(date, am.data, 103)) "
            "      AND (u_team.datafim IS NULL OR CAST(u_team.datafim AS DATE) = '1900-01-01' OR CAST(u_team.datafim AS DATE) >= COALESCE(TRY_CONVERT(date, am.data), TRY_CONVERT(date, am.data, 104), TRY_CONVERT(date, am.data, 103))) "
            "    ORDER BY CAST(u_team.dataini AS DATE) DESC, u_team.u_teamstamp DESC"
            ") AS ut "
            "WHERE am.fechado = 1 "
            "AND (COALESCE(TRY_CONVERT(date, am.data), TRY_CONVERT(date, am.data, 104), TRY_CONVERT(date, am.data, 103)) BETWEEN ? AND ?)"
        )
        params = (start_date, end_date)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def _ensure_intersol_roles_table(self) -> None:
        """Create u_intersol_roles table if it does not exist."""
        ddl = (
            "IF OBJECT_ID('dbo.u_intersol_roles', 'U') IS NULL "
            "BEGIN "
            "CREATE TABLE dbo.u_intersol_roles ("
            "    no INT NOT NULL PRIMARY KEY,"
            "    role NVARCHAR(40) NOT NULL,"
            "    is_depot_manager BIT NOT NULL DEFAULT(0)"
            "); "
            "END"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(ddl)
                conn.commit()
        except Exception:
            # Best-effort: ignore if lacking permissions
            return

    def fetch_intersol_roles(self) -> list[Dict[str, object]]:
        """Retrieve configured INTERSOL roles/depot manager flags."""
        self._ensure_intersol_roles_table()
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT no, role, is_depot_manager FROM u_intersol_roles ORDER BY role, no")
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_intersol_regularizations(
        self,
        year: int,
        month: int,
        employee_number: str | int | None = None,
        employee_name: str | None = None,
    ) -> list[Dict[str, object]]:
        """Retrieve INTERSOL payroll regularizations for a given month."""
        self._ensure_intersol_regularizations_table()
        query = (
            "SELECT u_intersol_regularizacoesstamp, ano, mes, no, nome, obs, valor, "
            "ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora "
            "FROM u_intersol_regularizacoes "
            "WHERE ano = ? AND mes = ?"
        )
        params: list[object] = [year, month]
        if employee_number is not None:
            query += " AND no = ?"
            params.append(int(employee_number))
        if employee_name:
            query += " AND UPPER(LTRIM(RTRIM(nome))) = UPPER(LTRIM(RTRIM(?)))"
            params.append(employee_name)
        query += " ORDER BY nome, no, obs, u_intersol_regularizacoesstamp"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_intersol_regularization_by_stamp(self, regularization_stamp: str) -> Dict[str, object] | None:
        """Return a single INTERSOL payroll regularization row by stamp."""
        self._ensure_intersol_regularizations_table()
        query = (
            "SELECT u_intersol_regularizacoesstamp, ano, mes, no, nome, obs, valor, "
            "ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora "
            "FROM u_intersol_regularizacoes "
            "WHERE u_intersol_regularizacoesstamp = ?"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (regularization_stamp,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_intersol_regularization(self, record: dict[str, object]) -> None:
        """Insert a row into u_intersol_regularizacoes."""
        self._ensure_intersol_regularizations_table()
        required_fields = [
            "u_intersol_regularizacoesstamp",
            "ano",
            "mes",
            "no",
            "nome",
            "obs",
            "valor",
            "ousrinis",
            "ousrdata",
            "ousrhora",
            "usrinis",
            "usrdata",
            "usrhora",
        ]
        missing = [field for field in required_fields if field not in record]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        columns_sql = ", ".join(required_fields)
        placeholders = ", ".join(["?"] * len(required_fields))
        values = [record[field] for field in required_fields]
        query = f"INSERT INTO u_intersol_regularizacoes ({columns_sql}) VALUES ({placeholders})"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(values))
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_intersol_regularization(self, regularization_stamp: str, updates: dict[str, object]) -> int:
        """Update a u_intersol_regularizacoes row; returns affected rows."""
        self._ensure_intersol_regularizations_table()
        if not updates:
            raise ValueError("No updates provided")
        disallowed = {"u_intersol_regularizacoesstamp", "ousrinis", "ousrdata", "ousrhora"}
        set_clauses: list[str] = []
        params: list[object] = []
        for key, value in updates.items():
            if key in disallowed:
                continue
            set_clauses.append(f"{key} = ?")
            params.append(value)
        if not set_clauses:
            return 0
        params.append(regularization_stamp)
        query = f"UPDATE u_intersol_regularizacoes SET {', '.join(set_clauses)} WHERE u_intersol_regularizacoesstamp = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                updated = cursor.rowcount
                if updated:
                    conn.commit()
                return updated
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_intersol_regularization(self, regularization_stamp: str) -> int:
        """Delete a row from u_intersol_regularizacoes."""
        self._ensure_intersol_regularizations_table()
        query = "DELETE FROM u_intersol_regularizacoes WHERE u_intersol_regularizacoesstamp = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (regularization_stamp,))
                deleted = cursor.rowcount
                if deleted:
                    conn.commit()
                return deleted
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def upsert_intersol_role(self, employee_number: int, role: str, is_depot_manager: bool = False) -> None:
        """Insert or update an INTERSOL role mapping."""
        self._ensure_intersol_roles_table()
        query = (
            "MERGE u_intersol_roles AS target "
            "USING (VALUES (?, ?, ?)) AS src(no, role, is_depot_manager) "
            "ON target.no = src.no "
            "WHEN MATCHED THEN UPDATE SET role = src.role, is_depot_manager = src.is_depot_manager "
            "WHEN NOT MATCHED THEN INSERT (no, role, is_depot_manager) VALUES (src.no, src.role, src.is_depot_manager);"
        )
        params = (employee_number, role, 1 if is_depot_manager else 0)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_intersol_role(self, employee_number: int) -> bool:
        """Delete an INTERSOL role mapping."""
        self._ensure_intersol_roles_table()
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM u_intersol_roles WHERE no = ?", (employee_number,))
                deleted = cursor.rowcount > 0
                if deleted:
                    conn.commit()
                return deleted
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_plan_values(
        self,
        plan_stamp: str,
        *,
        fixed_value: Decimal | float | None = None,
        bonus_value: Decimal | float | None = None,
    ) -> int:
        """Update fixo/premio on u_plano; returns affected rows."""
        fields: list[str] = []
        params: list[object] = []
        if fixed_value is not None:
            fields.append("fixo = ?")
            params.append(float(fixed_value))
        if bonus_value is not None:
            fields.append("premio = ?")
            params.append(float(bonus_value))
        if not fields:
            return 0
        params.append(plan_stamp.upper())
        query = f"UPDATE u_plano SET {', '.join(fields)} WHERE u_planostamp = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                affected = cursor.rowcount
                if affected:
                    conn.commit()
                return affected
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def close_fulfilled_production_records(self, week_start: date, week_end: date) -> tuple[int, list[str]]:
        """Set fechado=1 for production records whose quantities match their lines."""
        query = (
            "WITH line_totals AS ("
            "    SELECT u_amstamp,"
            "           SUM(ISNULL(qtt, 0)) AS total_qtt,"
            "           SUM(ISNULL(kgferro, 0)) AS total_kgferro,"
            "           SUM(ISNULL(m2serragem, 0)) AS total_m2serragem"
            "    FROM u_aml"
            "    GROUP BY u_amstamp"
            "), eligible AS ("
            "    SELECT am.u_amstamp"
            "    FROM u_am AS am"
            "    LEFT JOIN line_totals AS lt ON lt.u_amstamp = am.u_amstamp"
            "    WHERE am.fechado = 0"
            "      AND COALESCE(TRY_CONVERT(date, am.data), TRY_CONVERT(date, am.data, 104), TRY_CONVERT(date, am.data, 103)) BETWEEN ? AND ?"
            "      AND ("
            "            ABS(ISNULL(am.qtt, 0)) > 0.0001"
            "         OR ABS(ISNULL(am.kgferro, 0)) > 0.0001"
            "         OR ABS(ISNULL(am.m2serragem, 0)) > 0.0001"
            "      )"
            "      AND ABS(ISNULL(am.qtt, 0) - ISNULL(lt.total_qtt, 0)) <= 0.0001"
            "      AND ABS(ISNULL(am.kgferro, 0) - ISNULL(lt.total_kgferro, 0)) <= 0.0001"
            "      AND ABS(ISNULL(am.m2serragem, 0) - ISNULL(lt.total_m2serragem, 0)) <= 0.0001"
            ") "
            "UPDATE am"
            " SET fechado = 1"
            " OUTPUT INSERTED.planostamp"
            " FROM u_am AS am"
            " INNER JOIN eligible AS e ON e.u_amstamp = am.u_amstamp"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (week_start, week_end))
                rows = cursor.fetchall()
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
        plan_stamps: list[str] = []
        seen: set[str] = set()
        for row in rows:
            if not row:
                continue
            plan_stamp = str(row[0]).strip() if row[0] is not None else ""
            if not plan_stamp:
                continue
            plan_upper = plan_stamp.upper()
            if plan_upper in seen:
                continue
            seen.add(plan_upper)
            plan_stamps.append(plan_upper)
        return len(rows), plan_stamps

    def insert_production_record(self, record: dict[str, object]) -> None:
        """Insert a production record into u_am."""
        required_fields = [
            'u_amstamp', 'fref', 'processo', 'data', 'dgeral', 'qtt', 'chefe', 'confirmado',
            'fechado', 'kgferro', 'preparacao', 'obs', 'm3bomba', 'm2serragem', 'preparacao2',
            'm3betao', 'litem', 'valor', 'ousrinis', 'ousrdata', 'ousrhora', 'usrinis',
            'usrdata', 'usrhora', 'marcada', 'pastilha', 'valorfixo', 'premio', 'acabamento',
            'valorun', 'planostamp'
        ]
        missing = [field for field in required_fields if field not in record]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        columns = ', '.join(required_fields)
        placeholders = ', '.join(['?'] * len(required_fields))
        values = tuple(record[field] for field in required_fields)
        query = f"INSERT INTO u_am ({columns}) VALUES ({placeholders})"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_production_record(
        self,
        updates: dict[str, object],
        am_stamp: str | None = None,
        team_code: str | None = None,
        project_code: str | None = None,
        assignment_date: date | None = None,
    ) -> int:
        """Update production record(s) in u_am."""
        if not updates:
            raise ValueError('No updates provided')
        if am_stamp:
            where_clause = 'u_amstamp = ?'
            where_params = (am_stamp,)
        elif team_code and project_code and assignment_date is not None:
            where_clause = 'fref = ? AND processo = ? AND CAST(data AS DATE) = ?'
            where_params = (team_code, project_code, assignment_date)
        else:
            raise ValueError('Provide am_stamp or team_code, project_code and assignment_date')
        disallowed = {'u_amstamp'}
        set_clauses = []
        params: list[object] = []
        for key, value in updates.items():
            if key in disallowed:
                continue
            set_clauses.append(f"{key} = ?")
            params.append(value)
        if not set_clauses:
            return 0
        params.extend(where_params)
        query = f"UPDATE u_am SET {', '.join(set_clauses)} WHERE {where_clause}"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                updated = cursor.rowcount
                if updated:
                    conn.commit()
                return updated
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_production_record(
        self,
        am_stamp: str | None = None,
        team_code: str | None = None,
        project_code: str | None = None,
        assignment_date: date | None = None,
    ) -> int:
        """Delete production record(s) from u_am."""
        if am_stamp:
            where_clause = 'u_amstamp = ?'
            params = (am_stamp,)
        elif team_code and project_code and assignment_date is not None:
            where_clause = 'fref = ? AND processo = ? AND CAST(data AS DATE) = ?'
            params = (team_code, project_code, assignment_date)
        else:
            raise ValueError('Provide am_stamp or team_code, project_code and assignment_date')
        query = f"DELETE FROM u_am WHERE {where_clause}"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                deleted = cursor.rowcount
                if deleted:
                    conn.commit()
                return deleted
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_production_line_records(
        self,
        am_line_stamp: str | None = None,
        am_stamp: str | None = None,
    ) -> list[dict[str, object]]:
        """Fetch production line records (u_aml)."""
        prime_column = self._production_line_prime_column()
        prime_select = f"[{prime_column}] AS u_prime, " if prime_column else "CAST(0 AS decimal(18,2)) AS u_prime, "
        if am_line_stamp:
            query = (
                "SELECT u_amlstamp, u_amstamp, no, nome, qtt, fref, processo, data, litem, kgferro, m2serragem, "
                f"{prime_select}"
                "falta, "
                "preparacao, preprep, ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada, outros, presente, disponivel "
                "FROM u_aml WHERE u_amlstamp = ?"
            )
            params = (am_line_stamp,)
        elif am_stamp:
            query = (
                "SELECT u_amlstamp, u_amstamp, no, nome, qtt, fref, processo, data, litem, kgferro, m2serragem, "
                f"{prime_select}"
                "falta, "
                "preparacao, preprep, ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada, outros, presente, disponivel "
                "FROM u_aml WHERE u_amstamp = ?"
            )
            params = (am_stamp,)
        else:
            raise ValueError('Provide am_line_stamp or am_stamp')
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_production_line(self, record: dict[str, object]) -> None:
        """Insert a production line record into u_aml."""
        prime_column = self._production_line_prime_column()
        required_fields = [
            'u_amlstamp', 'u_amstamp', 'no', 'nome', 'qtt', 'fref', 'processo', 'data', 'litem', 'kgferro', 'm2serragem',
            'falta', 'preparacao', 'preprep', 'ousrinis', 'ousrdata', 'ousrhora', 'usrinis', 'usrdata', 'usrhora',
            'marcada', 'outros', 'presente', 'disponivel'
        ]
        missing = [field for field in required_fields if field not in record]
        if prime_column and 'u_prime' not in record and 'prime' not in record:
            missing.append('u_prime')
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        columns = list(required_fields)
        values = [record[field] for field in required_fields]
        if prime_column:
            columns.insert(11, prime_column)
            values.insert(11, record['u_prime'] if 'u_prime' in record else record.get('prime'))
        columns_sql = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        query = f"INSERT INTO u_aml ({columns_sql}) VALUES ({placeholders})"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(values))
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_production_line(
        self,
        updates: dict[str, object],
        am_line_stamp: str | None = None,
        am_stamp: str | None = None,
    ) -> int:
        """Update production line record(s) in u_aml."""
        if not updates:
            raise ValueError('No updates provided')
        if am_line_stamp:
            where_clause = 'u_amlstamp = ?'
            where_params = (am_line_stamp,)
        elif am_stamp:
            where_clause = 'u_amstamp = ?'
            where_params = (am_stamp,)
        else:
            raise ValueError('Provide am_line_stamp or am_stamp')
        disallowed = {'u_amlstamp'}
        set_clauses = []
        params: list[object] = []
        prime_column = self._production_line_prime_column()
        validprime_column = self._production_line_validprime_column()
        for key, value in updates.items():
            if key in disallowed:
                continue
            if key in {'u_prime', 'prime'}:
                if not prime_column:
                    continue
                key = prime_column
            if key in {'u_validprime', 'validprime'}:
                if not validprime_column:
                    continue
                key = validprime_column
            set_clauses.append(f"{key} = ?")
            params.append(value)
        if not set_clauses:
            return 0
        params.extend(where_params)
        query = f"UPDATE u_aml SET {', '.join(set_clauses)} WHERE {where_clause}"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                updated = cursor.rowcount
                if updated:
                    conn.commit()
                return updated
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_production_line(
        self,
        am_line_stamp: str | None = None,
        am_stamp: str | None = None,
    ) -> int:
        """Delete production line record(s) from u_aml."""
        if am_line_stamp:
            where_clause = 'u_amlstamp = ?'
            params = (am_line_stamp,)
        elif am_stamp:
            where_clause = 'u_amstamp = ?'
            params = (am_stamp,)
        else:
            raise ValueError('Provide am_line_stamp or am_stamp')
        query = f"DELETE FROM u_aml WHERE {where_clause}"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                deleted = cursor.rowcount
                if deleted:
                    conn.commit()
                return deleted
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_planning_assignment(
        self,
        plano_stamp: str,
        assignment_date: date,
        team_code: str,
        project_code: str,
        fixed_value: Decimal | float | int | None = None,
        bonus_value: Decimal | float | int | None = None,
    ) -> None:
        """Insert a planning assignment row into u_plano."""
        fixed_value = fixed_value if fixed_value is not None else 0
        bonus_value = bonus_value if bonus_value is not None else 0
        query = (
            "INSERT INTO u_plano (u_planostamp, data, fref, processo, fixo, premio, rep) "
            "VALUES (?, ?, ?, ?, ?, ?, 0)"
        )
        params = (plano_stamp, assignment_date, team_code, project_code, float(fixed_value), float(bonus_value))
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_plan_line(
        self,
        plan_stamp: str,
        budget_item_stamp: str,
        line_item: int,
        description: str,
        team_code: str,
        project_code: str,
        assignment_date: date,
        fixed_value: Decimal | float | int,
    ) -> str:
        """Insert a plan line row into u_lplano and return its generated stamp."""
        plan_line_stamp = uuid.uuid4().hex.upper()[:25]
        query = (
            "INSERT INTO u_lplano (u_lplanostamp, u_planostamp, bistamp, litem, dgeral, fref, processo, data, fixo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            plan_line_stamp,
            plan_stamp,
            budget_item_stamp,
            line_item,
            description,
            team_code,
            project_code,
            assignment_date,
            fixed_value,
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return plan_line_stamp
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_plan_lines(
        self,
        plan_stamp: str,
    ) -> list[Dict[str, object]]:
        """Return plan lines associated with the provided plan stamp."""
        if not plan_stamp:
            return []
        query = (
            "SELECT u_lplanostamp, u_planostamp, bistamp, litem, dgeral, fref, processo, data, fixo "
            "FROM u_lplano "
            "WHERE u_planostamp = ? "
            "ORDER BY litem"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (plan_stamp,))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                results: list[Dict[str, object]] = []
                for row in rows:
                    record: Dict[str, object] = {}
                    for idx, column in enumerate(columns):
                        value = row[idx]
                        if column == "fixo" and isinstance(value, Decimal):
                            value = float(value)
                        elif column in {"u_lplanostamp", "u_planostamp", "bistamp", "fref", "processo"} and value is not None:
                            value = str(value).strip().upper()
                        record[column] = value
                    results.append(record)
                return results
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_plan_lines_for_plans(
        self,
        plan_stamps: Iterable[str],
    ) -> dict[str, list[Dict[str, object]]]:
        """Return plan lines grouped by plan stamp for the provided plan stamps."""
        stamps = [str(stamp).strip().upper()[:25] for stamp in plan_stamps if stamp]
        if not stamps:
            return {}
        placeholders = ', '.join(['?'] * len(stamps))
        query = (
            "SELECT u_lplanostamp, u_planostamp, bistamp, litem, dgeral, fref, processo, data, fixo "
            f"FROM u_lplano WHERE u_planostamp IN ({placeholders}) "
            "ORDER BY u_planostamp, litem"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(stamps))
                rows = cursor.fetchall()
                if not rows:
                    return {stamp: [] for stamp in stamps}
                columns = [col[0].lower() for col in cursor.description]
                grouped: dict[str, list[Dict[str, object]]] = {stamp: [] for stamp in stamps}
                for row in rows:
                    record: Dict[str, object] = {}
                    for idx, column in enumerate(columns):
                        value = row[idx]
                        if column == 'fixo' and isinstance(value, Decimal):
                            value = float(value)
                        elif column == 'data' and isinstance(value, (date, datetime)):
                            value = value.isoformat()
                        elif column in {'u_lplanostamp', 'u_planostamp', 'bistamp', 'fref', 'processo'} and value is not None:
                            value = str(value).strip().upper()
                        record[column] = value
                    record['plan_stamp'] = record.get('u_planostamp') or ''
                    stamp = record['plan_stamp']
                    if stamp:
                        grouped.setdefault(stamp, []).append(record)
                for stamp in stamps:
                    grouped.setdefault(stamp, [])
                return grouped
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc


    def delete_plan_line(
        self,
        line_stamp: str,
    ) -> None:
        """Remove a plan line row from u_lplano by its stamp."""
        query = (
            "DELETE FROM u_lplano WHERE u_lplanostamp = ?"
        )
        params = (line_stamp,)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_planning_assignment(
        self,
        assignment_date: date,
        team_code: str,
        project_code: str,
    ) -> None:
        """Remove a planning assignment row from u_plano and its plan lines."""
        select_query = (
            "SELECT u_planostamp FROM u_plano WHERE data = ? AND fref = ? AND processo = ?"
        )
        delete_plan_query = (
            "DELETE FROM u_plano WHERE data = ? AND fref = ? AND processo = ?"
        )
        delete_lines_query = (
            "DELETE FROM u_lplano WHERE u_planostamp = ?"
        )
        params = (assignment_date, team_code, project_code)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(select_query, params)
                rows = cursor.fetchall() or []
                plan_stamps = []
                for row in rows:
                    if not row:
                        continue
                    stamp = row[0]
                    if stamp:
                        plan_stamps.append(str(stamp).strip())
                cursor.execute(delete_plan_query, params)
                for stamp in plan_stamps:
                    if not stamp:
                        continue
                    cursor.execute(delete_lines_query, (stamp,))
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_project_budget_items(
        self,
        project_code: str,
    ) -> list[Dict[str, object]]:
        """Return adjudicated budget items for the provided project."""
        if not project_code:
            return []
        core_code = project_code.strip()
        if len(core_code) < 3:
            return []
        core_code = core_code[2:]
        if not core_code:
            return []
        core_code = core_code.upper()
        query = (
            "SELECT OBRAM, LITEM, DGERAL, QTT, UNIDADE, QTT2, BISTAMP "
            "FROM v_bi_ee "
            "WHERE UPPER(RIGHT(OBRAM, LEN(OBRAM) - 2)) = ? "
            "ORDER BY LITEM"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (core_code,))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                items: list[Dict[str, object]] = []
                for row in rows:
                    record: Dict[str, object] = {}
                    for idx, column in enumerate(columns):
                        value = row[idx]
                        if column in {"qtt", "qtt2"} and value is not None:
                            try:
                                value = float(value)
                            except (TypeError, ValueError):
                                value = None
                        elif column == "bistamp" and value is not None:
                            value = str(value).strip().upper()
                        record[column] = value
                    items.append(record)

                return items
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_projects_for_week(
        self,
        start_date: date,
        end_date: date,
        markets: Optional[Iterable[str]] = None,
        include_external_planning: bool = False,
    ) -> list[Dict[str, object]]:
        """Return projects whose schedule overlaps the provided week range."""
        opc_overlap = (
            "(COALESCE(TRY_CONVERT(date, opc.datai), TRY_CONVERT(date, opc.datai, 104), TRY_CONVERT(date, opc.datai, 103)) IS NULL "
            " OR COALESCE(TRY_CONVERT(date, opc.datai), TRY_CONVERT(date, opc.datai, 104), TRY_CONVERT(date, opc.datai, 103)) <= ?) "
            "AND (COALESCE(TRY_CONVERT(date, opc.dataf), TRY_CONVERT(date, opc.dataf, 104), TRY_CONVERT(date, opc.dataf, 103)) IS NULL "
            " OR COALESCE(TRY_CONVERT(date, opc.dataf), TRY_CONVERT(date, opc.dataf, 104), TRY_CONVERT(date, opc.dataf, 103)) >= ?)"
        )
        mn_overlap_exists = (
            "EXISTS (SELECT 1 FROM U_OPCMN mn "
            "WHERE mn.opcstamp = opc.opcstamp "
            "AND (COALESCE(TRY_CONVERT(date, mn.dataini), TRY_CONVERT(date, mn.dataini, 104), TRY_CONVERT(date, mn.dataini, 103)) IS NULL "
            "     OR COALESCE(TRY_CONVERT(date, mn.dataini), TRY_CONVERT(date, mn.dataini, 104), TRY_CONVERT(date, mn.dataini, 103)) <= ?) "
            "AND (COALESCE(TRY_CONVERT(date, mn.datafim), TRY_CONVERT(date, mn.datafim, 104), TRY_CONVERT(date, mn.datafim, 103)) IS NULL "
            "     OR COALESCE(TRY_CONVERT(date, mn.datafim), TRY_CONVERT(date, mn.datafim, 104), TRY_CONVERT(date, mn.datafim, 103)) >= ?))"
        )
        base_filters: list[str] = []
        market_list: list[str] = []
        if markets:
            market_list = list(markets)
            if market_list:
                placeholders = ", ".join(["?"] * len(market_list))
                origin_filter = f"opc.u_origem IN ({placeholders})"
                if include_external_planning:
                    origin_filter = f"({origin_filter} OR ISNULL(opc.u_planext, 0) = 1)"
                base_filters.append(origin_filter)
        where_clause_parts = []
        if base_filters:
            where_clause_parts.append(" AND ".join(base_filters))
        where_clause_parts.append(f"(({opc_overlap}) OR ({mn_overlap_exists}))")
        where_clause = " AND ".join(where_clause_parts)
        query = (
            "SELECT opc.processo, opc.nome, opc.descricao, opc.u_origem, opc.datai, opc.dataf, opc.opcstamp, "
            "ISNULL(opc.u_planext, 0) AS u_planext "
            "FROM OPC opc "
            f"WHERE {where_clause} "
            "ORDER BY opc.nome"
        )
        # Build params in the same order placeholders appear in the WHERE clause:
        # First market values (if any), then the four date bounds for opc/maintenance overlaps
        params: list[object] = []
        if market_list:
            params.extend(market_list)
        params.extend([end_date, start_date, end_date, start_date])
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                results = []
                for row in rows:
                    results.append({columns[idx]: value for idx, value in enumerate(row)})
                return results
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc



    def fetch_maintenance_for_projects(
        self,
        start_date: date,
        end_date: date,
        opcstamps: Iterable[str],
    ) -> list[Dict[str, object]]:
        """Return maintenance windows (U_OPCMN) overlapping the provided range for given OPC stamps.

        A row qualifies if (dataini <= end_date) and (datafim >= start_date). NULLs are treated as open-ended.
        """
        stamps = [str(stamp).strip().upper() for stamp in opcstamps if stamp]
        if not stamps:
            return []
        placeholders = ", ".join(["?"] * len(stamps))
        query = (
            "SELECT opcstamp, dataini, datafim "
            "FROM U_OPCMN "
            "WHERE (COALESCE(TRY_CONVERT(date, dataini), TRY_CONVERT(date, dataini, 104), TRY_CONVERT(date, dataini, 103)) IS NULL "
            "       OR COALESCE(TRY_CONVERT(date, dataini), TRY_CONVERT(date, dataini, 104), TRY_CONVERT(date, dataini, 103)) <= ?) "
            "AND (COALESCE(TRY_CONVERT(date, datafim), TRY_CONVERT(date, datafim, 104), TRY_CONVERT(date, datafim, 103)) IS NULL "
            "       OR COALESCE(TRY_CONVERT(date, datafim), TRY_CONVERT(date, datafim, 104), TRY_CONVERT(date, datafim, 103)) >= ?) "
            f"AND opcstamp IN ({placeholders}) "
            "ORDER BY opcstamp, dataini"
        )
        params: list[object] = [end_date, start_date, *stamps]
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
    def fetch_planning_teams(self) -> list[Dict[str, object]]:
        """Return planning-enabled teams grouped by planning bucket."""
        columns_to_try = ("planning", "u_planning")
        last_missing_column_error: Exception | None = None
        # Allowlist extra teams that must appear even if u_plano is not set
        extra_planning_frefs: tuple[str, ...] = ("IS ALSACE 01", "IS LORRAINE 01", "IS CHAMPAGNE 01")
        extra_normalised = tuple(code.upper() for code in extra_planning_frefs)
        extra_clause = " OR UPPER(LTRIM(RTRIM(fref))) IN ({placeholders})".format(
            placeholders=", ".join(["?"] * len(extra_normalised))
        )
        for column in columns_to_try:
            query = (
                "SELECT fref, nmfref, {column} AS planning "
                "FROM FREF "
                f"WHERE ISNULL(u_plano, 0) != 0{extra_clause} "
                "ORDER BY {column}, nmfref"
            ).format(column=column)
            try:
                with self.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, extra_normalised)
                    rows = cursor.fetchall()
                    if not rows:
                        return []
                    columns = [col[0].lower() for col in cursor.description]
                    return [
                        {columns[idx]: value for idx, value in enumerate(row)}
                        for row in rows
                    ]
            except Exception as exc:
                message = str(exc)
                if f"Invalid column name '{column}'" in message:
                    last_missing_column_error = exc
                    continue
                raise RuntimeError(message) from exc
        if last_missing_column_error is not None:
            raise RuntimeError(str(last_missing_column_error)) from last_missing_column_error
        return []


    def fetch_all_teams(self) -> list[Dict[str, object]]:
        """Return all teams grouped by their planning bucket."""
        query = (
            "SELECT fref, nmfref, u_planning, frefstamp "
            "FROM FREF "
            "WHERE ISNULL(u_plano, 0) = 1 "
            "ORDER BY ISNULL(u_planning, ''), nmfref"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_team_members_for_date(self, target_date: date) -> list[Dict[str, object]]:
        """Return active team members for a given date."""
        query = (
            "SELECT u_teamstamp, fref, frefstamp, no, nome, chefe, dataini, datafim, ausente, marcada, origem "
            "FROM u_team "
            "WHERE CAST(dataini AS DATE) <= ? "
            "AND (datafim IS NULL OR CAST(datafim AS DATE) = '1900-01-01' OR CAST(datafim AS DATE) >= ?)"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (target_date, target_date))
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_unassigned_employees(self, target_date: date) -> list[Dict[str, object]]:
        """Return employees without an active team assignment for the date."""
        query = (
            "SELECT pe.bdados, pe.no, pe.cval4 "
            "FROM v_pe AS pe "
            "WHERE ISNULL(pe.cval4, '') <> '' "
            "AND ISNULL(pe.u_prod, 0) = 1 "
            "AND NOT EXISTS ("
                "    SELECT 1 "
                "    FROM u_team AS ut "
                "    WHERE ut.no = pe.no "
            "      AND ISNULL(ut.origem, '') = ISNULL(pe.bdados, '') "
            "      AND CAST(ut.dataini AS DATE) <= ? "
            "      AND (ut.datafim IS NULL OR CAST(ut.datafim AS DATE) = '1900-01-01' OR CAST(ut.datafim AS DATE) >= ?)"
            ") "
            "ORDER BY pe.cval4"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (target_date, target_date))
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc



    def fetch_employee_details(self, employee_number: str, employee_origin: str | None = None) -> Dict[str, object] | None:
        """Return basic details for an employee from v_pe."""
        query = (
            "SELECT pe.no, pe.cval4, pe.bdados "
            "FROM v_pe AS pe "
            "WHERE pe.no = ?"
        )
        params: list[object] = [employee_number]
        if employee_origin:
            query += " AND ISNULL(pe.bdados, '') = ?"
            params.append(employee_origin)
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc


    def fetch_employees_basic(self) -> list[dict[str, object]]:
        """Return list of employees from v_pe with non-empty cval4."""
        query = (
            "SELECT pe.no, pe.cval4 FROM v_pe AS pe WHERE ISNULL(pe.cval4, '') <> '' ORDER BY pe.cval4"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_absences_for_date(self, reference_date: date) -> list[Dict[str, object]]:
        """Return present and future absences based on a reference date."""
        query = (
            "SELECT u_ausenciasstamp, no, nome, dataini, datafim, obs, "
            "ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada "
            "FROM u_ausencias "
            "WHERE CAST(datafim AS DATE) >= ? "
            "ORDER BY CAST(dataini AS DATE), nome, no"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (reference_date,))
                rows = cursor.fetchall()
                if not rows:
                    return []
                columns = [col[0].lower() for col in cursor.description]
                return [{columns[idx]: value for idx, value in enumerate(row)} for row in rows]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_absence_by_stamp(self, absence_stamp: str) -> Dict[str, object] | None:
        """Return a single absence row by stamp."""
        query = (
            "SELECT u_ausenciasstamp, no, nome, dataini, datafim, obs, "
            "ousrinis, ousrdata, ousrhora, usrinis, usrdata, usrhora, marcada "
            "FROM u_ausencias "
            "WHERE u_ausenciasstamp = ?"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (absence_stamp,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def insert_absence(self, record: dict[str, object]) -> None:
        """Insert a row into u_ausencias."""
        required_fields = [
            'u_ausenciasstamp',
            'no',
            'nome',
            'dataini',
            'datafim',
            'obs',
            'ousrinis',
            'ousrdata',
            'ousrhora',
            'usrinis',
            'usrdata',
            'usrhora',
            'marcada',
        ]
        missing = [field for field in required_fields if field not in record]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        columns_sql = ', '.join(required_fields)
        placeholders = ', '.join(['?'] * len(required_fields))
        values = [record[field] for field in required_fields]
        query = f"INSERT INTO u_ausencias ({columns_sql}) VALUES ({placeholders})"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(values))
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def update_absence(self, absence_stamp: str, updates: dict[str, object]) -> int:
        """Update a u_ausencias row; returns affected rows."""
        if not updates:
            raise ValueError('No updates provided')
        disallowed = {'u_ausenciasstamp', 'ousrinis', 'ousrdata', 'ousrhora'}
        set_clauses: list[str] = []
        params: list[object] = []
        for key, value in updates.items():
            if key in disallowed:
                continue
            set_clauses.append(f"{key} = ?")
            params.append(value)
        if not set_clauses:
            return 0
        params.append(absence_stamp)
        query = f"UPDATE u_ausencias SET {', '.join(set_clauses)} WHERE u_ausenciasstamp = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                updated = cursor.rowcount
                if updated:
                    conn.commit()
                return updated
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def delete_absence(self, absence_stamp: str) -> int:
        """Delete a row from u_ausencias."""
        query = "DELETE FROM u_ausencias WHERE u_ausenciasstamp = ?"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (absence_stamp,))
                deleted = cursor.rowcount
                if deleted:
                    conn.commit()
                return deleted
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_team_by_code(self, team_code: str) -> Dict[str, object] | None:
        """Return team metadata by code (filtered to planning-enabled teams)."""
        query = (
            "SELECT fref, nmfref, u_planning, frefstamp "
            "FROM FREF "
            "WHERE fref = ? AND ISNULL(u_plano, 0) = 1"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (team_code,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0].lower() for col in cursor.description]
                return {columns[idx]: value for idx, value in enumerate(row)}
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_employee_memberships(self, employee_number: str, employee_origin: str | None = None) -> list[Dict[str, object]]:
        """Return membership records for an employee ordered by start date."""
        query = (
            "SELECT u_teamstamp, fref, frefstamp, no, nome, chefe, dataini, datafim, origem "
            "FROM u_team "
            "WHERE no = ? "
        )
        params: list[object] = [employee_number]
        if employee_origin:
            query += "AND ISNULL(origem, '') = ? "
            params.append(employee_origin)
        query += "ORDER BY dataini"
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def fetch_team_leads_for_period(self, team_code: str, period_start: date, period_end: date | None) -> list[Dict[str, object]]:
        """Return lead records for a team that overlap the provided period."""
        effective_end = period_end or period_start
        query = (
            "SELECT u_teamstamp, fref, frefstamp, no, nome, chefe, dataini, datafim, origem "
            "FROM u_team "
            "WHERE fref = ? AND chefe = 1 "
            "AND dataini <= ? "
            "AND (datafim IS NULL OR CAST(datafim AS DATE) = '1900-01-01' OR CAST(datafim AS DATE) >= ?)"
        )
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (team_code, effective_end, period_start))
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                return [
                    {columns[idx]: value for idx, value in enumerate(row)}
                    for row in rows
                ]
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    def apply_team_membership_operations(self, operations: list[Dict[str, object]]) -> None:
        """Execute a list of membership operations inside a single transaction."""
        if not operations:
            return
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                for operation in operations:
                    op_type = operation.get("type")
                    if op_type == "update_period":
                        end_date = operation.get("end")
                        end_value = "1900-01-01" if end_date is None else end_date
                        cursor.execute(
                            "UPDATE u_team SET dataini = ?, datafim = ? WHERE u_teamstamp = ?",
                            (operation.get("start"), end_value, operation.get("stamp"))
                        )
                    elif op_type == "update_role":
                        cursor.execute(
                            "UPDATE u_team SET chefe = ? WHERE u_teamstamp = ?",
                            (1 if operation.get("chefe") else 0, operation.get("stamp"))
                        )
                    elif op_type == "delete":
                        cursor.execute(
                            "DELETE FROM u_team WHERE u_teamstamp = ?",
                            (operation.get("stamp"),)
                        )
                    elif op_type == "insert":
                        end_date = operation.get("end")
                        end_value = "1900-01-01" if end_date is None else end_date
                        now = datetime.now()
                        date_value = now.date()
                        time_value = now.strftime("%H:%M:%S")
                        cursor.execute(
                            "INSERT INTO u_team (u_teamstamp, frefstamp, fref, no, nome, chefe, dataini, datafim, ausente, marcada, origem, ousrinis, usrinis, ousrdata, usrdata, ousrhora, usrhora) "
                            "VALUES (LEFT(REPLACE(CONVERT(NVARCHAR(36), NEWID()), '-', ''), 25), ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'ADM', 'ADM', ?, ?, ?, ?)",
                            (
                                operation.get("team_stamp"),
                                operation.get("team_code"),
                                operation.get("employee_number"),
                                operation.get("employee_name"),
                                1 if operation.get("chefe") else 0,
                                operation.get("start"),
                                end_value,
                                operation.get("origin"),
                                date_value,
                                date_value,
                                time_value,
                                time_value,
                            )
                        )
                    else:
                        raise RuntimeError(f"Unsupported operation '{op_type}'")
                conn.commit()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc



database = Database()
