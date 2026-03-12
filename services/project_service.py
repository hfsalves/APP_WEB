from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import text

from models import db


DEFAULT_PROJECT_STATES = [
    {"CODIGO": 1, "NOME": "Planeado", "ORDEM": 10, "COR": "secondary", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 2, "NOME": "Em curso", "ORDEM": 20, "COR": "primary", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 3, "NOME": "Em espera", "ORDEM": 30, "COR": "warning", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 4, "NOME": "Concluido", "ORDEM": 40, "COR": "success", "FINAL": 1, "ATIVO": 1},
    {"CODIGO": 5, "NOME": "Cancelado", "ORDEM": 50, "COR": "danger", "FINAL": 1, "ATIVO": 1},
]

DEFAULT_TASK_STATES = [
    {"CODIGO": 1, "NOME": "Por fazer", "ORDEM": 10, "COR": "secondary", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 2, "NOME": "Em curso", "ORDEM": 20, "COR": "primary", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 3, "NOME": "Em espera", "ORDEM": 30, "COR": "warning", "FINAL": 0, "ATIVO": 1},
    {"CODIGO": 4, "NOME": "Concluida", "ORDEM": 40, "COR": "success", "FINAL": 1, "ATIVO": 1},
    {"CODIGO": 5, "NOME": "Cancelada", "ORDEM": 50, "COR": "danger", "FINAL": 1, "ATIVO": 1},
]

DEFAULT_PRIORITIES = [
    {"CODIGO": 1, "NOME": "Baixa", "COR": "secondary"},
    {"CODIGO": 2, "NOME": "Media", "COR": "primary"},
    {"CODIGO": 3, "NOME": "Alta", "COR": "warning"},
    {"CODIGO": 4, "NOME": "Urgente", "COR": "danger"},
]


class ProjectServiceError(Exception):
    pass


class ProjectValidationError(ProjectServiceError):
    pass


class ProjectNotFoundError(ProjectServiceError):
    pass


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _table_exists(table_name: str) -> bool:
    sql = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
        """
    )
    return bool(db.session.execute(sql, {"table_name": table_name}).scalar() or 0)


def _table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(
        text(
            """
            SELECT UPPER(COLUMN_NAME)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {str(row[0]).upper() for row in rows}


def _insert_if_missing(table_name: str, key_column: str, row_data: dict):
    cols = _table_columns(table_name)
    payload = {}

    if f"{table_name}STAMP".upper() in cols:
        payload[f"{table_name}STAMP"] = _new_stamp()
    elif f"{table_name.rstrip('S')}STAMP".upper() in cols:
        payload[f"{table_name.rstrip('S')}STAMP"] = _new_stamp()

    for key, value in row_data.items():
        if key.upper() in cols:
            payload[key] = value

    if key_column.upper() not in {k.upper() for k in payload.keys()}:
        return

    columns_sql = ", ".join(payload.keys())
    values_sql = ", ".join(f":{key}" for key in payload.keys())
    db.session.execute(
        text(
            f"""
            IF NOT EXISTS (SELECT 1 FROM dbo.{table_name} WHERE TRY_CONVERT(INT, {key_column}) = :_check_codigo)
            BEGIN
                INSERT INTO dbo.{table_name} ({columns_sql})
                VALUES ({values_sql})
            END
            """
        ),
        {"_check_codigo": row_data.get(key_column), **payload},
    )


def _require_tables(*table_names: str):
    missing = [name for name in table_names if not _table_exists(name)]
    if missing:
        raise ProjectServiceError(
            "Estrutura do modulo de projetos indisponivel. Tabelas em falta: " + ", ".join(missing)
        )


def _require_task_columns():
    cols = _table_columns("TAREFAS")
    required = {
        "TAREFASSTAMP",
        "ORIGEM",
        "ORISTAMP",
        "UTILIZADOR",
        "DATA",
        "HORA",
        "DURACAO",
        "TAREFA",
        "TRATADO",
        "DTTRATADO",
        "NMTRATADO",
        "ESTADO",
        "PRIORIDADE",
        "DESCRICAO",
        "DTCONCLUIDA",
        "DTCRIACAO",
        "DTALTERACAO",
        "USERCRIACAO",
        "USERALTERACAO",
    }
    missing = sorted(required - cols)
    if missing:
        raise ProjectServiceError(
            "Campos em falta na TAREFAS para o modulo PROJ: " + ", ".join(missing)
        )


