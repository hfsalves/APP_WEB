import re
import uuid
from urllib.parse import urlsplit

from markupsafe import escape
from sqlalchemy import text

from models import db


DASHBOARD_LINKS_TABLES = {"DBW", "DBWL", "DBWU"}
_schema_ready = False
_table_exists_cache: dict[str, bool] = {}
_column_exists_cache: dict[tuple[str, str], bool] = {}


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _truthy(value) -> bool:
    try:
        return bool(int(value or 0))
    except Exception:
        return bool(value)


def _clean_css_value(value: str, fallback: str = "") -> str:
    raw = str(value or "").strip()[:30]
    if not raw:
        return fallback
    if re.match(r"^#[0-9A-Fa-f]{3,8}$", raw):
        return raw
    if re.match(r"^[A-Za-z0-9_(),.%\s-]+$", raw):
        return raw
    return fallback


def _safe_link_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "#"
    if raw.startswith("/"):
        return raw
    try:
        parsed = urlsplit(raw)
    except Exception:
        return "#"
    if parsed.scheme.lower() in {"http", "https", "mailto", "tel"}:
        return raw
    return "#"


def _style_attr(values: dict[str, str]) -> str:
    parts = []
    for key, value in values.items():
        clean = _clean_css_value(value)
        if clean:
            parts.append(f"{key}: {clean}")
    return "; ".join(parts)


def _table_exists(table_name: str) -> bool:
    key = str(table_name or "").strip().upper()
    if key in _table_exists_cache:
        return _table_exists_cache[key]
    row = db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
    """), {"table_name": key}).first()
    exists = bool(row)
    _table_exists_cache[key] = exists
    return exists


def _column_exists(table_name: str, column_name: str) -> bool:
    key = (str(table_name or "").strip().upper(), str(column_name or "").strip().upper())
    if key in _column_exists_cache:
        return _column_exists_cache[key]
    row = db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
    """), {"table_name": key[0], "column_name": key[1]}).first()
    exists = bool(row)
    _column_exists_cache[key] = exists
    return exists


def _ensure_dashboard_links_layout_columns() -> None:
    if not _table_exists("DBWU"):
        return
    db.session.execute(text("""
        IF COL_LENGTH('dbo.DBWU', 'COLUNA') IS NULL
            ALTER TABLE dbo.DBWU ADD COLUNA INT NULL;
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.DBWU', 'ORDEM_COLUNA') IS NULL
            ALTER TABLE dbo.DBWU ADD ORDEM_COLUNA INT NULL;
    """))
    _column_exists_cache.pop(("DBWU", "COLUNA"), None)
    _column_exists_cache.pop(("DBWU", "ORDEM_COLUNA"), None)


