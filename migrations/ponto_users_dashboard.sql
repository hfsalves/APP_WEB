/* GR360_CORE — Atalhos do dashboard para utilizadores marcados para registo de ponto */
SET XACT_ABORT ON;
GO
BEGIN TRANSACTION;

/* Um widget pessoal de atalhos por utilizador, partilhado com outros atalhos quando já existe. */
INSERT INTO dbo.DBW
    (DBWSTAMP, NOME, TITULO, ATIVO, COLUNA, ORDEM_COLUNA, USRCRIACAO)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    CONCAT('SHORTCUTS_', U.USSTAMP),
    'Pointage',
    1, 1, 0, 'sistema'
FROM dbo.US U
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.PONTO, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBW W
      WHERE LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
  );

INSERT INTO dbo.DBWU (DBWUSTAMP, DBWSTAMP, USRSTAMP, COLUNA, ORDEM_COLUNA)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    W.DBWSTAMP, U.USSTAMP, 1, 0
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.PONTO, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWU UW
      WHERE UW.DBWSTAMP = W.DBWSTAMP AND UW.USRSTAMP = U.USSTAMP
  );

DECLARE @daily_menu varchar(25) = (
    SELECT TOP 1 MENUSTAMP FROM dbo.MENU
    WHERE TABELA = 'PONTO' AND URL = '/ponto/registo'
);
DECLARE @monthly_menu varchar(25) = (
    SELECT TOP 1 MENUSTAMP FROM dbo.MENU
    WHERE TABELA = 'PONTO' AND URL = '/ponto/resumo-mensal'
);

IF @daily_menu IS NULL OR @monthly_menu IS NULL
    THROW 50004, 'Menus do registo de ponto não encontrados.', 1;

INSERT INTO dbo.DBWL
    (DBWLSTAMP, DBWSTAMP, ORDEM, TEXTO, URL, ABRIR_NOVA_TAB, ATIVO, COR_BORDER, ICONE, MENUSTAMP)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    W.DBWSTAMP, 30, 'Pointage journalier', '/ponto/registo',
    0, 1, '#5b9dff', 'fa-clock', @daily_menu
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.PONTO, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWL L
      WHERE L.DBWSTAMP = W.DBWSTAMP
        AND LTRIM(RTRIM(ISNULL(L.URL, ''))) = '/ponto/registo'
  );

INSERT INTO dbo.DBWL
    (DBWLSTAMP, DBWSTAMP, ORDEM, TEXTO, URL, ABRIR_NOVA_TAB, ATIVO, COR_BORDER, ICONE, MENUSTAMP)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    W.DBWSTAMP, 40, 'Résumé mensuel du pointage', '/ponto/resumo-mensal',
    0, 1, '#5b9dff', 'fa-calendar-check', @monthly_menu
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.PONTO, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWL L
      WHERE L.DBWSTAMP = W.DBWSTAMP
        AND LTRIM(RTRIM(ISNULL(L.URL, ''))) = '/ponto/resumo-mensal'
  );

/* Corrige também atalhos já existentes que tenham herdado o nome português do MENU. */
UPDATE L
   SET TEXTO = CASE LTRIM(RTRIM(ISNULL(L.URL, '')))
       WHEN '/ponto/registo' THEN 'Pointage journalier'
       WHEN '/ponto/resumo-mensal' THEN 'Résumé mensuel du pointage'
   END
FROM dbo.DBWL L
INNER JOIN dbo.DBW W ON W.DBWSTAMP = L.DBWSTAMP
INNER JOIN dbo.DBWU UW ON UW.DBWSTAMP = W.DBWSTAMP
INNER JOIN dbo.US U ON U.USSTAMP = UW.USRSTAMP
WHERE ISNULL(U.PONTO, 0) = 1
  AND LTRIM(RTRIM(ISNULL(L.URL, ''))) IN ('/ponto/registo', '/ponto/resumo-mensal');

COMMIT TRANSACTION;
GO
