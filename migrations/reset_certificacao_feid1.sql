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

    DECLARE @CodValidacao VARCHAR(50) = (
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(X.COD_VALIDACAO_SERIE, '')))
        FROM dbo.FTS AS S
        INNER JOIN dbo.FTSX AS X
            ON X.FTSSTAMP = S.FTSSTAMP
        WHERE ISNULL(S.FEID, 0) = @TargetFEID
          AND LTRIM(RTRIM(ISNULL(X.COD_VALIDACAO_SERIE, ''))) <> ''
        ORDER BY ISNULL(S.NDOC, 0), LTRIM(RTRIM(ISNULL(S.SERIE, '')))
    );

    DECLARE @Series TABLE (
        DOC_TYPE VARCHAR(10) NOT NULL,
        NDOC INT NOT NULL,
        SERIE VARCHAR(30) NOT NULL,
        DESCR VARCHAR(100) NOT NULL,
        TIPOSAFT VARCHAR(10) NOT NULL,
        NO_SAFT BIT NOT NULL,
        ATIVA BIT NOT NULL,
        ESTADO INT NOT NULL,
        IS_DOC_TRANSPORTE BIT NOT NULL
    );

    INSERT INTO @Series (DOC_TYPE, NDOC, SERIE, DESCR, TIPOSAFT, NO_SAFT, ATIVA, ESTADO, IS_DOC_TRANSPORTE)
    VALUES
        ('FT', 1,  'AT', 'FT AT', 'FT', 0, 1, 0, 0),
        ('NC', 2,  'AT', 'NC AT', 'NC', 0, 1, 1, 0),
        ('FR', 5,  'AT', 'FR AT', 'FR', 0, 1, 1, 0),
        ('FS', 7,  'AT', 'FS AT', 'FS', 0, 1, 1, 0),
        ('PF', 9,  'AT', 'PF AT', 'PF', 1, 1, 1, 0),
        ('GT', 11, 'AT', 'GT AT', 'GT', 0, 1, 1, 1);

    DECLARE @InsertedSeries TABLE (
        NDOC INT NOT NULL,
        FTSSTAMP VARCHAR(25) NOT NULL
    );

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

    INSERT INTO dbo.FTS (
        FTSSTAMP, FESTAMP, NDOC, SERIE, DESCR, ATIVA, ESTADO, ANO, ULTIMO_FNO,
        DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO, NO_SAFT, TIPOSAFT, FEID, IS_DOC_TRANSPORTE
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
        ISNULL(@CodValidacao, ''),
        CASE WHEN ISNULL(@CodValidacao, '') <> '' THEN CONCAT(S.DOC_TYPE, '-', @CodValidacao) ELSE '' END,
        CASE WHEN ISNULL(@CodValidacao, '') <> '' THEN 1 ELSE 0 END,
        CASE WHEN ISNULL(@CodValidacao, '') <> '' THEN @Now ELSE CONVERT(DATETIME2, '19000101') END,
        CASE WHEN ISNULL(@CodValidacao, '') <> '' THEN 'Reset certificacao FEID 1' ELSE '' END,
        @Now,
        @Now,
        @UserLogin,
        @UserLogin,
        @TargetFEID
    FROM @InsertedSeries AS I
    INNER JOIN @Series AS S
        ON S.NDOC = I.NDOC;

    COMMIT TRANSACTION;

    SELECT
        'OK' AS RESULTADO,
        @TargetFEID AS FEID,
        @FESTAMP AS FESTAMP,
        @CodValidacao AS COD_VALIDACAO_BASE;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