def _insert_campo_if_missing(table_name: str, field: dict) -> None:
    table_name = table_name.upper()
    field_name = field["name"].upper()
    exists = db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.CAMPOS
        WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
          AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = :field_name
    """), {"table_name": table_name, "field_name": field_name}).first()

    defaults = {
        "CAMPOSSTAMP": _new_stamp(),
        "ORDEM": int(field.get("ordem", 0)),
        "NMCAMPO": field_name,
        "DESCRICAO": field.get("label", field_name),
        "TIPO": field.get("tipo", "TEXT"),
        "TABELA": table_name,
        "LISTA": 1 if field.get("lista") else 0,
        "FILTRO": 1 if field.get("filtro") else 0,
        "ADMIN": 0,
        "VISIVEL": 1 if field.get("visivel", True) else 0,
        "RONLY": 1 if field.get("readonly") else 0,
        "COMBO": field.get("combo", ""),
        "VIRTUAL": "",
        "TAM": int(field.get("tam", 4)),
        "ORDEM_MOBILE": int(field.get("ordem_mobile", field.get("ordem", 0))),
        "TAM_MOBILE": int(field.get("tam_mobile", 12)),
        "CONDICAO_VISIVEL": "",
        "OBRIGATORIO": 1 if field.get("obrigatorio") else 0,
        "ORDEM_LISTA": int(field.get("ordem_lista", field.get("ordem", 0))),
        "TAM_LISTA": int(field.get("tam_lista", field.get("tam", 4))),
        "ORDEM_LISTA_MOBILE": int(field.get("ordem_lista_mobile", field.get("ordem_mobile", field.get("ordem", 0)))),
        "TAM_LISTA_MOBILE": int(field.get("tam_lista_mobile", field.get("tam_mobile", 12))),
        "LISTA_MOBILE_BOLD": 1 if field.get("mobile_bold") else 0,
        "LISTA_MOBILE_ITALIC": 0,
        "LISTA_MOBILE_SHOW_LABEL": 1,
        "LISTA_MOBILE_LABEL": field.get("label", field_name),
        "PROPRIEDADES": field.get("propriedades", "{}"),
    }
    if exists:
        update_values = {
            name: defaults[name]
            for name in (
                "ORDEM", "DESCRICAO", "TIPO", "LISTA", "FILTRO", "RONLY",
                "VISIVEL", "COMBO", "TAM", "ORDEM_MOBILE", "TAM_MOBILE",
                "OBRIGATORIO", "ORDEM_LISTA", "TAM_LISTA",
                "ORDEM_LISTA_MOBILE", "TAM_LISTA_MOBILE",
                "LISTA_MOBILE_BOLD", "LISTA_MOBILE_SHOW_LABEL",
                "LISTA_MOBILE_LABEL", "PROPRIEDADES"
            )
            if _column_exists("CAMPOS", name)
        }
        if update_values:
            assignments = ", ".join(f"{name} = :{name}" for name in update_values)
            params = {**update_values, "table_name": table_name, "field_name": field_name}
            db.session.execute(text(f"""
                UPDATE dbo.CAMPOS
                SET {assignments}
                WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
                  AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = :field_name
            """), params)
        return

    columns = [name for name in defaults if _column_exists("CAMPOS", name)]
    sql = f"""
        INSERT INTO dbo.CAMPOS ({", ".join(columns)})
        VALUES ({", ".join(":" + name for name in columns)})
    """
    db.session.execute(text(sql), {name: defaults[name] for name in columns})


def _ensure_dashboard_links_metadata() -> None:
    menu_cols = {
        "MENUSTAMP": _new_stamp(),
        "ORDEM": 910,
        "NOME": "Configuração de Widgets",
        "TABELA": "DBW",
        "URL": "/generic/view/DBW/",
        "ADMIN": 0,
        "ICONE": "fa-solid fa-link",
        "FORM": "/generic/form/DBW",
        "ORDERBY": "COLUNA, ORDEM_COLUNA",
        "INATIVO": 0,
    }

    menu_exists = db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.MENU
        WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'DBW'
    """)).first()
    if not menu_exists:
        columns = [name for name in menu_cols if _column_exists("MENU", name)]
        sql = f"""
            INSERT INTO dbo.MENU ({", ".join(columns)})
            VALUES ({", ".join(":" + name for name in columns)})
        """
        db.session.execute(text(sql), {name: menu_cols[name] for name in columns})

    dbw_fields = [
        {"name": "DBWSTAMP", "label": "ID", "tipo": "TEXT", "ordem": 0, "tam": 3, "readonly": True, "visivel": False},
        {"name": "NOME", "label": "Nome", "tipo": "TEXT", "ordem": 0, "tam": 4, "visivel": False},
        {"name": "TITULO", "label": "Título", "tipo": "TEXT", "ordem": 10, "tam": 6, "lista": True, "filtro": True, "obrigatorio": True, "mobile_bold": True},
        {"name": "COLUNA", "label": "Coluna", "tipo": "COMBO", "ordem": 20, "tam": 3, "lista": True, "combo": "SELECT 1 AS value, 'Esquerda' AS text UNION ALL SELECT 2, 'Centro' UNION ALL SELECT 3, 'Direita'"},
        {"name": "ORDEM_COLUNA", "label": "Ordem", "tipo": "INT", "ordem": 30, "tam": 3, "lista": True},
        {"name": "ATIVO", "label": "Ativo", "tipo": "BIT", "ordem": 0, "tam": 2, "visivel": False},
        {"name": "BACKGROUND", "label": "Background", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "TEXT_COLOR", "label": "Cor texto", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "BORDER_COLOR", "label": "Cor border", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "LARGURA", "label": "Largura", "tipo": "INT", "ordem": 0, "tam": 2, "visivel": False},
        {"name": "ALTURA", "label": "Altura", "tipo": "INT", "ordem": 0, "tam": 2, "visivel": False},
    ]
    dbwl_fields = [
        {"name": "DBWLSTAMP", "label": "ID", "tipo": "TEXT", "ordem": 0, "tam": 3, "readonly": True, "visivel": False},
        {"name": "DBWSTAMP", "label": "Widget", "tipo": "TEXT", "ordem": 0, "tam": 3, "readonly": True, "visivel": False},
        {"name": "ORDEM", "label": "Ordem", "tipo": "INT", "ordem": 10, "tam": 2, "lista": True},
        {"name": "TEXTO", "label": "Texto", "tipo": "TEXT", "ordem": 20, "tam": 4, "lista": True, "obrigatorio": True, "mobile_bold": True},
        {"name": "URL", "label": "URL", "tipo": "TEXT", "ordem": 30, "tam": 6, "lista": True, "obrigatorio": True},
        {"name": "ABRIR_NOVA_TAB", "label": "Abrir nova tab", "tipo": "BIT", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "ATIVO", "label": "Ativo", "tipo": "BIT", "ordem": 0, "tam": 2, "visivel": False},
        {"name": "COR_BACKGROUND", "label": "Background", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "COR_BORDER", "label": "Cor border", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
        {"name": "COR_TEXTO", "label": "Cor texto", "tipo": "COLOR", "ordem": 0, "tam": 3, "visivel": False},
    ]
    for field in dbw_fields:
        _insert_campo_if_missing("DBW", field)
    for field in dbwl_fields:
        _insert_campo_if_missing("DBWL", field)

    linhas_exists = db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.LINHAS
        WHERE UPPER(LTRIM(RTRIM(ISNULL(MAE, '')))) = 'DBW'
          AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'DBWL'
    """)).first()
    if not linhas_exists:
        db.session.execute(text("""
            INSERT INTO dbo.LINHAS
                (LINHASSTAMP, MAE, TABELA, LIGACAO, LIGACAOMAE, CAMPOSCAB, CAMPOSLIN)
            VALUES
                (:stamp, 'DBW', 'DBWL', 'DBWSTAMP', 'DBWSTAMP', 'DBW.DBWSTAMP', 'DBWL.DBWSTAMP')
        """), {"stamp": _new_stamp()})

    if _table_exists("ACESSOS") and _table_exists("US"):
        access_defaults = {
            "ACESSOSSTAMP": _new_stamp(),
            "UTILIZADOR": "",
            "TABELA": "DBW",
            "CONSULTAR": 1,
            "INSERIR": 1,
            "EDITAR": 1,
            "ELIMINAR": 1,
            "USSTAMP": "",
        }
        access_columns = [name for name in access_defaults if _column_exists("ACESSOS", name)]
        users = db.session.execute(text("""
            SELECT
                LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
                LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS USSTAMP
            FROM dbo.US
            WHERE ISNULL(ADMIN, 0) = 1 OR ISNULL(DEV, 0) = 1
        """)).mappings().all()
        for table_name in DASHBOARD_LINKS_TABLES:
            for user in users:
                login = str(user.get("LOGIN") or "").strip()
                if not login:
                    continue
                exists = db.session.execute(text("""
                    SELECT TOP 1 1
                    FROM dbo.ACESSOS
                    WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
                      AND LTRIM(RTRIM(ISNULL(UTILIZADOR, ''))) = :login
                """), {"table_name": table_name, "login": login}).first()
                if exists:
                    continue
                values = {
                    "ACESSOSSTAMP": _new_stamp(),
                    "UTILIZADOR": login,
                    "TABELA": table_name,
                    "CONSULTAR": 1,
                    "INSERIR": 1,
                    "EDITAR": 1,
                    "ELIMINAR": 1,
                    "USSTAMP": str(user.get("USSTAMP") or "").strip(),
                }
                db.session.execute(text(f"""
                    INSERT INTO dbo.ACESSOS ({", ".join(access_columns)})
                    VALUES ({", ".join(":" + name for name in access_columns)})
                """), {name: values[name] for name in access_columns})


def ensure_dashboard_links_schema() -> None:
    global _schema_ready
    if _schema_ready:
        _ensure_dashboard_links_layout_columns()
        db.session.commit()
        return
    db.session.execute(text("""
        IF OBJECT_ID('dbo.DBW', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.DBW (
                DBWSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBW_STAMP DEFAULT (LEFT(REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''), 25)),
                NOME VARCHAR(100) NOT NULL CONSTRAINT DF_DBW_NOME DEFAULT (''),
                ATIVO BIT NOT NULL CONSTRAINT DF_DBW_ATIVO DEFAULT (1),
                COLUNA INT NOT NULL CONSTRAINT DF_DBW_COLUNA DEFAULT (1),
                ORDEM_COLUNA INT NOT NULL CONSTRAINT DF_DBW_ORDEM_COLUNA DEFAULT (0),
                LARGURA INT NULL,
                ALTURA INT NULL,
                TITULO VARCHAR(100) NOT NULL CONSTRAINT DF_DBW_TITULO DEFAULT (''),
                BACKGROUND VARCHAR(30) NOT NULL CONSTRAINT DF_DBW_BACKGROUND DEFAULT (''),
                BORDER_COLOR VARCHAR(30) NOT NULL CONSTRAINT DF_DBW_BORDER_COLOR DEFAULT (''),
                TEXT_COLOR VARCHAR(30) NOT NULL CONSTRAINT DF_DBW_TEXT_COLOR DEFAULT (''),
                FEID VARCHAR(25) NOT NULL CONSTRAINT DF_DBW_FEID DEFAULT (''),
                OUSRDATA DATETIME NOT NULL CONSTRAINT DF_DBW_OUSRDATA DEFAULT (GETDATE()),
                OUSRHORA VARCHAR(8) NOT NULL CONSTRAINT DF_DBW_OUSRHORA DEFAULT (CONVERT(VARCHAR(8), GETDATE(), 108)),
                USRCRIACAO VARCHAR(25) NOT NULL CONSTRAINT DF_DBW_USRCRIACAO DEFAULT (''),
                CONSTRAINT PK_DBW PRIMARY KEY CLUSTERED (DBWSTAMP)
            );
        END
    """))
    db.session.execute(text("""
        IF OBJECT_ID('dbo.DBWL', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.DBWL (
                DBWLSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBWL_STAMP DEFAULT (LEFT(REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''), 25)),
                DBWSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBWL_DBWSTAMP DEFAULT (''),
                ORDEM INT NOT NULL CONSTRAINT DF_DBWL_ORDEM DEFAULT (0),
                TEXTO VARCHAR(100) NOT NULL CONSTRAINT DF_DBWL_TEXTO DEFAULT (''),
                URL VARCHAR(500) NOT NULL CONSTRAINT DF_DBWL_URL DEFAULT (''),
                ABRIR_NOVA_TAB BIT NOT NULL CONSTRAINT DF_DBWL_ABRIR_NOVA_TAB DEFAULT (1),
                ATIVO BIT NOT NULL CONSTRAINT DF_DBWL_ATIVO DEFAULT (1),
                COR_BACKGROUND VARCHAR(30) NOT NULL CONSTRAINT DF_DBWL_COR_BACKGROUND DEFAULT (''),
                COR_BORDER VARCHAR(30) NOT NULL CONSTRAINT DF_DBWL_COR_BORDER DEFAULT (''),
                COR_TEXTO VARCHAR(30) NOT NULL CONSTRAINT DF_DBWL_COR_TEXTO DEFAULT (''),
                CONSTRAINT PK_DBWL PRIMARY KEY CLUSTERED (DBWLSTAMP)
            );
        END
    """))
    db.session.execute(text("""
        IF OBJECT_ID('dbo.DBWU', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.DBWU (
                DBWUSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBWU_STAMP DEFAULT (LEFT(REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''), 25)),
                DBWSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBWU_DBWSTAMP DEFAULT (''),
                USRSTAMP VARCHAR(25) NOT NULL CONSTRAINT DF_DBWU_USRSTAMP DEFAULT (''),
                CONSTRAINT PK_DBWU PRIMARY KEY CLUSTERED (DBWUSTAMP)
            );
        END
    """))
    db.session.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DBWL_DBWSTAMP_ORDEM' AND object_id = OBJECT_ID('dbo.DBWL'))
            CREATE INDEX IX_DBWL_DBWSTAMP_ORDEM ON dbo.DBWL (DBWSTAMP, ATIVO, ORDEM, TEXTO);
    """))
    db.session.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DBWU_USRSTAMP' AND object_id = OBJECT_ID('dbo.DBWU'))
            CREATE INDEX IX_DBWU_USRSTAMP ON dbo.DBWU (USRSTAMP, DBWSTAMP);
    """))
    db.session.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_DBWU_DBW_USER' AND object_id = OBJECT_ID('dbo.DBWU'))
            CREATE UNIQUE INDEX UX_DBWU_DBW_USER ON dbo.DBWU (DBWSTAMP, USRSTAMP);
    """))
    _ensure_dashboard_links_layout_columns()
    _ensure_dashboard_links_metadata()
    db.session.commit()
    _schema_ready = True


