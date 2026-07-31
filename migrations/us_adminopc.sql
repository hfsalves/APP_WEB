IF COL_LENGTH('dbo.US', 'ADMINOPC') IS NULL
BEGIN
    ALTER TABLE dbo.US
        ADD ADMINOPC bit NOT NULL
            CONSTRAINT DF_US_ADMINOPC DEFAULT (0) WITH VALUES;
END;

MERGE dbo.CAMPOS AS target
USING (
    SELECT
        CAST('ADMINOPC' AS varchar(25)) AS NMCAMPO,
        CAST('Admin Obras' AS varchar(60)) AS DESCRICAO,
        CAST('BIT' AS varchar(18)) AS TIPO,
        CAST(48 AS int) AS ORDEM,
        CAST(10 AS int) AS TAM,
        CAST(58 AS int) AS ORDEM_MOBILE,
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

EXEC sys.sp_executesql N'
    UPDATE dbo.US
       SET ADMINOPC = 1
     WHERE LOWER(LTRIM(RTRIM(LOGIN))) IN (''sferreira'', ''srferreira'');
';
