SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH('dbo.US', 'VENDEDOR') IS NULL
    BEGIN
        ALTER TABLE dbo.US
            ADD VENDEDOR int NOT NULL
                CONSTRAINT DF_US_VENDEDOR DEFAULT (0) WITH VALUES;
    END;

    MERGE dbo.CAMPOS AS target
    USING (
        SELECT
            CAST('VENDEDOR' AS varchar(25)) AS NMCAMPO,
            CAST('Vendedor' AS varchar(60)) AS DESCRICAO,
            CAST('INT' AS varchar(18)) AS TIPO,
            CAST(32 AS int) AS ORDEM,
            CAST(10 AS int) AS TAM,
            CAST(32 AS int) AS ORDEM_MOBILE,
            CAST(10 AS int) AS TAM_MOBILE
    ) AS source
       ON UPPER(LTRIM(RTRIM(ISNULL(target.TABELA, '')))) = 'US'
      AND UPPER(LTRIM(RTRIM(ISNULL(target.NMCAMPO, '')))) = source.NMCAMPO
    WHEN MATCHED THEN
        UPDATE SET
            DESCRICAO = source.DESCRICAO,
            TIPO = source.TIPO,
            ORDEM = source.ORDEM,
            TAM = source.TAM,
            ORDEM_MOBILE = source.ORDEM_MOBILE,
            TAM_MOBILE = source.TAM_MOBILE,
            LISTA = 0,
            FILTRO = 0,
            ADMIN = 1,
            VISIVEL = 1,
            RONLY = 0,
            OBRIGATORIO = 0
    WHEN NOT MATCHED THEN
        INSERT (
            CAMPOSSTAMP, ORDEM, NMCAMPO, DESCRICAO, TIPO, TABELA,
            LISTA, FILTRO, FILTRODEFAULT, ADMIN, RONLY, COMBO, VIRTUAL, VISIVEL,
            TAM, ORDEM_MOBILE, TAM_MOBILE, CONDICAO_VISIVEL, OBRIGATORIO
        )
        VALUES (
            LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
            source.ORDEM, source.NMCAMPO, source.DESCRICAO, source.TIPO, 'US',
            0, 0, '', 1, 0, '', '', 1,
            source.TAM, source.ORDEM_MOBILE, source.TAM_MOBILE, '', 0
        );

    IF OBJECT_ID('dbo.I18N_TRADUCOES', 'U') IS NOT NULL
    BEGIN
        DECLARE @camposstamp varchar(25);

        SELECT TOP 1 @camposstamp = LTRIM(RTRIM(ISNULL(CAMPOSSTAMP, '')))
          FROM dbo.CAMPOS
         WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'US'
           AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = 'VENDEDOR';

        IF ISNULL(@camposstamp, '') <> ''
        BEGIN
            MERGE dbo.I18N_TRADUCOES AS target
            USING (
                SELECT
                    CAST('CAMPOS' AS varchar(10)) AS ORIGEM,
                    @camposstamp AS ORISTAMP,
                    CAST('fr' AS varchar(10)) AS IDIOMA,
                    CAST(N'Vendeur' AS nvarchar(250)) AS TRADUCAO
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
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
