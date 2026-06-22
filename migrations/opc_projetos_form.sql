DECLARE @menustamp varchar(25);

SELECT TOP 1 @menustamp = MENUSTAMP
FROM dbo.MENU
WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'OPC'
ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(MENUSTAMP, '')));

IF @menustamp IS NULL
BEGIN
    SET @menustamp = LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25);

    INSERT INTO dbo.MENU (MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM)
    VALUES (@menustamp, 0, 'Obras', 'OPC', '/generic/view/OPC', 0, 'fa-briefcase', 'OPC_PROJETOS_FORM');
END
ELSE
BEGIN
    UPDATE dbo.MENU
       SET NOME = CASE WHEN LTRIM(RTRIM(ISNULL(NOME, ''))) = '' THEN 'Obras' ELSE NOME END,
           URL = '/generic/view/OPC',
           FORM = 'OPC_PROJETOS_FORM'
     WHERE MENUSTAMP = @menustamp;
END;

DECLARE @fields TABLE (
    NMCAMPO varchar(25) NOT NULL,
    DESCRICAO varchar(60) NOT NULL,
    TIPO varchar(18) NOT NULL,
    ORDEM int NOT NULL,
    TAM int NOT NULL,
    ORDEM_MOBILE int NOT NULL,
    TAM_MOBILE int NOT NULL,
    LISTA bit NOT NULL,
    FILTRO bit NOT NULL,
    RONLY bit NOT NULL,
    OBRIGATORIO bit NOT NULL
);

INSERT INTO @fields (NMCAMPO, DESCRICAO, TIPO, ORDEM, TAM, ORDEM_MOBILE, TAM_MOBILE, LISTA, FILTRO, RONLY, OBRIGATORIO)
VALUES
    ('PROCESSO', 'Processo', 'TEXT', 11, 3, 11, 20, 1, 1, 0, 1),
    ('DESCRICAO', 'Obra', 'TEXT', 12, 6, 21, 20, 1, 1, 0, 1),
    ('NOME', 'Cliente', 'TEXT', 13, 3, 31, 20, 1, 1, 0, 0),
    ('U_ORIGEM', 'Origem', 'TEXT', 21, 3, 41, 20, 1, 1, 0, 0),
    ('DATAI', 'Data início', 'DATE', 22, 3, 51, 10, 1, 1, 0, 0),
    ('DATAF', 'Data fim', 'DATE', 23, 3, 52, 10, 1, 1, 0, 0),
    ('NO', 'Nº cliente', 'INT', 31, 2, 61, 10, 0, 0, 0, 0),
    ('DATAFECHO', 'Data fecho', 'DATE', 32, 2, 62, 10, 0, 0, 0, 0),
    ('OBS', 'Observações', 'TEXT', 33, 2, 71, 20, 0, 0, 0, 0),
    ('U_RG', 'RG', 'DECIMAL', 41, 2, 81, 10, 0, 0, 0, 0),
    ('U_RFT', 'RFT', 'DECIMAL', 42, 2, 82, 10, 0, 0, 0, 0),
    ('U_CODE', 'Código', 'TEXT', 43, 2, 91, 10, 0, 0, 0, 0),
    ('U_FACTOR', 'Factor', 'BIT', 51, 2, 101, 10, 0, 0, 0, 0),
    ('U_NMARCHE', 'Nº mercado', 'TEXT', 52, 3, 111, 20, 0, 0, 0, 0),
    ('U_CONTAFAC', 'Conta faturação', 'TEXT', 53, 3, 121, 20, 0, 0, 0, 0),
    ('U_IBAN2', 'IBAN', 'TEXT', 61, 6, 131, 20, 0, 0, 0, 0);

MERGE dbo.CAMPOS AS target
USING @fields AS source
   ON UPPER(LTRIM(RTRIM(ISNULL(target.TABELA, '')))) = 'OPC'
  AND UPPER(LTRIM(RTRIM(ISNULL(target.NMCAMPO, '')))) = source.NMCAMPO
WHEN MATCHED THEN
    UPDATE SET
        DESCRICAO = source.DESCRICAO,
        TIPO = source.TIPO,
        ORDEM = source.ORDEM,
        TAM = source.TAM,
        ORDEM_MOBILE = source.ORDEM_MOBILE,
        TAM_MOBILE = source.TAM_MOBILE,
        LISTA = source.LISTA,
        FILTRO = source.FILTRO,
        RONLY = source.RONLY,
        OBRIGATORIO = source.OBRIGATORIO
WHEN NOT MATCHED THEN
    INSERT (
        CAMPOSSTAMP, ORDEM, NMCAMPO, DESCRICAO, TIPO, TABELA,
        LISTA, FILTRO, FILTRODEFAULT, ADMIN, RONLY, COMBO, VIRTUAL,
        TAM, ORDEM_MOBILE, TAM_MOBILE, CONDICAO_VISIVEL, OBRIGATORIO
    )
    VALUES (
        LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
        source.ORDEM, source.NMCAMPO, source.DESCRICAO, source.TIPO, 'OPC',
        source.LISTA, source.FILTRO, '', 0, source.RONLY, '', '',
        source.TAM, source.ORDEM_MOBILE, source.TAM_MOBILE, '', source.OBRIGATORIO
    );

IF COL_LENGTH('dbo.CAMPOS', 'ORDEM_LISTA') IS NOT NULL
BEGIN
    UPDATE C
       SET ORDEM_LISTA = F.ORDEM,
           TAM_LISTA = F.TAM,
           ORDEM_LISTA_MOBILE = F.ORDEM_MOBILE,
           TAM_LISTA_MOBILE = F.TAM_MOBILE
      FROM dbo.CAMPOS C
      INNER JOIN @fields F
        ON UPPER(LTRIM(RTRIM(ISNULL(C.NMCAMPO, '')))) = F.NMCAMPO
     WHERE UPPER(LTRIM(RTRIM(ISNULL(C.TABELA, '')))) = 'OPC';
END;
