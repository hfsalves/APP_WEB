"""Idempotent menu registration for the GuestSpaTur transfer dashboard."""

import uuid

from sqlalchemy import text

from models import db


MENU_STAMP = "TRANSFERDASHBOARDMENU0001"
MENU_URL = "/dashboard/transfers"


def ensure_transfer_dashboard_menu() -> None:
    if db.engine.dialect.name != "mssql":
        return
    database_name = str(db.session.execute(text("SELECT DB_NAME()")).scalar() or "").strip().upper()
    if database_name != "GESTAO":
        db.session.rollback()
        return
    existing = db.session.execute(text("""
        SELECT TOP 1 MENUSTAMP
        FROM dbo.MENU WITH (UPDLOCK, HOLDLOCK)
        WHERE MENUSTAMP = :stamp
           OR LTRIM(RTRIM(COALESCE(URL, ''))) = :url
    """), {"stamp": MENU_STAMP, "url": MENU_URL}).scalar()
    if existing:
        db.session.execute(text("""
            UPDATE dbo.MENU
               SET ORDEM = 207,
                   NOME = 'Resumo de Transfers',
                   TABELA = 'TRANSFERS',
                   URL = :url,
                   ADMIN = 0,
                   ICONE = 'fa-solid fa-route',
                   INATIVO = 0
             WHERE MENUSTAMP = :existing
        """), {"url": MENU_URL, "existing": existing})
    else:
        db.session.execute(text("""
            INSERT INTO dbo.MENU
                (MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO)
            VALUES
                (:stamp, 207, 'Resumo de Transfers', 'TRANSFERS', :url, 0,
                 'fa-solid fa-route', '', '', 1, 0)
        """), {"stamp": MENU_STAMP, "url": MENU_URL})

    # Empresas com módulos ativos filtram a barra lateral por MOD_OBJETOS.
    # O resumo pertence ao mesmo módulo PMS das reservas e do calendário.
    if db.session.execute(text("SELECT OBJECT_ID('dbo.MOD_OBJETOS', 'U')")).scalar():
        pms_stamp = db.session.execute(text("""
            SELECT TOP 1 MODSTAMP
            FROM dbo.MODULOS
            WHERE UPPER(LTRIM(RTRIM(COALESCE(CODIGO, '')))) = 'PMS'
              AND COALESCE(ATIVO, 0) = 1
        """)).scalar()
        if pms_stamp:
            object_key = f"MENU:{MENU_STAMP}"
            module_object = db.session.execute(text("""
                SELECT TOP 1 MODOBJSTAMP
                FROM dbo.MOD_OBJETOS WITH (UPDLOCK, HOLDLOCK)
                WHERE MODSTAMP = :modstamp AND OBJKEY = :object_key
            """), {"modstamp": pms_stamp, "object_key": object_key}).scalar()
            if module_object:
                db.session.execute(text("""
                    UPDATE dbo.MOD_OBJETOS
                       SET TIPO = 'MENU', OBJNOME = 'Resumo de Transfers', OBJROTA = :url,
                           MENUSTAMP = :menu_stamp, ORDEM = 207, ATIVO = 1,
                           DTALT = GETDATE(), USERALTERACAO = 'codex'
                     WHERE MODOBJSTAMP = :object_stamp
                """), {"url": MENU_URL, "menu_stamp": MENU_STAMP, "object_stamp": module_object})
            else:
                db.session.execute(text("""
                    INSERT INTO dbo.MOD_OBJETOS
                        (MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA,
                         MENUSTAMP, ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO)
                    VALUES
                        (:object_stamp, :modstamp, 'MENU', :object_key, 'Resumo de Transfers',
                         :url, :menu_stamp, 207, 1, GETDATE(), 'codex', '')
                """), {
                    "object_stamp": uuid.uuid4().hex.upper()[:25],
                    "modstamp": pms_stamp,
                    "object_key": object_key,
                    "url": MENU_URL,
                    "menu_stamp": MENU_STAMP,
                })
    db.session.commit()