def _text(value, max_len: int | None = None) -> str:
    raw = "" if value is None else str(value).strip()
    if max_len is not None:
        raw = raw[:max_len]
    return raw


def _nullable_text(value, max_len: int | None = None):
    raw = _text(value, max_len=max_len)
    return raw or None


def _int(value, default=0, minimum=None, maximum=None) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    if minimum is not None and number < minimum:
        number = minimum
    if maximum is not None and number > maximum:
        number = maximum
    return number


def _parse_date(value, field_name: str, allow_empty=True):
    raw = _text(value, 20)
    if not raw:
        if allow_empty:
            return None
        raise ProjectValidationError(f"{field_name} obrigatoria.")
    try:
        return date.fromisoformat(raw[:10])
    except Exception as exc:
        raise ProjectValidationError(f"{field_name} invalida.") from exc


def _parse_hour(value):
    raw = _text(value, 5)
    if not raw:
        return ""
    parts = raw.split(":")
    if len(parts) != 2:
        raise ProjectValidationError("Hora invalida.")
    hh = _int(parts[0], default=-1)
    mm = _int(parts[1], default=-1)
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        raise ProjectValidationError("Hora invalida.")
    return f"{hh:02d}:{mm:02d}"


def _dt_iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _date_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _priority_meta(code):
    code_int = _int(code, default=2, minimum=1, maximum=4)
    for item in DEFAULT_PRIORITIES:
        if item["CODIGO"] == code_int:
            return item
    return DEFAULT_PRIORITIES[1]


def _state_rows(table_name: str, defaults: list[dict]) -> list[dict]:
    if _table_exists(table_name):
        rows = db.session.execute(
            text(
                f"""
                SELECT
                    TRY_CONVERT(INT, CODIGO) AS CODIGO,
                    ISNULL(NOME, '') AS NOME,
                    ISNULL(ORDEM, 0) AS ORDEM,
                    ISNULL(COR, 'secondary') AS COR,
                    ISNULL(FINAL, 0) AS FINAL,
                    ISNULL(ATIVO, 1) AS ATIVO
                FROM dbo.{table_name}
                WHERE ISNULL(ATIVO, 1) = 1
                ORDER BY ISNULL(ORDEM, 0), TRY_CONVERT(INT, CODIGO)
                """
            )
        ).mappings().all()
        if rows:
            return [dict(r) for r in rows]
    return [dict(item) for item in defaults]


def _ensure_default_states():
    if _table_exists("PROJEST"):
        for item in DEFAULT_PROJECT_STATES:
            _insert_if_missing("PROJEST", "CODIGO", item)
    if _table_exists("TAREFAEST"):
        for item in DEFAULT_TASK_STATES:
            _insert_if_missing("TAREFAEST", "CODIGO", item)
    db.session.commit()


def _users():
    _require_tables("US")
    rows = db.session.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
            FROM dbo.US
            WHERE LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
            ORDER BY LTRIM(RTRIM(ISNULL(NOME, ''))), LTRIM(RTRIM(ISNULL(LOGIN, '')))
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def get_project_meta():
    _require_tables("PROJ", "PROJEST", "TAREFAS", "TAREFAEST", "US")
    _require_task_columns()
    _ensure_default_states()
    return {
        "users": _users(),
        "project_states": _state_rows("PROJEST", DEFAULT_PROJECT_STATES),
        "task_states": _state_rows("TAREFAEST", DEFAULT_TASK_STATES),
        "priorities": DEFAULT_PRIORITIES,
    }


def _project_auto_code():
    today = datetime.now().strftime("%Y%m%d")
    return f"PRJ-{today}-{uuid.uuid4().hex[:4].upper()}"


