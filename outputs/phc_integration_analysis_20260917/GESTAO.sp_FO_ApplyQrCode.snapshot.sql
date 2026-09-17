
-- =============================================================
-- SP: Aplicar QR_CODE da AT (Portugal) ao documento de compras
--     Atualiza FO (cabeçalho) e recria FN (linhas por taxa de IVA)
--
-- Regras (conforme pedido):
--   FO:
--     DOCNOME  = nome do documento (mapeamento simples por D)
--     ADOC     = número do documento (parte à direita do "/" em G)
--     NOME     = nome do fornecedor (via view V_FL) ou "Fornecedor não Encontrado"
--     ETOTAL   = total do documento (O)
--     DATA     = data do documento (F)
--     TIPO     = "FO"
--     DOCDATA  = data do documento (F)
--     FOANO    = ano do documento
--     ETTIVA   = total IVA (N)
--     ETTILIQ  = total base (soma das bases por taxa; fallback = O - N)
--     NIF (coluna a detetar) = NIF do fornecedor (A)
--
--   FN (1 linha por taxa):
--     FNSTAMP     = LEFT(NEWID(),25)
--     FOSTAMP     = FO.FOSTAMP
--     REF/DESIGN  = ''
--     TAXAIVA     = percentagem (23 / 13 / 6 / 0)
--     TABIVA      = código da taxa (1=6, 2=23, 3=13, 4=0)
--     QTT         = 1
--     EPV         = base
--     ETILIQUIDO  = base
--     LORDEM      = ordem
--
-- Observações:
--   - O QR nem sempre traz explicitamente as percentagens por grupo.
--     Aqui calculamos taxa_percent = round(IVA / Base * 100, 0)
--     e mapeamos com tolerância.
--   - Linhas são extraídas de pares I5/I6, I7/I8, I9/I10, ..., I(MaxI-1)/I(MaxI)
-- =============================================================

