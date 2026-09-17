-- Diagnóstico apenas de leitura. Não executa procedures nem altera dados.
-- Documento da imagem: fatura 387, 15/05/2026, FOSTAMP abaixo.
-- Executar no servidor comum, contexto GESTAO.

SELECT 'GESTAO' AS origem, FOSTAMP, ADOC, ETTILIQ, EIVAIN, ETTIVA, EIVAV2, ETOTAL
FROM GESTAO.dbo.FO
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E';

SELECT 'PHC' AS origem, FOSTAMP, ADOC, ETTILIQ, EIVAIN, ETTIVA, EIVAV2, ETOTAL, PLANO, DOSTAMP
FROM Guest_SPA_Tur.dbo.FO
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E';

SELECT FNSTAMP, REF, DESIGN, QTT, EPV, ETILIQUIDO, TAXAIVA, TABIVA, IVAINCL, LORDEM
FROM GESTAO.dbo.FN
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E'
ORDER BY LORDEM, FNSTAMP;

SELECT TABIVA, TAXAIVA, COUNT(*) AS linhas,
       ROUND(SUM(CASE WHEN IVAINCL = 1 THEN ETILIQUIDO / (1 + TAXAIVA / 100)
                      ELSE ETILIQUIDO END), 2) AS base_app,
       ROUND(SUM(CASE WHEN IVAINCL = 1 THEN ETILIQUIDO - ETILIQUIDO / (1 + TAXAIVA / 100)
                      ELSE ETILIQUIDO * TAXAIVA / 100 END), 2) AS iva_app
FROM GESTAO.dbo.FN
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E'
GROUP BY TABIVA, TAXAIVA;

SELECT TABIVA, IVA, COUNT(*) AS linhas,
       ROUND(SUM(CASE WHEN IVAINCL = 1 THEN ETILIQUIDO / (1 + IVA / 100)
                      ELSE ETILIQUIDO END), 2) AS base_phc,
       ROUND(SUM(CASE WHEN IVAINCL = 1 THEN ETILIQUIDO - ETILIQUIDO / (1 + IVA / 100)
                      ELSE ETILIQUIDO * IVA / 100 END), 2) AS iva_phc
FROM Guest_SPA_Tur.dbo.FN
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E'
GROUP BY TABIVA, IVA;

SELECT FOTSTAMP, FOSTAMP, CODIGO, TAXA, EBASEINC, EVALOR
FROM Guest_SPA_Tur.dbo.FOT
WHERE FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E';

SELECT M.DOSTAMP, M.CONTA, M.DESCRICAO, M.EDEB, M.ECRE, M.ORISTAMP, M.DILNO
FROM Guest_SPA_Tur.dbo.ML AS M
JOIN Guest_SPA_Tur.dbo.FO AS F ON F.DOSTAMP = M.DOSTAMP
WHERE F.FOSTAMP = '4CE5EDE6-6D02-4741-8C03-E';

-- Triagem: documentos comuns às duas bases, DATA da app desde 2026-01-01.
-- Tolerância > 0,02 EUR. Divergência não prova por si só a mesma causa.
-- PLANO indica integração contabilística; não verifica todos os respetivos ML.
WITH L AS (
    SELECT FOSTAMP, COUNT(*) AS n,
           SUM(CASE WHEN IVAINCL = 1 THEN ETILIQUIDO / (1 + TAXAIVA / 100)
                    ELSE ETILIQUIDO END) AS base,
           SUM(CASE WHEN LTRIM(RTRIM(ISNULL(REF, ''))) = ''
                         AND LTRIM(RTRIM(ISNULL(DESIGN, ''))) = '' THEN 1 ELSE 0 END) AS blank_count,
           SUM(CASE WHEN LTRIM(RTRIM(ISNULL(REF, ''))) = ''
                         AND LTRIM(RTRIM(ISNULL(DESIGN, ''))) = '' THEN ETILIQUIDO ELSE 0 END) AS blank_amount
    FROM GESTAO.dbo.FN
    GROUP BY FOSTAMP
), T AS (
    SELECT FOSTAMP, COUNT(*) AS n, SUM(EBASEINC) AS base, SUM(EVALOR) AS iva
    FROM Guest_SPA_Tur.dbo.FOT
    GROUP BY FOSTAMP
)
SELECT G.FOSTAMP, G.ADOC, G.NOME, G.DATA, G.SYNC,
       G.ETTILIQ AS base_cab_app, G.ETTIVA AS iva_cab_app,
       L.n AS linhas_app, L.base AS base_linhas_app,
       L.blank_count AS linhas_sem_ref_design, L.blank_amount AS valor_sem_ref_design,
       P.EIVAIN AS base_cab_phc, P.ETTIVA AS iva_cab_phc,
       T.n AS registos_fot, T.base AS base_fot, T.iva AS iva_fot,
       P.PLANO, P.DOSTAMP,
       CASE WHEN ABS(T.base - 2 * P.EIVAIN) < 0.02 AND ABS(P.EIVAIN) > 0.02
            THEN 1 ELSE 0 END AS base_duplicada,
       CASE WHEN L.blank_count > 0 AND L.n > L.blank_count
                 AND ABS(L.blank_amount - G.ETTILIQ) < 0.02
                 AND ABS(L.base - 2 * G.ETTILIQ) < 0.02 AND ABS(G.ETTILIQ) > 0.02
            THEN 1 ELSE 0 END AS padrao_resumo_mais_detalhe
FROM GESTAO.dbo.FO AS G
JOIN Guest_SPA_Tur.dbo.FO AS P
  ON P.FOSTAMP COLLATE SQL_Latin1_General_CP1_CI_AI = G.FOSTAMP
LEFT JOIN L ON L.FOSTAMP = G.FOSTAMP
LEFT JOIN T ON T.FOSTAMP = P.FOSTAMP
WHERE G.DATA >= '20260101'
  AND (ABS(T.base - P.EIVAIN) > 0.02 OR ABS(T.iva - P.ETTIVA) > 0.02)
ORDER BY G.DATA, G.FOSTAMP;

