SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @menustamp varchar(25);
    DECLARE @modstamp varchar(25);

    SELECT TOP 1 @menustamp = LTRIM(RTRIM(ISNULL(MENUSTAMP, '')))
      FROM dbo.MENU
     WHERE LOWER(LTRIM(RTRIM(ISNULL(URL, '')))) IN ('/orcamentos', '/gr_orcamentos', '/gr360_orcamentos')
        OR UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'GR_ORCAMENTOS'
     ORDER BY
        CASE WHEN LOWER(LTRIM(RTRIM(ISNULL(URL, '')))) = '/orcamentos' THEN 0 ELSE 1 END,
        ISNULL(INATIVO, 0),
        ISNULL(ORDEM, 0);

    IF ISNULL(@menustamp, '') = ''
    BEGIN
        SET @menustamp = 'GRORCAMENTOS2026080300001';

        INSERT INTO dbo.MENU
        (
            MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM,
            NOVO, [ORDERBY], INATIVO, LARGURAS_EXATAS, LARGURAS_EXATAS_LISTA
        )
        VALUES
        (
            @menustamp, 205, 'Orçamentos', 'GR_ORCAMENTOS', '/orcamentos', 0,
            'fa-solid fa-file-invoice', '', 0, '', 0, 0, 0
        );
    END
    ELSE
    BEGIN
        UPDATE dbo.MENU
           SET ORDEM = 205,
               NOME = 'Orçamentos',
               TABELA = 'GR_ORCAMENTOS',
               URL = '/orcamentos',
               ADMIN = 0,
               ICONE = 'fa-solid fa-file-invoice',
               FORM = '',
               NOVO = 0,
               INATIVO = 0
         WHERE MENUSTAMP = @menustamp;
    END;

    IF OBJECT_ID('dbo.I18N_TRADUCOES', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.I18N_TRADUCOES AS target
        USING
        (
            SELECT 'MENU' AS ORIGEM, @menustamp AS ORISTAMP, 'pt_PT' AS IDIOMA, N'Orçamentos' AS TRADUCAO
            UNION ALL
            SELECT 'MENU', @menustamp, 'fr', N'Devis'
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

    SELECT TOP 1 @modstamp = LTRIM(RTRIM(ISNULL(MODSTAMP, '')))
      FROM dbo.MODULOS
     WHERE UPPER(LTRIM(RTRIM(ISNULL(CODIGO, '')))) = 'ADMIN'
       AND ISNULL(ATIVO, 0) = 1
     ORDER BY ISNULL(ORDEM, 0), MODSTAMP;

    IF ISNULL(@modstamp, '') = ''
        THROW 50001, 'O módulo ADMIN não existe ou não está ativo.', 1;

    DELETE FROM dbo.MOD_OBJETOS
     WHERE MENUSTAMP = @menustamp
       AND MODSTAMP <> @modstamp;

    IF EXISTS
    (
        SELECT 1
          FROM dbo.MOD_OBJETOS
         WHERE MODSTAMP = @modstamp
           AND MENUSTAMP = @menustamp
    )
    BEGIN
        UPDATE dbo.MOD_OBJETOS
           SET TIPO = 'MENU',
               OBJKEY = 'MENU:' + @menustamp,
               OBJNOME = 'Orçamentos',
               OBJROTA = '/orcamentos',
               ORDEM = 205,
               ATIVO = 1,
               DTALT = GETDATE(),
               USERALTERACAO = 'MIGRATION'
         WHERE MODSTAMP = @modstamp
           AND MENUSTAMP = @menustamp;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.MOD_OBJETOS
        (
            MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA,
            MENUSTAMP, ORDEM, ATIVO, DTCRI, DTALT, USERCRIACAO, USERALTERACAO
        )
        VALUES
        (
            LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
            @modstamp, 'MENU', 'MENU:' + @menustamp, 'Orçamentos', '/orcamentos',
            @menustamp, 205, 1, GETDATE(), GETDATE(), 'MIGRATION', 'MIGRATION'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
