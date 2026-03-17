SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

/*
    Seed default da curva de pickup mensal.

    Regras assumidas:
      - ALTA: abril a outubro, começa 90 dias antes do dia 1 do mês
      - MID: março, começa 120 dias antes do dia 1 do mês
      - BAIXA: novembro a fevereiro, começa 150 dias antes do dia 1 do mês
      - cada curva arranca em 5% no primeiro lead day e acelera de 30 em 30 dias
      - todas convergem para 80% no lead day 0

    O script é idempotente:
      - atualiza linhas existentes
      - cria linhas em falta
      - remove linhas extra apenas para as temporadas seedadas
*/

IF OBJECT_ID('dbo.PR_PICKUP_CURVE_MENSAL', 'U') IS NULL
BEGIN
    RAISERROR('A tabela dbo.PR_PICKUP_CURVE_MENSAL não existe.', 16, 1);
    RETURN;
END
GO

;WITH SourceRows AS (
    SELECT V.TEMPORADA, V.LEAD_DAYS, V.OCUP_ALVO
      FROM (VALUES
            ('ALTA',  90, CAST( 5.00 AS DECIMAL(7,2))),
            ('ALTA',  60, CAST(14.00 AS DECIMAL(7,2))),
            ('ALTA',  30, CAST(36.00 AS DECIMAL(7,2))),
            ('ALTA',   0, CAST(80.00 AS DECIMAL(7,2))),

            ('MID',  120, CAST( 5.00 AS DECIMAL(7,2))),
            ('MID',   90, CAST(11.00 AS DECIMAL(7,2))),
            ('MID',   60, CAST(24.00 AS DECIMAL(7,2))),
            ('MID',   30, CAST(46.00 AS DECIMAL(7,2))),
            ('MID',    0, CAST(80.00 AS DECIMAL(7,2))),

            ('BAIXA', 150, CAST( 5.00 AS DECIMAL(7,2))),
            ('BAIXA', 120, CAST( 9.00 AS DECIMAL(7,2))),
            ('BAIXA',  90, CAST(17.00 AS DECIMAL(7,2))),
            ('BAIXA',  60, CAST(31.00 AS DECIMAL(7,2))),
            ('BAIXA',  30, CAST(52.00 AS DECIMAL(7,2))),
            ('BAIXA',   0, CAST(80.00 AS DECIMAL(7,2)))
      ) AS V(TEMPORADA, LEAD_DAYS, OCUP_ALVO)
)
MERGE dbo.PR_PICKUP_CURVE_MENSAL AS target
USING SourceRows AS source
   ON target.TEMPORADA = source.TEMPORADA
  AND target.LEAD_DAYS = source.LEAD_DAYS
WHEN MATCHED AND ISNULL(target.OCUP_ALVO, -1) <> source.OCUP_ALVO THEN
    UPDATE SET target.OCUP_ALVO = source.OCUP_ALVO
WHEN NOT MATCHED BY TARGET THEN
    INSERT (TEMPORADA, LEAD_DAYS, OCUP_ALVO)
    VALUES (source.TEMPORADA, source.LEAD_DAYS, source.OCUP_ALVO)
WHEN NOT MATCHED BY SOURCE
     AND target.TEMPORADA IN ('ALTA', 'MID', 'BAIXA') THEN
    DELETE;
GO
