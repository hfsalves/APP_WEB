SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;
BEGIN TRY
    DECLARE @TargetFEID INT = 1;
    DECLARE @Now DATETIME2 = SYSDATETIME();
    DECLARE @UserLogin VARCHAR(50) = 'dev-reset';
    DECLARE @Ano INT = YEAR(GETDATE());
    DECLARE @FESTAMP VARCHAR(25) = (
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(FESTAMP, '')))
        FROM dbo.FE
        WHERE FEID = @TargetFEID
    );

    IF @TargetFEID <> 1
        THROW 51000, 'Este script so permite reset FEID = 1.', 1;

    IF ISNULL(@FESTAMP, '') = ''
        THROW 51000, 'A empresa FEID = 1 nao existe ou nao tem FESTAMP.', 1;

    DECLARE @Series TABLE (
        DOC_TYPE VARCHAR(10) NOT NULL,
        NDOC INT NOT NULL,
        SERIE VARCHAR(30) NOT NULL,
        DESCR VARCHAR(100) NOT NULL,
        TIPOSAFT VARCHAR(10) NOT NULL,
        CODIGO_VALIDACAO_AT VARCHAR(20) NOT NULL,
        NO_SAFT BIT NOT NULL,
        ATIVA BIT NOT NULL,
        ESTADO INT NOT NULL,
        IS_DOC_TRANSPORTE BIT NOT NULL
    );

    INSERT INTO @Series (DOC_TYPE, NDOC, SERIE, DESCR, TIPOSAFT, CODIGO_VALIDACAO_AT, NO_SAFT, ATIVA, ESTADO, IS_DOC_TRANSPORTE)
    VALUES
        ('FT', 1,  'FT', 'Fatura', 'FT', 'AA123456', 0, 1, 0, 0),
        ('NC', 2,  'NC', 'Nota de Cr??dito', 'NC', 'AA123459', 0, 1, 1, 0),
        ('FR', 5,  'FR', 'Fatura-Recibo', 'FR', 'AA123457', 0, 1, 1, 0),
        ('FS', 7,  'FS', 'Fatura Simplificada', 'FS', 'AA123458', 0, 1, 1, 0),
        ('PF', 9,  'PF', 'Fatura Proforma', 'PF', 'AA12345A', 1, 1, 1, 0),
        ('GT', 11, 'GT', 'Guia de Transporte', 'GT', 'AA12345B', 0, 1, 1, 1);

    DECLARE @InsertedSeries TABLE (
        NDOC INT NOT NULL,
        FTSSTAMP VARCHAR(25) NOT NULL
    );

    DECLARE @SampleArticles TABLE (
        REF VARCHAR(18) NOT NULL,
        DESIGN VARCHAR(60) NOT NULL,
        FAMILIA VARCHAR(18) NOT NULL,
        FAMINOME VARCHAR(60) NOT NULL,
        EPV DECIMAL(18,2) NOT NULL,
        TABIVA INT NOT NULL,
        TIPOPROD VARCHAR(1) NOT NULL,
        UNIDADE VARCHAR(10) NOT NULL
    );

    INSERT INTO @SampleArticles (REF, DESIGN, FAMILIA, FAMINOME, EPV, TABIVA, TIPOPROD, UNIDADE)
    VALUES
        ('ATC-P2301', 'Snack Bar Premium', 'PROD-23', 'Mercadorias 23%', 3.50, 2, 'P', 'UN'),
        ('ATC-P2302', 'Vinho Casa Reserva', 'PROD-23', 'Mercadorias 23%', 12.50, 2, 'P', 'UN'),
        ('ATC-P2303', 'Cabaz Regional', 'PROD-23', 'Mercadorias 23%', 24.90, 2, 'P', 'UN'),
        ('ATC-P2304', 'Amenities Deluxe', 'PROD-23', 'Mercadorias 23%', 9.80, 2, 'P', 'UN'),
        ('ATC-P2305', 'Kit Bebe Conforto', 'PROD-23', 'Mercadorias 23%', 15.00, 2, 'P', 'UN'),
        ('ATC-P0601', 'Agua Mineral 1,5L', 'PROD-06', 'Mercadorias 6%', 1.20, 1, 'P', 'UN'),
        ('ATC-P0602', 'Compota Caseira', 'PROD-06', 'Mercadorias 6%', 4.80, 1, 'P', 'UN'),
        ('ATC-P0603', 'Mel Artesanal', 'PROD-06', 'Mercadorias 6%', 6.50, 1, 'P', 'UN'),
        ('ATC-P0604', 'Azeite Virgem', 'PROD-06', 'Mercadorias 6%', 8.90, 1, 'P', 'UN'),
        ('ATC-P0605', 'Livro Guia Porto', 'PROD-06', 'Mercadorias 6%', 11.00, 1, 'P', 'UN'),
        ('ATC-P1301', 'Pequeno-Almoco Box', 'PROD-13', 'Mercadorias 13%', 9.50, 3, 'P', 'UN'),
        ('ATC-P1302', 'Brunch Menu', 'PROD-13', 'Mercadorias 13%', 14.00, 3, 'P', 'UN'),
        ('ATC-P1303', 'Tabua de Queijos', 'PROD-13', 'Mercadorias 13%', 18.00, 3, 'P', 'UN'),
        ('ATC-P1304', 'Menu Degustacao', 'PROD-13', 'Mercadorias 13%', 22.50, 3, 'P', 'UN'),
        ('ATC-P1305', 'Cabaz Breakfast', 'PROD-13', 'Mercadorias 13%', 17.90, 3, 'P', 'UN'),
        ('ATC-S2301', 'Limpeza Extra', 'SERV-23', 'Servicos 23%', 35.00, 2, 'S', 'SERV'),
        ('ATC-S2302', 'Late Checkout', 'SERV-23', 'Servicos 23%', 25.00, 2, 'S', 'SERV'),
        ('ATC-S2303', 'Early Check-in', 'SERV-23', 'Servicos 23%', 20.00, 2, 'S', 'SERV'),
        ('ATC-S2304', 'Transfer Aeroporto', 'SERV-23', 'Servicos 23%', 45.00, 2, 'S', 'SERV'),
        ('ATC-S2305', 'Lavandaria Express', 'SERV-23', 'Servicos 23%', 18.00, 2, 'S', 'SERV'),
        ('ATC-S2306', 'Aluguer Bicicleta', 'SERV-23', 'Servicos 23%', 22.00, 2, 'S', 'SERV'),
        ('ATC-S1301', 'Pequeno-Almoco Servico', 'SERV-13', 'Servicos 13%', 8.50, 3, 'S', 'SERV'),
        ('ATC-S1302', 'Jantar Privado', 'SERV-13', 'Servicos 13%', 45.00, 3, 'S', 'SERV'),
        ('ATC-S1303', 'Chef ao Domicilio', 'SERV-13', 'Servicos 13%', 75.00, 3, 'S', 'SERV'),
        ('ATC-S1304', 'Menu Room Service', 'SERV-13', 'Servicos 13%', 19.50, 3, 'S', 'SERV'),
        ('ATC-S0601', 'Visita Museu Guiada', 'SERV-06', 'Servicos 6%', 16.00, 1, 'S', 'SERV'),
        ('ATC-S0602', 'Bilhete Evento Cultural', 'SERV-06', 'Servicos 6%', 20.00, 1, 'S', 'SERV'),
        ('ATC-SIS01', 'Formacao Isenta', 'SERV-IS', 'Servicos Isentos', 60.00, 4, 'S', 'SERV'),
        ('ATC-SIS02', 'Servico Medico Isento', 'SERV-IS', 'Servicos Isentos', 80.00, 4, 'S', 'SERV'),
        ('ATC-SIS03', 'Seguro Viagem Isento', 'SERV-IS', 'Servicos Isentos', 14.00, 4, 'S', 'SERV');

    DELETE FROM dbo.FI
    WHERE FTSTAMP IN (
        SELECT FTSTAMP
        FROM dbo.FT
        WHERE ISNULL(FEID, 0) = @TargetFEID
    );

    DELETE FROM dbo.FT
    WHERE ISNULL(FEID, 0) = @TargetFEID;

    DELETE FROM dbo.FTSX
    WHERE FTSSTAMP IN (
        SELECT FTSSTAMP
        FROM dbo.FTS
        WHERE ISNULL(FEID, 0) = @TargetFEID
    );

    DELETE FROM dbo.FTS
    WHERE ISNULL(FEID, 0) = @TargetFEID;

    DELETE FROM dbo.ST
    WHERE ISNULL(FEID, 0) = @TargetFEID
      AND UPPER(LTRIM(RTRIM(ISNULL(REF, '')))) IN (
        SELECT UPPER(LTRIM(RTRIM(REF)))
        FROM @SampleArticles
      );

    INSERT INTO dbo.FTS (
        FTSSTAMP, FESTAMP, NDOC, SERIE, DESCR, ATIVA, ESTADO, ANO, ULTIMO_FNO,
        DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO, NO_SAFT, TIPOSAFT, FEID, CODIGO_VALIDACAO_AT, IS_DOC_TRANSPORTE
    )
    OUTPUT INSERTED.NDOC, INSERTED.FTSSTAMP INTO @InsertedSeries (NDOC, FTSSTAMP)
    SELECT
        LEFT(CONVERT(VARCHAR(36), NEWID()), 25),
        @FESTAMP,
        SRC.NDOC,
        SRC.SERIE,
        SRC.DESCR,
        SRC.ATIVA,
        SRC.ESTADO,
        @Ano,
        0,
        @Now,
        @Now,
        @UserLogin,
        @UserLogin,
        SRC.NO_SAFT,
        SRC.TIPOSAFT,
        @TargetFEID,
        SRC.CODIGO_VALIDACAO_AT,
        SRC.IS_DOC_TRANSPORTE
    FROM @Series AS SRC;

    INSERT INTO dbo.FTSX (
        FTSXSTAMP, FTSSTAMP, HASHVER, LAST_HASH, COD_VALIDACAO_SERIE, ATCUD_PREFIX,
        AT_SERIE_ESTADO, AT_SERIE_DATA, AT_SERIE_MSG,
        DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO, FEID
    )
    SELECT
        LEFT(CONVERT(VARCHAR(36), NEWID()), 25),
        I.FTSSTAMP,
        '',
        '',
        S.CODIGO_VALIDACAO_AT,
        '',
        1,
        @Now,
        'Reset certificacao FEID 1',
        @Now,
        @Now,
        @UserLogin,
        @UserLogin,
        @TargetFEID
    FROM @InsertedSeries AS I
    INNER JOIN @Series AS S
        ON S.NDOC = I.NDOC;

    INSERT INTO dbo.ST (
        STSTAMP, REF, DESIGN, FAMILIA, FAMINOME, STOCK, EPV, CPOC, TIPOPROD, UNIDADE, TABIVA, MOTISEIMP, FEID
    )
    SELECT
        LEFT(CONVERT(VARCHAR(36), NEWID()), 25),
        A.REF,
        A.DESIGN,
        A.FAMILIA,
        A.FAMINOME,
        CASE WHEN A.TIPOPROD = 'P' THEN 100 ELSE 0 END,
        A.EPV,
        CASE WHEN A.TIPOPROD = 'P' THEN ROUND(A.EPV * 0.55, 2) ELSE 0 END,
        A.TIPOPROD,
        A.UNIDADE,
        A.TABIVA,
        CASE WHEN A.TABIVA = 4 THEN 'M99' ELSE '' END,
        @TargetFEID
    FROM @SampleArticles AS A;

    COMMIT TRANSACTION;

    SELECT
        'OK' AS RESULTADO,
        @TargetFEID AS FEID,
        @FESTAMP AS FESTAMP,
        (SELECT COUNT(1) FROM @SampleArticles) AS ARTIGOS_TESTE;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
