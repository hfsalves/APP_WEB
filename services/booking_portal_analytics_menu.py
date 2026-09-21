"""Idempotent StationZero menu registration for portal analytics."""

import uuid

from sqlalchemy import text

from models import db


GROUP_STAMP = "PBANALYTICSGROUP00000001"
ITEM_STAMP = "PBANALYTICSMENU000000001"
ACCESS_LOGINS = ("admin", "pedro", "dyhia", "susana")


def ensure_booking_portal_analytics_menu() -> None:
    if db.engine.dialect.name != "mssql":
        return

    group_exists = db.session.execute(text("""
        SELECT TOP 1 1 FROM dbo.MENU WITH (UPDLOCK, HOLDLOCK) WHERE MENUSTAMP = :stamp
    """), {"stamp": GROUP_STAMP}).scalar()
    if not group_exists:
        db.session.execute(text("""
            INSERT INTO dbo.MENU (
                MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
            ) VALUES (
                :stamp, 1500, 'PortoBreak', '', '', 0,
                'fa-solid fa-chart-line', '', '', 0, 0
            )
        """), {"stamp": GROUP_STAMP})
    else:
        db.session.execute(text("""
            UPDATE dbo.MENU SET ADMIN = 0 WHERE MENUSTAMP = :stamp
        """), {"stamp": GROUP_STAMP})

    item_exists = db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.MENU WITH (UPDLOCK, HOLDLOCK)
        WHERE MENUSTAMP = :stamp
           OR LTRIM(RTRIM(ISNULL(URL, ''))) = '/analytics/portobreak'
    """), {"stamp": ITEM_STAMP}).scalar()
    if not item_exists:
        db.session.execute(text("""
            INSERT INTO dbo.MENU (
                MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
            ) VALUES (
                :stamp, 1501, 'Analítica do Portal', 'PB_ANALYTICS',
                '/analytics/portobreak', 0, 'fa-solid fa-chart-column', '', '', 0, 0
            )
        """), {"stamp": ITEM_STAMP})
    else:
        db.session.execute(text("""
            UPDATE dbo.MENU
            SET ADMIN = 0
            WHERE MENUSTAMP = :stamp
               OR LTRIM(RTRIM(ISNULL(URL, ''))) = '/analytics/portobreak'
        """), {"stamp": ITEM_STAMP})

    for login in ACCESS_LOGINS:
        user = db.session.execute(text("""
            SELECT TOP 1 LTRIM(RTRIM(USSTAMP)) AS USSTAMP,
                         LTRIM(RTRIM(LOGIN)) AS LOGIN
            FROM dbo.US
            WHERE LOWER(LTRIM(RTRIM(ISNULL(LOGIN, '')))) = :login
              AND ISNULL(INATIVO, 0) = 0
        """), {"login": login}).mappings().first()
        if not user:
            continue
        existing = db.session.execute(text("""
            SELECT TOP 1 ACESSOSSTAMP
            FROM dbo.ACESSOS WITH (UPDLOCK, HOLDLOCK)
            WHERE LOWER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = :login
              AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'PB_ANALYTICS'
        """), {"login": login}).scalar()
        if existing:
            db.session.execute(text("""
                UPDATE dbo.ACESSOS
                SET CONSULTAR = 1, USSTAMP = :user_stamp
                WHERE ACESSOSSTAMP = :access_stamp
            """), {"user_stamp": user["USSTAMP"], "access_stamp": existing})
        else:
            db.session.execute(text("""
                INSERT INTO dbo.ACESSOS (
                    ACESSOSSTAMP, UTILIZADOR, TABELA, CONSULTAR,
                    INSERIR, EDITAR, ELIMINAR, USSTAMP
                ) VALUES (
                    :access_stamp, :login, 'PB_ANALYTICS', 1,
                    0, 0, 0, :user_stamp
                )
            """), {
                "access_stamp": uuid.uuid4().hex.upper()[:25],
                "login": user["LOGIN"],
                "user_stamp": user["USSTAMP"],
            })

    db.session.commit()
