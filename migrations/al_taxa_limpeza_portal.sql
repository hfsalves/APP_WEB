IF COL_LENGTH('dbo.AL', 'TXLIMPEZA') IS NULL
BEGIN
    ALTER TABLE dbo.AL
    ADD TXLIMPEZA NUMERIC(12, 2) NOT NULL
        CONSTRAINT DF_AL_TXLIMPEZA DEFAULT (0);

    EXEC(N'UPDATE dbo.AL SET TXLIMPEZA = 30.00;');
END;

IF NOT EXISTS (
    SELECT 1
    FROM dbo.CAMPOS
    WHERE UPPER(LTRIM(RTRIM(TABELA))) = 'AL'
      AND UPPER(LTRIM(RTRIM(NMCAMPO))) = 'TXLIMPEZA'
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
        COMBO,
        VIRTUAL,
        TAM,
        ORDEM_MOBILE,
        TAM_MOBILE,
        CONDICAO_VISIVEL,
        OBRIGATORIO,
        obrigatorio_se,
        formula,
        decimais,
        minimo,
        maximo,
        FILTRODEFAULT,
        VISIVEL,
        ORDEM_LISTA,
        TAM_LISTA,
        ORDEM_LISTA_MOBILE,
        TAM_LISTA_MOBILE,
        LISTA_MOBILE_BOLD,
        LISTA_MOBILE_ITALIC,
        LISTA_MOBILE_SHOW_LABEL,
        LISTA_MOBILE_LABEL,
        PROPRIEDADES
    )
    VALUES (
        LEFT(NEWID(), 25),
        185,
        'TXLIMPEZA',
        'Taxa de limpeza portal',
        'DECIMAL',
        'AL',
        0,
        0,
        0,
        0,
        '',
        '',
        10,
        43,
        10,
        '',
        0,
        '',
        '',
        2,
        0,
        999999999,
        '',
        1,
        0,
        10,
        0,
        10,
        0,
        0,
        1,
        'Taxa de limpeza portal',
        N'{}'
    );
END;

UPDATE dbo.CAMPOS
SET DESCRICAO = 'Taxa de limpeza portal',
    TIPO = 'DECIMAL',
    ORDEM = 185,
    TAM = 10,
    ORDEM_MOBILE = 43,
    TAM_MOBILE = 10,
    DECIMAIS = 2,
    MINIMO = 0,
    MAXIMO = 999999999,
    VISIVEL = 1
WHERE UPPER(LTRIM(RTRIM(TABELA))) = 'AL'
  AND UPPER(LTRIM(RTRIM(NMCAMPO))) = 'TXLIMPEZA';
