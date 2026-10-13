/*
  Excecao historica do SECRET GARDEN.

  Ate 2026-09-30 o alojamento era de EXPLORACAO. A partir de 2026-10-01
  passa a usar a configuracao atual de dbo.AL.

  A classificacao usa DATAIN para manter cada reserva num unico regime.
  O script inverso esta em secret_garden_tipo_historico_rollback.sql.
*/
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    EXEC(N'
ALTER VIEW dbo.v_diario_v2
AS

/* Reservas ativas (diario) */
SELECT
    TIPO     = A.TIPO_AL,
    EMPRESA  = COALESCE(AL1.EMPRESA, AL2.EMPRESA),
    CCUSTO   = RS.ALOJAMENTO,
    nmdos    = ''RESERVA'',
    obrano   = 0,
    dataobra = RS.DATAIN,
    DATA     = DATEADD(DAY, N.n - 1, RS.DATAIN),
    RS.NOME,
    TOTAL    = ROUND(CALC.RENDIMENTO_TOTAL, 2),
    RS.NOITES,
    DIA      = N.n,
    VALOR    = CASE
        WHEN N.n <= RS.NOITES
            THEN ROUND(CALC.RENDIMENTO_TOTAL / NULLIF(RS.NOITES, 0), 2)
        ELSE 0
    END,
    OBS      = CASE
        WHEN N.n = 1 THEN ''Check-In''
        WHEN N.n = RS.NOITES + 1 THEN ''Check-Out''
        ELSE ''---''
    END,
    RS.ORIGEM,
    RS.RESERVA
FROM dbo.RS AS RS
CROSS APPLY (
    SELECT TOP (
        CASE
            WHEN RS.NOITES IS NULL OR RS.NOITES < 0 THEN 0
            ELSE CONVERT(int, RS.NOITES) + 1
        END
    ) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects AS ao
) AS N
LEFT JOIN dbo.AL AS AL1 ON AL1.NOME = RS.ALOJAMENTO
LEFT JOIN dbo.AL AS AL2 ON AL2.NOMETG = RS.ALOJAMENTO
CROSS APPLY (
    SELECT
        TIPO_AL = CASE
            WHEN UPPER(LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, '''')))) COLLATE Latin1_General_CI_AI = ''SECRET GARDEN''
             AND RS.DATAIN < CONVERT(date, ''20261001'', 112)
                THEN ''EXPLORACAO''
            ELSE COALESCE(AL1.TIPO, AL2.TIPO)
        END,
        COMISSAO_AL  = COALESCE(AL1.COMISSAO, AL2.COMISSAO, 0),
        FTLIMPEZA_AL = COALESCE(AL1.FTLIMPEZA, AL2.FTLIMPEZA, 0)
) AS A
CROSS APPLY (
    SELECT TAXA_PLATAFORMA = CASE
        WHEN COALESCE(RS.ESTADIA, 0) + COALESCE(RS.LIMPEZA, 0) = 0 THEN 0
        ELSE COALESCE(RS.COMISSAO, 0)
             / NULLIF(COALESCE(RS.ESTADIA, 0) + COALESCE(RS.LIMPEZA, 0), 0)
    END
) AS P
CROSS APPLY (
    SELECT RENDIMENTO_TOTAL = CASE
        WHEN A.TIPO_AL = ''GESTAO'' AND A.FTLIMPEZA_AL = 1 THEN
            COALESCE(RS.ESTADIA, 0) * (1 - P.TAXA_PLATAFORMA) * (A.COMISSAO_AL / 100.0)
            + COALESCE(RS.LIMPEZA, 0) * (1 - P.TAXA_PLATAFORMA)
        WHEN A.TIPO_AL = ''GESTAO'' THEN
            (COALESCE(RS.ESTADIA, 0) + COALESCE(RS.LIMPEZA, 0) - COALESCE(RS.COMISSAO, 0))
            * (A.COMISSAO_AL / 100.0)
        ELSE
            COALESCE(RS.ESTADIA, 0) + COALESCE(RS.LIMPEZA, 0) - COALESCE(RS.COMISSAO, 0)
    END
) AS CALC
WHERE RS.CANCELADA = 0

UNION ALL

/* Reservas canceladas */
SELECT
    TIPO     = A.TIPO_AL,
    EMPRESA  = COALESCE(AL1.EMPRESA, AL2.EMPRESA),
    CCUSTO   = RS.ALOJAMENTO,
    nmdos    = ''RESERVA'',
    obrano   = 0,
    dataobra = RS.DATAIN,
    DATA     = RS.DATAIN,
    RS.NOME,
    TOTAL    = ROUND(CASE
        WHEN A.TIPO_AL = ''GESTAO''
            THEN COALESCE(RS.PCANCEL, 0) * (A.COMISSAO_AL / 100.0)
        ELSE COALESCE(RS.PCANCEL, 0)
    END, 2),
    NOITES   = 0,
    DIA      = 0,
    VALOR    = ROUND(CASE
        WHEN A.TIPO_AL = ''GESTAO''
            THEN COALESCE(RS.PCANCEL, 0) * (A.COMISSAO_AL / 100.0)
        ELSE COALESCE(RS.PCANCEL, 0)
    END, 2),
    OBS      = ''CANCELADA'',
    RS.ORIGEM,
    RS.RESERVA
FROM dbo.RS AS RS
LEFT JOIN dbo.AL AS AL1 ON AL1.NOME = RS.ALOJAMENTO
LEFT JOIN dbo.AL AS AL2 ON AL2.NOMETG = RS.ALOJAMENTO
CROSS APPLY (
    SELECT
        TIPO_AL = CASE
            WHEN UPPER(LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, '''')))) COLLATE Latin1_General_CI_AI = ''SECRET GARDEN''
             AND RS.DATAIN < CONVERT(date, ''20261001'', 112)
                THEN ''EXPLORACAO''
            ELSE COALESCE(AL1.TIPO, AL2.TIPO)
        END,
        COMISSAO_AL = COALESCE(AL1.COMISSAO, AL2.COMISSAO, 0)
) AS A
WHERE RS.CANCELADA = 1
  AND COALESCE(RS.PCANCEL, 0) > 0;
');

    EXEC(N'
ALTER VIEW dbo.v_diario_all
AS

/* Reservas ativas (diario) */
SELECT
    TIPO = CASE
        WHEN UPPER(LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, '''')))) COLLATE Latin1_General_CI_AI = ''SECRET GARDEN''
         AND RS.DATAIN < CONVERT(date, ''20261001'', 112)
            THEN ''EXPLORACAO''
        ELSE COALESCE(AL1.TIPO, AL2.TIPO)
    END,
    EMPRESA  = COALESCE(AL1.EMPRESA, AL2.EMPRESA),
    CCUSTO   = RS.ALOJAMENTO,
    nmdos    = ''RESERVA'',
    obrano   = 0,
    dataobra = RS.DATAIN,
    DATA     = DATEADD(DAY, N.n - 1, RS.DATAIN),
    RS.NOME,
    TOTAL    = ROUND((RS.ESTADIA + RS.LIMPEZA) * 0.85, 2),
    RS.NOITES,
    DIA      = N.n,
    VALOR    = CASE
        WHEN N.n <= RS.NOITES
            THEN ROUND(CAST((RS.ESTADIA + RS.LIMPEZA) / RS.NOITES AS numeric(12,2)) * 0.85, 2)
        ELSE 0
    END,
    OBS      = CASE
        WHEN N.n = 1 THEN ''Check-In''
        WHEN N.n = RS.NOITES + 1 THEN ''Check-Out''
        ELSE ''---''
    END,
    RS.ORIGEM,
    RS.RESERVA
FROM dbo.RS AS RS
CROSS APPLY (
    SELECT TOP (
        CASE
            WHEN RS.NOITES IS NULL OR RS.NOITES < 0 THEN 0
            ELSE CONVERT(int, RS.NOITES) + 1
        END
    ) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects AS ao
) AS N
LEFT JOIN dbo.AL AS AL1 ON AL1.NOME = RS.ALOJAMENTO
LEFT JOIN dbo.AL AS AL2 ON AL2.NOMETG = RS.ALOJAMENTO
WHERE RS.CANCELADA = 0

UNION ALL

/* Reservas canceladas */
SELECT
    TIPO = CASE
        WHEN UPPER(LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, '''')))) COLLATE Latin1_General_CI_AI = ''SECRET GARDEN''
         AND RS.DATAIN < CONVERT(date, ''20261001'', 112)
            THEN ''EXPLORACAO''
        ELSE COALESCE(AL1.TIPO, AL2.TIPO)
    END,
    EMPRESA  = COALESCE(AL1.EMPRESA, AL2.EMPRESA),
    CCUSTO   = RS.ALOJAMENTO,
    nmdos    = ''RESERVA'',
    obrano   = 0,
    dataobra = RS.DATAIN,
    DATA     = RS.DATAIN,
    RS.NOME,
    TOTAL    = RS.PCANCEL,
    NOITES   = 0,
    DIA      = 0,
    VALOR    = RS.PCANCEL,
    OBS      = ''CANCELADA'',
    ORIGEM   = ''AIRBNB'',
    RS.RESERVA
FROM dbo.RS AS RS
LEFT JOIN dbo.AL AS AL1 ON AL1.NOME = RS.ALOJAMENTO
LEFT JOIN dbo.AL AS AL2 ON AL2.NOMETG = RS.ALOJAMENTO
WHERE RS.CANCELADA = 1
  AND RS.PCANCEL > 0;
');

    EXEC(N'
ALTER VIEW dbo.V_ENTRADAS_TESOURARIA
AS
WITH Checkins AS (
    SELECT
        D.[DATA] AS DataCheckin,
        D.CCUSTO,
        D.TOTAL,
        TipoAlojamento = D.TIPO
    FROM dbo.V_DIARIO_ALL AS D
    WHERE D.OBS = ''Check-In''
),
Exploracao AS (
    SELECT
        TipoLinha = ''EXPLORACAO'',
        DataEntrada = CASE
            WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) BETWEEN 1 AND 4
                THEN DATEADD(DAY, 2, DataCheckin)
            WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) = 5
                THEN DATEADD(DAY, 4, DataCheckin)
            WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) = 6
                THEN DATEADD(DAY, 3, DataCheckin)
            ELSE DATEADD(DAY, 2, DataCheckin)
        END,
        Valor = SUM(CAST(TOTAL AS decimal(18,2)))
    FROM Checkins
    WHERE TipoAlojamento = ''EXPLORACAO''
    GROUP BY CASE
        WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) BETWEEN 1 AND 4
            THEN DATEADD(DAY, 2, DataCheckin)
        WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) = 5
            THEN DATEADD(DAY, 4, DataCheckin)
        WHEN (((DATEPART(WEEKDAY, DATEADD(DAY, 1, DataCheckin)) + @@DATEFIRST - 2) % 7) + 1) = 6
            THEN DATEADD(DAY, 3, DataCheckin)
        ELSE DATEADD(DAY, 2, DataCheckin)
    END
)
SELECT
    1 AS noConta,
    DataEntrada,
    TipoLinha,
    Valor
