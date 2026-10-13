SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF COL_LENGTH('dbo.US', 'EXTERNO') IS NULL
BEGIN
    ALTER TABLE dbo.US
    ADD EXTERNO bit NOT NULL
        CONSTRAINT DF_US_EXTERNO DEFAULT (0) WITH VALUES;
END;

IF NOT EXISTS (
    SELECT 1
    FROM dbo.CAMPOS
    WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'US'
      AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = 'EXTERNO'
)
BEGIN
    INSERT INTO dbo.CAMPOS (
        CAMPOSSTAMP,
        ORDEM,
        NMCAMPO,
        DESCRICAO,
        TIPO,
        TABELA,
        LISTA,
        FILTRO,
        ADMIN,
        RONLY,
        TAM,
        ORDEM_MOBILE,
        TAM_MOBILE,
        OBRIGATORIO,
        VISIVEL,
        ORDEM_LISTA,
        TAM_LISTA,
        ORDEM_LISTA_MOBILE,
        TAM_LISTA_MOBILE,
        LISTA_MOBILE_LABEL
    )
    VALUES (
        LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
        35,
        'EXTERNO',
        'Externo',
        'BIT',
        'US',
        0,
        0,
        0,
        0,
        10,
        35,
        10,
        0,
        1,
        0,
        5,
        0,
        5,
        'Externo'
    );
END;

COMMIT TRANSACTION;