def list_projects(args):
    _require_tables("PROJ", "PROJEST", "TAREFAS")
    _require_task_columns()
    _ensure_default_states()

    q = _text(args.get("q"), 120)
    estado = _text(args.get("estado"), 10)
    responsavel = _text(args.get("responsavel"), 60)
    mine = _text(args.get("mine"), 5).lower() in {"1", "true", "on", "yes"}
    current_user_login = _text(args.get("current_user"), 60)

    sql = text(
        """
        WITH TASK_STATS AS (
            SELECT
                LTRIM(RTRIM(ISNULL(T.ORISTAMP, ''))) AS PROJSTAMP,
                COUNT(*) AS TOTAL_TAREFAS,
                SUM(
                    CASE
                        WHEN TRY_CONVERT(INT, ISNULL(T.ESTADO, 0)) = 4 OR ISNULL(T.TRATADO, 0) = 1 THEN 1
                        ELSE 0
                    END
                ) AS TAREFAS_CONCLUIDAS
            FROM dbo.TAREFAS AS T
            WHERE UPPER(LTRIM(RTRIM(ISNULL(T.ORIGEM, '')))) = 'PROJ'
            GROUP BY LTRIM(RTRIM(ISNULL(T.ORISTAMP, '')))
        )
        SELECT
            P.PROJSTAMP,
            ISNULL(P.CODIGO, '') AS CODIGO,
            ISNULL(P.NOME, '') AS NOME,
            ISNULL(P.DESCRICAO, '') AS DESCRICAO,
            ISNULL(P.RESPONSAVEL, '') AS RESPONSAVEL,
            ISNULL(U.NOME, '') AS RESPONSAVEL_NOME,
            TRY_CONVERT(INT, ISNULL(P.ESTADO, 0)) AS ESTADO,
            ISNULL(PE.NOME, '') AS ESTADO_NOME,
            ISNULL(PE.COR, 'secondary') AS ESTADO_COR,
            ISNULL(PE.FINAL, 0) AS ESTADO_FINAL,
            TRY_CONVERT(INT, ISNULL(P.PRIORIDADE, 2)) AS PRIORIDADE,
            P.DATAINICIO,
            P.DATAPREVISTA,
            P.DATAFIM,
            P.CRIADOEM,
            P.CRIADOPOR,
            P.ALTERADOEM,
            P.ALTERADOPOR,
            ISNULL(S.TOTAL_TAREFAS, 0) AS TOTAL_TAREFAS,
            ISNULL(S.TAREFAS_CONCLUIDAS, 0) AS TAREFAS_CONCLUIDAS
        FROM dbo.PROJ AS P
        LEFT JOIN dbo.US AS U
          ON LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) = LTRIM(RTRIM(ISNULL(P.RESPONSAVEL, '')))
        LEFT JOIN dbo.PROJEST AS PE
          ON TRY_CONVERT(INT, PE.CODIGO) = TRY_CONVERT(INT, P.ESTADO)
        LEFT JOIN TASK_STATS AS S
          ON S.PROJSTAMP = LTRIM(RTRIM(ISNULL(P.PROJSTAMP, '')))
        WHERE
            (:q = '' OR
             UPPER(ISNULL(P.CODIGO, '')) LIKE :q_like OR
             UPPER(ISNULL(P.NOME, '')) LIKE :q_like OR
             UPPER(ISNULL(P.DESCRICAO, '')) LIKE :q_like OR
             UPPER(ISNULL(P.RESPONSAVEL, '')) LIKE :q_like OR
             UPPER(ISNULL(U.NOME, '')) LIKE :q_like)
            AND (:estado = '' OR CONVERT(VARCHAR(10), TRY_CONVERT(INT, ISNULL(P.ESTADO, 0))) = :estado)
            AND (:responsavel = '' OR LTRIM(RTRIM(ISNULL(P.RESPONSAVEL, ''))) = :responsavel)
            AND (:mine = 0 OR LTRIM(RTRIM(ISNULL(P.RESPONSAVEL, ''))) = :current_user)
        ORDER BY
            CASE WHEN P.DATAFIM IS NULL THEN 0 ELSE 1 END,
            CASE WHEN P.DATAPREVISTA IS NULL THEN 1 ELSE 0 END,
            P.DATAPREVISTA,
            ISNULL(P.ALTERADOEM, P.CRIADOEM) DESC,
            ISNULL(P.NOME, '')
        """
    )
    rows = db.session.execute(
        sql,
        {
            "q": q,
            "q_like": f"%{q.upper()}%" if q else "",
            "estado": estado,
            "responsavel": responsavel,
            "mine": 1 if mine and current_user_login else 0,
            "current_user": current_user_login,
        },
    ).mappings().all()

    items = []
    for row in rows:
        total = _int(row.get("TOTAL_TAREFAS"), default=0, minimum=0)
        done = _int(row.get("TAREFAS_CONCLUIDAS"), default=0, minimum=0)
        progress = 0 if total <= 0 else round((done / total) * 100)
        priority = _priority_meta(row.get("PRIORIDADE"))
        items.append(
            {
                "PROJSTAMP": _text(row.get("PROJSTAMP"), 25),
                "CODIGO": _text(row.get("CODIGO"), 30),
                "NOME": _text(row.get("NOME"), 120),
                "DESCRICAO": _text(row.get("DESCRICAO")),
                "RESPONSAVEL": _text(row.get("RESPONSAVEL"), 60),
                "RESPONSAVEL_NOME": _text(row.get("RESPONSAVEL_NOME"), 120),
                "ESTADO": _int(row.get("ESTADO"), default=1),
                "ESTADO_NOME": _text(row.get("ESTADO_NOME"), 40) or "Sem estado",
                "ESTADO_COR": _text(row.get("ESTADO_COR"), 20) or "secondary",
                "ESTADO_FINAL": bool(row.get("ESTADO_FINAL") or 0),
                "PRIORIDADE": priority["CODIGO"],
                "PRIORIDADE_NOME": priority["NOME"],
                "PRIORIDADE_COR": priority["COR"],
                "DATAINICIO": _date_iso(row.get("DATAINICIO")),
                "DATAPREVISTA": _date_iso(row.get("DATAPREVISTA")),
                "DATAFIM": _date_iso(row.get("DATAFIM")),
                "CRIADOEM": _dt_iso(row.get("CRIADOEM")),
                "CRIADOPOR": _text(row.get("CRIADOPOR"), 60),
                "ALTERADOEM": _dt_iso(row.get("ALTERADOEM")),
                "ALTERADOPOR": _text(row.get("ALTERADOPOR"), 60),
                "TOTAL_TAREFAS": total,
                "TAREFAS_CONCLUIDAS": done,
                "TAREFAS_ABERTAS": max(total - done, 0),
                "PROGRESSO": progress,
            }
        )

    metrics = {
        "total_projects": len(items),
        "active_projects": sum(1 for item in items if not item["ESTADO_FINAL"]),
        "completed_projects": sum(1 for item in items if item["ESTADO"] == 4),
        "my_projects": sum(1 for item in items if current_user_login and item["RESPONSAVEL"] == current_user_login),
        "overdue_projects": sum(
            1
            for item in items
            if item["DATAPREVISTA"]
            and not item["DATAFIM"]
            and item["PROGRESSO"] < 100
            and date.fromisoformat(item["DATAPREVISTA"]) < date.today()
        ),
    }
    return {"items": items, "metrics": metrics}


