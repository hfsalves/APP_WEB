/* GR360_CORE — Menus do registo de ponto no módulo ADMIN / Colaboradores */
SET XACT_ABORT ON;
GO
BEGIN TRANSACTION;

IF NOT EXISTS (SELECT 1 FROM dbo.MENU WHERE TABELA = 'PONTO' AND URL = '/ponto/registo')
BEGIN
    INSERT INTO dbo.MENU (ORDEM, NOME, TABELA, URL, FORM, ICONE, ADMIN, NOVO, INATIVO)
    VALUES (1360, 'Registo diário de ponto', 'PONTO', '/ponto/registo', '', 'fa-solid fa-clock', 0, 0, 0);
END;

IF NOT EXISTS (SELECT 1 FROM dbo.MENU WHERE TABELA = 'PONTO' AND URL = '/ponto/resumo-mensal')
BEGIN
    INSERT INTO dbo.MENU (ORDEM, NOME, TABELA, URL, FORM, ICONE, ADMIN, NOVO, INATIVO)
    VALUES (1361, 'Resumo mensal de ponto', 'PONTO', '/ponto/resumo-mensal', '', 'fa-solid fa-calendar-check', 0, 0, 0);
END;

/* O dashboard e a sidebar usam a tradução do MENU quando o utilizador está em francês. */
IF OBJECT_ID('dbo.I18N_TRADUCOES', 'U') IS NOT NULL
BEGIN
    MERGE dbo.I18N_TRADUCOES AS target
    USING
    (
        SELECT
            'MENU' AS ORIGEM,
            M.MENUSTAMP AS ORISTAMP,
            'fr' AS IDIOMA,
            CASE M.URL
                WHEN '/ponto/registo' THEN N'Pointage journalier'
                WHEN '/ponto/resumo-mensal' THEN N'Résumé mensuel du pointage'
            END AS TRADUCAO
        FROM dbo.MENU M
        WHERE M.TABELA = 'PONTO'
          AND M.URL IN ('/ponto/registo', '/ponto/resumo-mensal')
    ) AS source
       ON target.ORIGEM = source.ORIGEM
      AND target.ORISTAMP = source.ORISTAMP
      AND target.IDIOMA = source.IDIOMA
    WHEN MATCHED THEN
        UPDATE SET TRADUCAO = source.TRADUCAO
    WHEN NOT MATCHED THEN
        INSERT (ORIGEM, ORISTAMP, IDIOMA, TRADUCAO)
        VALUES (source.ORIGEM, source.ORISTAMP, source.IDIOMA, source.TRADUCAO);
END;

DECLARE @admin_modstamp varchar(25) = (
    SELECT TOP 1 MODSTAMP
    FROM dbo.MODULOS
    WHERE UPPER(LTRIM(RTRIM(ISNULL(NOME, '')))) = 'ADMIN'
    ORDER BY MODSTAMP
);

IF @admin_modstamp IS NULL
    THROW 50003, 'Módulo ADMIN não encontrado.', 1;

INSERT INTO dbo.MOD_OBJETOS
(
    MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA,
    MENUSTAMP, ORDEM, ATIVO, DTCRI, DTALT, USERCRIACAO, USERALTERACAO
)
SELECT
    LEFT(CONVERT(varchar(36), NEWID()), 25),
    @admin_modstamp,
    'MENU',
    CONCAT('MENU:', M.MENUSTAMP),
    M.NOME,
    M.URL,
    M.MENUSTAMP,
    M.ORDEM,
    1,
    GETDATE(),
    GETDATE(),
    'sistema',
    'sistema'
FROM dbo.MENU M
WHERE M.TABELA = 'PONTO'
  AND M.URL IN ('/ponto/registo', '/ponto/resumo-mensal')
  AND NOT EXISTS (
      SELECT 1 FROM dbo.MOD_OBJETOS MO
      WHERE MO.MODSTAMP = @admin_modstamp
        AND MO.OBJKEY = CONCAT('MENU:', M.MENUSTAMP)
  );

COMMIT TRANSACTION;
GO
