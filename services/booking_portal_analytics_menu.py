"""Idempotent StationZero menu registration for portal analytics."""

from sqlalchemy import text

from models import db


GROUP_STAMP = "PBANALYTICSGROUP00000001"
ITEM_STAMP = "PBANALYTICSMENU000000001"


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
                :stamp, 1500, 'PortoBreak', '', '', 1,
                'fa-solid fa-chart-line', '', '', 0, 0
            )
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
                '/analytics/portobreak', 1, 'fa-solid fa-chart-column', '', '', 0, 0
            )
        """), {"stamp": ITEM_STAMP})

    db.session.commit()