CREATE   PROCEDURE [dbo].[sp_FO_ApplyQrCode]
    @FOSTAMP VARCHAR(25),
    @MaxI    INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRAN;

        ---------------------------------------------------------------------
        -- 1) LER QR_CODE do FO
        ---------------------------------------------------------------------
        DECLARE @QR NVARCHAR(1000);

        SELECT @QR = QR_CODE
        FROM FO WITH (UPDLOCK, ROWLOCK)
        WHERE FOSTAMP = @FOSTAMP;

        IF @QR IS NULL OR LTRIM(RTRIM(@QR)) = N''
        BEGIN
            RAISERROR('FO.QR_CODE vazio para o FOSTAMP=%s', 16, 1, @FOSTAMP);
            ROLLBACK TRAN;
            RETURN;
        END

        ---------------------------------------------------------------------
        -- 2) PARSER: "A:...*B:...*..." -> tabela Key/Value
        ---------------------------------------------------------------------
        DECLARE @kv TABLE (
            k NVARCHAR(20)  NOT NULL,
            v NVARCHAR(400) NOT NULL
        );

        DECLARE @x XML =
            CAST(N'<i>' + REPLACE(REPLACE(@QR, N'&', N'&amp;'), N'*', N'</i><i>') + N'</i>' AS XML);

        INSERT INTO @kv(k, v)
        SELECT
            LEFT(T.c.value('.', 'nvarchar(400)'),
                 NULLIF(CHARINDEX(':', T.c.value('.', 'nvarchar(400)')) - 1, -1)) AS k,
            SUBSTRING(T.c.value('.', 'nvarchar(400)'),
                      CHARINDEX(':', T.c.value('.', 'nvarchar(400)')) + 1,
                      400) AS v
        FROM @x.nodes('/i') T(c)
        WHERE CHARINDEX(':', T.c.value('.', 'nvarchar(400)')) > 0;

        ---------------------------------------------------------------------
        -- 3) CAMPOS PRINCIPAIS DO QR (FO)
        ---------------------------------------------------------------------
        DECLARE
            @NIF_FORN      NVARCHAR(20)  = (SELECT TOP 1 v FROM @kv WHERE k = N'A'),
            @DOC_TIPO      NVARCHAR(10)  = (SELECT TOP 1 v FROM @kv WHERE k = N'D'),
            @DOC_SERIE     NVARCHAR(60)  = (SELECT TOP 1 v FROM @kv WHERE k = N'G'),
            @DATA_YYYYMMDD NVARCHAR(20)  = (SELECT TOP 1 v FROM @kv WHERE k = N'F'),
            @TOTAL_IVA     DECIMAL(18,2) = TRY_CONVERT(DECIMAL(18,2), (SELECT TOP 1 v FROM @kv WHERE k = N'N')),
            @TOTAL         DECIMAL(18,2) = TRY_CONVERT(DECIMAL(18,2), (SELECT TOP 1 v FROM @kv WHERE k = N'O'));

        -- Data do documento (YYYYMMDD)
        DECLARE @DATA DATE =
            CASE
                WHEN @DATA_YYYYMMDD IS NULL THEN NULL
                WHEN LEN(@DATA_YYYYMMDD) >= 8 THEN TRY_CONVERT(date,
                    STUFF(STUFF(LEFT(@DATA_YYYYMMDD,8), 5, 0, '-'), 8, 0, '-'))
                ELSE NULL
            END;

        -- Número do documento (ADOC): parte à direita do "/" em G
        DECLARE @ADOC NVARCHAR(40) =
            CASE
                WHEN @DOC_SERIE IS NULL THEN NULL
                WHEN CHARINDEX('/', @DOC_SERIE) > 0 THEN RIGHT(@DOC_SERIE, LEN(@DOC_SERIE) - CHARINDEX('/', @DOC_SERIE))
                ELSE @DOC_SERIE
            END;

        -- Nome do documento (DOCNOME): mapeamento simples
        DECLARE @DOCNOME NVARCHAR(60) =
            CASE @DOC_TIPO
                WHEN N'FT' THEN N'Fatura'
                WHEN N'FR' THEN N'Fatura-Recibo'
                ELSE ISNULL(@DOC_TIPO, N'Documento')
            END;

        ---------------------------------------------------------------------
        -- 4) EXTRAIR LINHAS DE IVA (pares I5/I6, I7/I8, I9/I10, ...)
        ---------------------------------------------------------------------
        DECLARE @lines TABLE(
            l_ordem INT IDENTITY(1,1),
            base         DECIMAL(18,2) NULL,
            iva          DECIMAL(18,2) NULL,
            taxa_percent DECIMAL(18,2) NULL,  -- 6/13/23/0
            tabiva_code  INT NULL             -- 1/3/2/4
        );

        DECLARE @i INT = 5;
        WHILE @i <= @MaxI
        BEGIN
            DECLARE @kBase NVARCHAR(10) = N'I' + CONVERT(NVARCHAR(10), @i);
            DECLARE @kIva  NVARCHAR(10) = N'I' + CONVERT(NVARCHAR(10), @i + 1);

            DECLARE @base DECIMAL(18,2) = TRY_CONVERT(DECIMAL(18,2), (SELECT TOP 1 v FROM @kv WHERE k = @kBase));
            DECLARE @iva  DECIMAL(18,2) = TRY_CONVERT(DECIMAL(18,2), (SELECT TOP 1 v FROM @kv WHERE k = @kIva));

            IF @base IS NOT NULL AND @iva IS NOT NULL
            BEGIN
                DECLARE @taxa_percent DECIMAL(18,2) =
                    CASE WHEN @base = 0 THEN 0 ELSE ROUND((@iva / NULLIF(@base,0)) * 100.0, 0) END;

                -- Mapear para códigos internos (tolerância)
                DECLARE @tabiva_code INT =
                    CASE
                        WHEN @iva = 0 OR @taxa_percent = 0 THEN 4
                        WHEN @taxa_percent BETWEEN 5 AND 7 THEN 1     -- 6%
                        WHEN @taxa_percent BETWEEN 12 AND 14 THEN 3   -- 13%
                        WHEN @taxa_percent BETWEEN 22 AND 24 THEN 2   -- 23%
                        ELSE NULL
                    END;

                INSERT INTO @lines(base, iva, taxa_percent, tabiva_code)
                VALUES(@base, @iva, @taxa_percent, @tabiva_code);
            END

            SET @i += 2;
        END

        -- Total base: soma das bases por taxa; fallback = total - total_iva
        DECLARE @TOTAL_BASE DECIMAL(18,2) = (SELECT SUM(base) FROM @lines);
        IF @TOTAL_BASE IS NULL AND @TOTAL IS NOT NULL AND @TOTAL_IVA IS NOT NULL
            SET @TOTAL_BASE = @TOTAL - @TOTAL_IVA;

        ---------------------------------------------------------------------
        -- 5) Nome do fornecedor (NOME) - via VIEW V_FL
        --     Se não existir: "Fornecedor não Encontrado"
        ---------------------------------------------------------------------
        DECLARE @NOME_FORN NVARCHAR(200) = NULL;
        DECLARE @NO_FORN   INT = 0;

        IF OBJECT_ID('dbo.V_FL') IS NOT NULL
        BEGIN
            -- Ajusta nomes de colunas se necessário (NOME / NIF / NCONT / NO)
            SELECT TOP 1
                   @NOME_FORN = NULLIF(LTRIM(RTRIM(v.NOME)), ''),
                   @NO_FORN   = v.NO
            FROM dbo.V_FL v
            WHERE TRY_CONVERT(NVARCHAR(20), v.NCONT) = @NIF_FORN;
        END

        IF @NOME_FORN IS NULL
        BEGIN
            SET @NOME_FORN = N'Fornecedor não Encontrado';
            SET @NO_FORN   = 0;
        END

        ---------------------------------------------------------------------
        -- 6) DETETAR QUAL É A COLUNA DE NIF EXISTENTE NO FO
        ---------------------------------------------------------------------
        DECLARE @FO_NIF_COL SYSNAME = NULL;

        IF COL_LENGTH('dbo.FO', 'NCONT') IS NOT NULL SET @FO_NIF_COL = 'NCONT';
        ELSE IF COL_LENGTH('dbo.FO', 'NIF') IS NOT NULL SET @FO_NIF_COL = 'NIF';
        ELSE IF COL_LENGTH('dbo.FO', 'NCONTRIB') IS NOT NULL SET @FO_NIF_COL = 'NCONTRIB';
        ELSE IF COL_LENGTH('dbo.FO', 'CONTRIB') IS NOT NULL SET @FO_NIF_COL = 'CONTRIB';
        ELSE IF COL_LENGTH('dbo.FO', 'NIF_FORN') IS NOT NULL SET @FO_NIF_COL = 'NIF_FORN';
        ELSE IF COL_LENGTH('dbo.FO', 'NIFFORN') IS NOT NULL SET @FO_NIF_COL = 'NIFFORN';

        ---------------------------------------------------------------------
        -- 7) Atualizar FO (dinâmico só para a coluna do NIF)
        ---------------------------------------------------------------------
        DECLARE @sql NVARCHAR(MAX) =