def _get_project_row(projstamp: str):
    _require_tables("PROJ", "PROJEST")
    _ensure_default_states()
    row = db.session.execute(
        text(
            """
            SELECT
                P.PROJSTAMP,
                ISNULL(P.CODIGO, '') AS CODIGO,
                ISNULL(P.NOME, '') AS NOME,
                ISNULL(P.DESCRICAO, '') AS DESCRICAO,
                ISNULL(P.RESPONSAVEL, '') AS RESPONSAVEL,
                ISNULL(U.NOME, '') AS RESPONSAVEL_NOME,
                TRY_CONVERT(INT, ISNULL(P.ESTADO, 0)) AS ESTADO,
                ISNULL(PE.NOME, '') AS ESTADO_NOME,
                ISNULL(PE.COR, 'secondary') AS ESTADO_COR,
                ISNULL(PE.FINAL, 0) AS ESTADO_FINAL,
                TRY_CONVERT(INT, ISNULL(P.PRIORIDADE, 2)) AS PRIORIDADE,
                P.DATAINICIO,
                P.DATAPREVISTA,
                P.DATAFIM,
                P.CRIADOEM,
                P.CRIADOPOR,
                P.ALTERADOEM,
                P.ALTERADOPOR
            FROM dbo.PROJ AS P
            LEFT JOIN dbo.US AS U
              ON LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) = LTRIM(RTRIM(ISNULL(P.RESPONSAVEL, '')))
            LEFT JOIN dbo.PROJEST AS PE
              ON TRY_CONVERT(INT, PE.CODIGO) = TRY_CONVERT(INT, P.ESTADO)
            WHERE LTRIM(RTRIM(ISNULL(P.PROJSTAMP, ''))) = :projstamp
            """
        ),
        {"projstamp": _text(projstamp, 25)},
    ).mappings().first()
    if not row:
        raise ProjectNotFoundError("Projeto nao encontrado.")
    row = dict(row)
    priority = _priority_meta(row.get("PRIORIDADE"))
    row["PRIORIDADE"] = priority["CODIGO"]
    row["PRIORIDADE_NOME"] = priority["NOME"]
    row["PRIORIDADE_COR"] = priority["COR"]
    row["DATAINICIO"] = _date_iso(row.get("DATAINICIO"))
    row["DATAPREVISTA"] = _date_iso(row.get("DATAPREVISTA"))
    row["DATAFIM"] = _date_iso(row.get("DATAFIM"))
    row["CRIADOEM"] = _dt_iso(row.get("CRIADOEM"))
    row["ALTERADOEM"] = _dt_iso(row.get("ALTERADOEM"))
    row["ESTADO"] = _int(row.get("ESTADO"), default=1)
    return row


