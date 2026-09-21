SET NOCOUNT ON;

IF NOT EXISTS (SELECT 1 FROM dbo.MENU WHERE MENUSTAMP = 'PBANALYTICSGROUP00000001')
BEGIN
    INSERT INTO dbo.MENU (
        MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
    ) VALUES (
        'PBANALYTICSGROUP00000001', 1500, 'PortoBreak', '', '', 1,
        'fa-solid fa-chart-line', '', '', 0, 0
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM dbo.MENU
    WHERE MENUSTAMP = 'PBANALYTICSMENU000000001'
       OR LTRIM(RTRIM(ISNULL(URL, ''))) = '/analytics/portobreak'
)
BEGIN
    INSERT INTO dbo.MENU (
        MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
    ) VALUES (
        'PBANALYTICSMENU000000001', 1501, 'Analítica do Portal', 'PB_ANALYTICS',
        '/analytics/portobreak', 1, 'fa-solid fa-chart-column', '', '', 0, 0
    );
END;