N'UPDATE FO
  SET DOCNOME = @DOCNOME,
      ADOC    = @ADOC,
      NOME    = @NOME_FORN,
      NO      = @NO_FORN,
      ETOTAL  = @TOTAL,
      DATA    = @DATA,
      TIPO    = ''FO'',
      DOCDATA = @DATA,
      FOANO   = CASE WHEN @DATA IS NULL THEN NULL ELSE YEAR(@DATA) END,
      ETTIVA  = @TOTAL_IVA,
      ETTILIQ = @TOTAL_BASE'
+ CASE WHEN @FO_NIF_COL IS NOT NULL THEN N',
      ' + QUOTENAME(@FO_NIF_COL) + N' = @NIF_FORN' ELSE N'' END
+ N'
 WHERE FOSTAMP = @FOSTAMP;';

        EXEC sp_executesql
            @sql,
            N'@DOCNOME NVARCHAR(60), @ADOC NVARCHAR(40), @NO_FORN INT, @NOME_FORN NVARCHAR(200),
              @TOTAL DECIMAL(18,2), @DATA DATE, @TOTAL_IVA DECIMAL(18,2), @TOTAL_BASE DECIMAL(18,2),
              @NIF_FORN NVARCHAR(20), @FOSTAMP VARCHAR(25)',
            @DOCNOME=@DOCNOME, @ADOC=@ADOC, @NO_FORN = @NO_FORN, @NOME_FORN=@NOME_FORN,
            @TOTAL=@TOTAL, @DATA=@DATA, @TOTAL_IVA=@TOTAL_IVA, @TOTAL_BASE=@TOTAL_BASE,
            @NIF_FORN=@NIF_FORN, @FOSTAMP=@FOSTAMP;

        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR('FO não encontrado para o FOSTAMP=%s', 16, 1, @FOSTAMP);
            ROLLBACK TRAN;
            RETURN;
        END

        ---------------------------------------------------------------------
        -- 8) Recriar FN (uma linha por taxa)
        --     IMPORTANTE: TAXAIVA = percentagem | TABIVA = código (1/2/3/4)
        ---------------------------------------------------------------------
        DELETE FROM FN WHERE FOSTAMP = @FOSTAMP;

        INSERT INTO FN (
            FNSTAMP,
            FOSTAMP,
            REF,
            DESIGN,
            TAXAIVA,
            TABIVA,
            QTT,
            EPV,
            ETILIQUIDO,
            LORDEM
        )
        SELECT
            LEFT(CONVERT(VARCHAR(36), NEWID()), 25) AS FNSTAMP,
            @FOSTAMP                                AS FOSTAMP,
            ''                                      AS REF,
            ''                                      AS DESIGN,
            ISNULL(taxa_percent, 0)                 AS TAXAIVA,
            ISNULL(tabiva_code, 0)                  AS TABIVA,
            1                                       AS QTT,
            base                                    AS EPV,
            base                                    AS ETILIQUIDO,
            l_ordem                                 AS LORDEM
        FROM @lines
        ORDER BY l_ordem;

        COMMIT TRAN;

        -- Output útil
        SELECT
            @FOSTAMP AS FOSTAMP,
            @FO_NIF_COL AS FO_NIF_COL_USADA,
            @NIF_FORN AS NIF_FORNECEDOR,
            @NOME_FORN AS NOME_FORNECEDOR,
            @DOC_TIPO AS DOC_TIPO,
            @DOC_SERIE AS DOC_SERIE_RAW,
            @ADOC AS ADOC,
            @DATA AS DATA_DOC,
            @TOTAL_BASE AS TOTAL_BASE,
            @TOTAL_IVA AS TOTAL_IVA,
            @TOTAL AS TOTAL_COM_IVA,
            (SELECT COUNT(1) FROM @lines) AS NUM_LINHAS_IVA;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;

        DECLARE @Err NVARCHAR(2048) = ERROR_MESSAGE();
        DECLARE @ErrNum INT = ERROR_NUMBER();
        RAISERROR('sp_FO_ApplyQrCode falhou (%d): %s', 16, 1, @ErrNum, @Err);
        RETURN;
    END CATCH
END