def _get_project_tasks(projstamp: str):
    _require_tables("TAREFAS", "TAREFAEST")
    _require_task_columns()
    _ensure_default_states()
    rows = db.session.execute(
        text(
            """
            SELECT
                T.TAREFASSTAMP,
                ISNULL(T.TAREFA, '') AS TAREFA,
                ISNULL(T.DESCRICAO, '') AS DESCRICAO,
                ISNULL(T.UTILIZADOR, '') AS UTILIZADOR,
                ISNULL(U.NOME, '') AS UTILIZADOR_NOME,
                T.DATA,
                ISNULL(T.HORA, '') AS HORA,
                ISNULL(T.DURACAO, 0) AS DURACAO,
                TRY_CONVERT(INT, ISNULL(T.ESTADO, 1)) AS ESTADO,
                ISNULL(TE.NOME, '') AS ESTADO_NOME,
                ISNULL(TE.COR, 'secondary') AS ESTADO_COR,
                ISNULL(TE.FINAL, 0) AS ESTADO_FINAL,
                TRY_CONVERT(INT, ISNULL(T.PRIORIDADE, 2)) AS PRIORIDADE,
                ISNULL(T.TRATADO, 0) AS TRATADO,
                T.DTCONCLUIDA,
                T.DTCriacao,
                T.DTAlteracao,
                ISNULL(T.USERCRIACAO, '') AS USERCRIACAO,
                ISNULL(T.USERALTERACAO, '') AS USERALTERACAO
            FROM dbo.TAREFAS AS T
            LEFT JOIN dbo.US AS U
              ON LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) = LTRIM(RTRIM(ISNULL(T.UTILIZADOR, '')))
            LEFT JOIN dbo.TAREFAEST AS TE
              ON TRY_CONVERT(INT, TE.CODIGO) = TRY_CONVERT(INT, T.ESTADO)
            WHERE UPPER(LTRIM(RTRIM(ISNULL(T.ORIGEM, '')))) = 'PROJ'
              AND LTRIM(RTRIM(ISNULL(T.ORISTAMP, ''))) = :projstamp
            ORDER BY
              ISNULL(TE.ORDEM, TRY_CONVERT(INT, ISNULL(T.ESTADO, 0))),
              CASE WHEN T.DATA IS NULL THEN 1 ELSE 0 END,
              T.DATA,
              ISNULL(T.HORA, ''),
              T.TAREFASSTAMP
            """
        ),
        {"projstamp": _text(projstamp, 25)},
    ).mappings().all()

    items = []
    for row in rows:
        priority = _priority_meta(row.get("PRIORIDADE"))
        done = _int(row.get("ESTADO"), default=1) == 4 or bool(row.get("TRATADO") or 0)
        items.append(
            {
                "TAREFASSTAMP": _text(row.get("TAREFASSTAMP"), 25),
                "TAREFA": _text(row.get("TAREFA"), 200),
                "DESCRICAO": _text(row.get("DESCRICAO")),
                "UTILIZADOR": _text(row.get("UTILIZADOR"), 60),
                "UTILIZADOR_NOME": _text(row.get("UTILIZADOR_NOME"), 120),
                "DATA": _date_iso(row.get("DATA")),
                "HORA": _text(row.get("HORA"), 5),
                "DURACAO": _int(row.get("DURACAO"), default=0, minimum=0),
                "ESTADO": _int(row.get("ESTADO"), default=1),
                "ESTADO_NOME": _text(row.get("ESTADO_NOME"), 40) or "Sem estado",
                "ESTADO_COR": _text(row.get("ESTADO_COR"), 20) or "secondary",
                "ESTADO_FINAL": bool(row.get("ESTADO_FINAL") or 0),
                "PRIORIDADE": priority["CODIGO"],
                "PRIORIDADE_NOME": priority["NOME"],
                "PRIORIDADE_COR": priority["COR"],
                "TRATADO": 1 if done else 0,
                "DTCONCLUIDA": _dt_iso(row.get("DTCONCLUIDA")),
                "DTCriacao": _dt_iso(row.get("DTCriacao")),
                "DTAlteracao": _dt_iso(row.get("DTAlteracao")),
                "USERCRIACAO": _text(row.get("USERCRIACAO"), 60),
                "USERALTERACAO": _text(row.get("USERALTERACAO"), 60),
            }
        )
    return items