FROM Exploracao;
');

    UPDATE dbo.USQL
       SET sqlexpr = REPLACE(
           CONVERT(varchar(max), sqlexpr),
           'sum(valor) * case when al.tipo = ''GESTAO'' then 0.25 else 1 end',
           'sum(valor * case when v.tipo = ''GESTAO'' then 0.25 else 1 end)'
       )
     WHERE usqlstamp IN (
         '05C7AD5D-6A59-4378-8952-D',
         'EBC3237C-8D69-4CB4-8158-8'
     );

    /* Validacoes antes do commit: qualquer falha reverte toda a alteracao. */
    IF EXISTS (
        SELECT 1
        FROM dbo.v_diario_v2
        WHERE UPPER(LTRIM(RTRIM(ISNULL(CCUSTO, '')))) COLLATE Latin1_General_CI_AI = 'SECRET GARDEN'
          AND DATA < CONVERT(date, '20261001', 112)
          AND UPPER(LTRIM(RTRIM(ISNULL(TIPO, '')))) <> 'EXPLORACAO'
    )
        THROW 51000, 'Validacao falhou: v_diario_v2 manteve linhas historicas fora de EXPLORACAO.', 1;

    IF EXISTS (
        SELECT 1
        FROM dbo.v_diario_all
        WHERE UPPER(LTRIM(RTRIM(ISNULL(CCUSTO, '')))) COLLATE Latin1_General_CI_AI = 'SECRET GARDEN'
          AND DATA < CONVERT(date, '20261001', 112)
          AND UPPER(LTRIM(RTRIM(ISNULL(TIPO, '')))) <> 'EXPLORACAO'
    )
        THROW 51001, 'Validacao falhou: v_diario_all manteve linhas historicas fora de EXPLORACAO.', 1;

    DECLARE @atual decimal(18,2), @esperado decimal(18,2);

    SELECT @atual = ROUND(SUM(ISNULL(VALOR, 0)), 2)
    FROM dbo.v_diario_v2
    WHERE UPPER(LTRIM(RTRIM(ISNULL(CCUSTO, '')))) COLLATE Latin1_General_CI_AI = 'SECRET GARDEN'
      AND DATA < CONVERT(date, '20261001', 112);

    SELECT @esperado = ROUND(SUM(
        CASE
            WHEN ISNULL(CANCELADA, 0) = 1 THEN ROUND(ISNULL(PCANCEL, 0), 2)
            WHEN ISNULL(NOITES, 0) > 0 THEN
                ROUND(
                    (ISNULL(ESTADIA, 0) + ISNULL(LIMPEZA, 0) - ISNULL(COMISSAO, 0))
                    / NULLIF(NOITES, 0),
                    2
                ) * NOITES
            ELSE 0
        END
    ), 2)
    FROM dbo.RS
    WHERE UPPER(LTRIM(RTRIM(ISNULL(ALOJAMENTO, '')))) COLLATE Latin1_General_CI_AI = 'SECRET GARDEN'
      AND DATAIN < CONVERT(date, '20261001', 112)
      AND (ISNULL(CANCELADA, 0) = 0 OR ISNULL(PCANCEL, 0) > 0);

    IF ABS(ISNULL(@atual, 0) - ISNULL(@esperado, 0)) > 0.01
        THROW 51002, 'Validacao falhou: o total historico de v_diario_v2 nao corresponde a EXPLORACAO.', 1;

    IF EXISTS (
        SELECT 1
        FROM dbo.USQL
        WHERE usqlstamp IN ('05C7AD5D-6A59-4378-8952-D', 'EBC3237C-8D69-4CB4-8158-8')
          AND (
              LOWER(CONVERT(nvarchar(max), sqlexpr)) LIKE '%case when al.tipo = ''gestao'' then 0.25 else 1 end%'
              OR LOWER(CONVERT(nvarchar(max), sqlexpr)) LIKE '%sum(valor) * case when v.tipo = ''gestao'' then 0.25 else 1 end%'
          )
    )
        THROW 51003, 'Validacao falhou: uma analise anual continua a usar AL.TIPO.', 1;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