def user_has_dashboard_links(userstamp: str) -> bool:
    if not _table_exists("DBW") or not _table_exists("DBWU"):
        return False
    stamp = str(userstamp or "").strip()
    if not stamp:
        return False
    row = db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.DBWU U
        INNER JOIN dbo.DBW W ON W.DBWSTAMP = U.DBWSTAMP
        WHERE U.USRSTAMP = :userstamp
          AND ISNULL(W.ATIVO, 1) = 1
    """), {"userstamp": stamp}).first()
    return bool(row)


def ensure_dashboard_links_for_user(userstamp: str) -> None:
    stamp = str(userstamp or "").strip()
    if not stamp or not _table_exists("DBW") or not _table_exists("DBWU"):
        return
    db.session.execute(text("""
        INSERT INTO dbo.DBWU (DBWSTAMP, USRSTAMP)
        SELECT W.DBWSTAMP, :userstamp
        FROM dbo.DBW W
        WHERE ISNULL(W.ATIVO, 1) = 1
          AND NOT EXISTS (
              SELECT 1
              FROM dbo.DBWU U
              WHERE U.DBWSTAMP = W.DBWSTAMP
          )
    """), {"userstamp": stamp})
    db.session.commit()


def dashboard_links_widget_items(userstamp: str) -> dict[int, list[dict]]:
    stamp = str(userstamp or "").strip()
    grouped = {1: [], 2: [], 3: []}
    if not stamp or not _table_exists("DBW") or not _table_exists("DBWL") or not _table_exists("DBWU"):
        return grouped
    _ensure_dashboard_links_layout_columns()
    has_user_col = _column_exists("DBWU", "COLUNA")
    has_user_order = _column_exists("DBWU", "ORDEM_COLUNA")
    col_expr = "ISNULL(U.COLUNA, ISNULL(W.COLUNA, 1))" if has_user_col else "ISNULL(W.COLUNA, 1)"
    order_expr = "ISNULL(U.ORDEM_COLUNA, ISNULL(W.ORDEM_COLUNA, 0))" if has_user_order else "ISNULL(W.ORDEM_COLUNA, 0)"

    widgets = db.session.execute(text(f"""
        SELECT
            W.DBWSTAMP,
            ISNULL(W.NOME, '') AS NOME,
            ISNULL(W.TITULO, '') AS TITULO,
            {col_expr} AS COLUNA,
            {order_expr} AS ORDEM_COLUNA,
            ISNULL(W.BACKGROUND, '') AS BACKGROUND,
            ISNULL(W.BORDER_COLOR, '') AS BORDER_COLOR,
            ISNULL(W.TEXT_COLOR, '') AS TEXT_COLOR
        FROM dbo.DBW W
        INNER JOIN dbo.DBWU U ON U.DBWSTAMP = W.DBWSTAMP
        WHERE U.USRSTAMP = :userstamp
          AND ISNULL(W.ATIVO, 1) = 1
        ORDER BY {col_expr}, {order_expr}, ISNULL(W.NOME, '')
    """), {"userstamp": stamp}).mappings().all()

    for widget in widgets:
        try:
            coluna = int(widget.get("COLUNA") or 1)
        except Exception:
            coluna = 1
        if coluna not in grouped:
            coluna = 1

        links = db.session.execute(text("""
            SELECT
                ISNULL(TEXTO, '') AS TEXTO,
                ISNULL(URL, '') AS URL,
                ISNULL(ABRIR_NOVA_TAB, 1) AS ABRIR_NOVA_TAB,
                ISNULL(COR_BACKGROUND, '') AS COR_BACKGROUND,
                ISNULL(COR_BORDER, '') AS COR_BORDER,
                ISNULL(COR_TEXTO, '') AS COR_TEXTO
            FROM dbo.DBWL
            WHERE DBWSTAMP = :dbwstamp
              AND ISNULL(ATIVO, 1) = 1
            ORDER BY ISNULL(ORDEM, 0), ISNULL(TEXTO, '')
        """), {"dbwstamp": widget.get("DBWSTAMP")}).mappings().all()

        widget_style = _style_attr({
            "--dashboard-links-bg": widget.get("BACKGROUND"),
            "--dashboard-links-border": widget.get("BORDER_COLOR"),
            "--dashboard-links-text": widget.get("TEXT_COLOR"),
        })
        title = str(widget.get("TITULO") or widget.get("NOME") or "Links").strip()
        link_html = []
        for link in links:
            url = _safe_link_url(link.get("URL"))
            target = ' target="_blank" rel="noopener noreferrer"' if _truthy(link.get("ABRIR_NOVA_TAB")) else ""
            link_style = _style_attr({
                "--dashboard-link-bg": link.get("COR_BACKGROUND"),
                "--dashboard-link-border": link.get("COR_BORDER"),
                "--dashboard-link-text": link.get("COR_TEXTO"),
            })
            link_style_attr = f' style="{escape(link_style)}"' if link_style else ""
            link_html.append(
                f'<a class="dashboard-link-btn" href="{escape(url)}"{target}{link_style_attr}>'
                f'{escape(str(link.get("TEXTO") or url))}</a>'
            )
        if not link_html:
            continue

        style_attr = f' style="{escape(widget_style)}"' if widget_style else ""
        grouped[coluna].append(
            {
                "kind": "links",
                "id": str(widget.get("DBWSTAMP") or "").strip(),
                "coluna": coluna,
                "ordem": int(widget.get("ORDEM_COLUNA") or 0),
                "html": (
                    f'<div class="dashboard-links-widget"{style_attr}>'
                    f'<div class="widget-title">{escape(title)}</div>'
                    f'<div class="links-grid">{"".join(link_html)}</div>'
                    f'</div>'
                ),
            }
        )

    for col in grouped:
        grouped[col].sort(key=lambda item: (int(item.get("ordem") or 0), str(item.get("id") or "")))
    return grouped


def render_dashboard_links_widgets(userstamp: str) -> dict[int, str]:
    grouped = dashboard_links_widget_items(userstamp)
    return {col: "".join(str(item.get("html") or "") for item in items) for col, items in grouped.items()}