def _project_summary(tasks):
    total = len(tasks)
    done = sum(1 for task in tasks if task["TRATADO"] == 1)
    progress = 0 if total <= 0 else round((done / total) * 100)
    return {
        "total_tasks": total,
        "done_tasks": done,
        "open_tasks": max(total - done, 0),
        "progress": progress,
    }


def get_project_detail(projstamp: str):
    project = _get_project_row(projstamp)
    tasks = _get_project_tasks(projstamp)
    summary = _project_summary(tasks)
    project["TOTAL_TAREFAS"] = summary["total_tasks"]
    project["TAREFAS_CONCLUIDAS"] = summary["done_tasks"]
    project["PROGRESSO"] = summary["progress"]
    return {"project": project, "tasks": tasks, "summary": summary}


def save_project(payload, user_login: str, projstamp: str | None = None):
    _require_tables("PROJ")
    _ensure_default_states()
    nome = _text(payload.get("NOME"), 120)
    responsavel = _text(payload.get("RESPONSAVEL"), 60)
    codigo = _text(payload.get("CODIGO"), 30) or _project_auto_code()
    estado = _int(payload.get("ESTADO"), default=1, minimum=1, maximum=5)
    prioridade = _int(payload.get("PRIORIDADE"), default=2, minimum=1, maximum=4)
    descricao = _nullable_text(payload.get("DESCRICAO"))
    data_inicio = _parse_date(payload.get("DATAINICIO"), "Data inicio")
    data_prevista = _parse_date(payload.get("DATAPREVISTA"), "Data prevista")
    data_fim = _parse_date(payload.get("DATAFIM"), "Data fim")

    if not nome:
        raise ProjectValidationError("Nome obrigatorio.")
    if not responsavel:
        raise ProjectValidationError("Responsavel obrigatorio.")
    if not estado:
        raise ProjectValidationError("Estado obrigatorio.")
    if data_inicio and data_fim and data_fim < data_inicio:
        raise ProjectValidationError("Data fim nao pode ser inferior a data inicio.")
    if data_inicio and data_prevista and data_prevista < data_inicio:
        raise ProjectValidationError("Data prevista nao pode ser inferior a data inicio.")

    conflict = db.session.execute(
        text(
            """
            SELECT TOP 1 PROJSTAMP
            FROM dbo.PROJ
            WHERE UPPER(LTRIM(RTRIM(ISNULL(CODIGO, '')))) = UPPER(LTRIM(RTRIM(:codigo)))
              AND (:projstamp = '' OR LTRIM(RTRIM(ISNULL(PROJSTAMP, ''))) <> :projstamp)
            """
        ),
        {"codigo": codigo, "projstamp": _text(projstamp, 25)},
    ).scalar()
    if conflict:
        raise ProjectValidationError("Ja existe um projeto com esse codigo.")

    params = {
        "codigo": codigo,
        "nome": nome,
        "descricao": descricao,
        "responsavel": responsavel,
        "estado": estado,
        "prioridade": prioridade,
        "data_inicio": data_inicio,
        "data_prevista": data_prevista,
        "data_fim": data_fim,
        "user": _text(user_login, 60),
    }

    try:
        if projstamp:
            if not db.session.execute(
                text("SELECT COUNT(*) FROM dbo.PROJ WHERE PROJSTAMP = :projstamp"),
                {"projstamp": _text(projstamp, 25)},
            ).scalar():
                raise ProjectNotFoundError("Projeto nao encontrado.")
            db.session.execute(
                text(
                    """
                    UPDATE dbo.PROJ
                    SET
                        CODIGO = :codigo,
                        NOME = :nome,
                        DESCRICAO = :descricao,
                        RESPONSAVEL = :responsavel,
                        ESTADO = :estado,
                        PRIORIDADE = :prioridade,
                        DATAINICIO = :data_inicio,
                        DATAPREVISTA = :data_prevista,
                        DATAFIM = :data_fim,
                        ALTERADOEM = SYSDATETIME(),
                        ALTERADOPOR = :user
                    WHERE PROJSTAMP = :projstamp
                    """
                ),
                {**params, "projstamp": _text(projstamp, 25)},
            )
        else:
            projstamp = _new_stamp()
            db.session.execute(
                text(
                    """
                    INSERT INTO dbo.PROJ (
                        PROJSTAMP, CODIGO, NOME, DESCRICAO, RESPONSAVEL, ESTADO, PRIORIDADE,
                        DATAINICIO, DATAPREVISTA, DATAFIM,
                        CRIADOEM, CRIADOPOR, ALTERADOEM, ALTERADOPOR
                    ) VALUES (
                        :projstamp, :codigo, :nome, :descricao, :responsavel, :estado, :prioridade,
                        :data_inicio, :data_prevista, :data_fim,
                        SYSDATETIME(), :user, SYSDATETIME(), :user
                    )
                    """
                ),
                {**params, "projstamp": projstamp},
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return get_project_detail(projstamp)


def _task_done_fields(estado: int):
    if estado == 4:
        return {
            "tratado": 1,
            "dtconcluida": datetime.now(),
            "dttratado": date.today(),
        }
    return {
        "tratado": 0,
        "dtconcluida": None,
        "dttratado": date(1900, 1, 1),
    }


def save_project_task(projstamp: str, payload, user_login: str, tarefastamp: str | None = None):
    _require_tables("PROJ", "TAREFAS", "TAREFAEST")
    _require_task_columns()
    _ensure_default_states()
    _get_project_row(projstamp)

    tarefa = _text(payload.get("TAREFA"), 200)
    descricao = _nullable_text(payload.get("DESCRICAO"))
    utilizador = _text(payload.get("UTILIZADOR"), 60)
    data_value = _parse_date(payload.get("DATA"), "Data")
    hora_value = _parse_hour(payload.get("HORA"))
    duracao = _int(payload.get("DURACAO"), default=60, minimum=0, maximum=24 * 60)
    estado = _int(payload.get("ESTADO"), default=1, minimum=1, maximum=5)
    prioridade = _int(payload.get("PRIORIDADE"), default=2, minimum=1, maximum=4)

    if not tarefa:
        raise ProjectValidationError("Titulo da tarefa obrigatorio.")
    if not utilizador:
        raise ProjectValidationError("Responsavel da tarefa obrigatorio.")

    done_fields = _task_done_fields(estado)
    params = {
        "projstamp": _text(projstamp, 25),
        "tarefa": tarefa,
        "descricao": descricao,
        "utilizador": utilizador,
        "data": data_value,
        "hora": hora_value,
        "duracao": duracao,
        "estado": estado,
        "prioridade": prioridade,
        "tratado": done_fields["tratado"],
        "dtconcluida": done_fields["dtconcluida"],
        "dttratado": done_fields["dttratado"],
        "nmtratado": _text(user_login, 60) if done_fields["tratado"] else "",
        "user": _text(user_login, 60),
    }

    try:
        if tarefastamp:
            exists = db.session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM dbo.TAREFAS
                    WHERE TAREFASSTAMP = :tarefastamp
                      AND UPPER(LTRIM(RTRIM(ISNULL(ORIGEM, '')))) = 'PROJ'
                      AND LTRIM(RTRIM(ISNULL(ORISTAMP, ''))) = :projstamp
                    """
                ),
                {"tarefastamp": _text(tarefastamp, 25), "projstamp": _text(projstamp, 25)},
            ).scalar()
            if not exists:
                raise ProjectNotFoundError("Tarefa do projeto nao encontrada.")
            db.session.execute(
                text(
                    """
                    UPDATE dbo.TAREFAS
                    SET
                        TAREFA = :tarefa,
                        DESCRICAO = :descricao,
                        UTILIZADOR = :utilizador,
                        DATA = :data,
                        HORA = :hora,
                        DURACAO = :duracao,
                        ESTADO = :estado,
                        PRIORIDADE = :prioridade,
                        TRATADO = :tratado,
                        DTCONCLUIDA = :dtconcluida,
                        DTTRATADO = :dttratado,
                        NMTRATADO = :nmtratado,
                        DTAlteracao = SYSDATETIME(),
                        USERALTERACAO = :user
                    WHERE TAREFASSTAMP = :tarefastamp
                    """
                ),
                {**params, "tarefastamp": _text(tarefastamp, 25)},
            )
        else:
            tarefastamp = _new_stamp()
            db.session.execute(
                text(
                    """
                    INSERT INTO dbo.TAREFAS (
                        TAREFASSTAMP, ORIGEM, ORISTAMP,
                        UTILIZADOR, DATA, HORA, DURACAO,
                        TAREFA, ALOJAMENTO, TRATADO, DTTRATADO, NMTRATADO,
                        ESTADO, PRIORIDADE, DESCRICAO, DTCONCLUIDA,
                        DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO
                    ) VALUES (
                        :tarefastamp, 'PROJ', :projstamp,
                        :utilizador, :data, :hora, :duracao,
                        :tarefa, '', :tratado, :dttratado, :nmtratado,
                        :estado, :prioridade, :descricao, :dtconcluida,
                        SYSDATETIME(), SYSDATETIME(), :user, :user
                    )
                    """
                ),
                {**params, "tarefastamp": tarefastamp},
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return get_project_detail(projstamp)


def get_project_task(projstamp: str, tarefastamp: str):
    detail = get_project_detail(projstamp)
    for task in detail["tasks"]:
        if task["TAREFASSTAMP"] == _text(tarefastamp, 25):
            return {"task": task, "project": detail["project"], "summary": detail["summary"]}
    raise ProjectNotFoundError("Tarefa do projeto nao encontrada.")
