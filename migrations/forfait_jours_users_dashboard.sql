/* GR360_CORE — Atalhos do dashboard para utilizadores já marcados como forfait-jours */
SET XACT_ABORT ON;
GO
BEGIN TRANSACTION;

/* Um widget pessoal de atalhos por utilizador. */
INSERT INTO dbo.DBW
    (DBWSTAMP, NOME, TITULO, ATIVO, COLUNA, ORDEM_COLUNA, USRCRIACAO)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    CONCAT('SHORTCUTS_', U.USSTAMP),
    'Forfait-jours',
    1, 1, 0, 'sistema'
FROM dbo.US U
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.FORFAIT, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBW W
      WHERE LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
  );

/* Associa o widget pessoal a cada utilizador. */
INSERT INTO dbo.DBWU (DBWUSTAMP, DBWSTAMP, USRSTAMP, COLUNA, ORDEM_COLUNA)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    W.DBWSTAMP, U.USSTAMP, 1, 0
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.FORFAIT, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWU UW
      WHERE UW.DBWSTAMP = W.DBWSTAMP AND UW.USRSTAMP = U.USSTAMP
  );

DECLARE @daily_menu varchar(25) = (
    SELECT TOP 1 MENUSTAMP FROM dbo.MENU
    WHERE TABELA = 'FORFAIT_JOURS' AND URL = '/forfait-jours/registo'
);
DECLARE @annual_menu varchar(25) = (
    SELECT TOP 1 MENUSTAMP FROM dbo.MENU
    WHERE TABELA = 'FORFAIT_JOURS' AND URL = '/forfait-jours/mapa-anual'
);

IF @daily_menu IS NULL OR @annual_menu IS NULL
    THROW 50002, 'Menus forfait-jours não encontrados.', 1;

/* Atalho para o registo diário. */
INSERT INTO dbo.DBWL
    (DBWLSTAMP, DBWSTAMP, ORDEM, TEXTO, URL, ABRIR_NOVA_TAB, ATIVO, COR_BORDER, ICONE, MENUSTAMP)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    W.DBWSTAMP, 10, 'Registo diário forfait-jours', '/forfait-jours/registo',
    0, 1, '#5b9dff', 'fa-calendar-day', @daily_menu
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.FORFAIT, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWL L
      WHERE L.DBWSTAMP = W.DBWSTAMP
        AND LTRIM(RTRIM(ISNULL(L.URL, ''))) = '/forfait-jours/registo'
  );

/* Atalho para o mapa anual. */
INSERT INTO dbo.DBWL
    (DBWLSTAMP, DBWSTAMP, ORDEM, TEXTO, URL, ABRIR_NOVA_TAB, ATIVO, COR_BORDER, ICONE, MENUSTAMP)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''),
    25), W.DBWSTAMP, 20, 'Mapa anual forfait-jours', '/forfait-jours/mapa-anual',
    0, 1, '#5b9dff', 'fa-calendar-days', @annual_menu
FROM dbo.US U
INNER JOIN dbo.DBW W
    ON LTRIM(RTRIM(ISNULL(W.NOME, ''))) = CONCAT('SHORTCUTS_', U.USSTAMP)
WHERE ISNULL(U.INATIVO, 0) = 0
  AND ISNULL(U.FORFAIT, 0) = 1
  AND NOT EXISTS (
      SELECT 1 FROM dbo.DBWL L
      WHERE L.DBWSTAMP = W.DBWSTAMP
        AND LTRIM(RTRIM(ISNULL(L.URL, ''))) = '/forfait-jours/mapa-anual'
  );

COMMIT TRANSACTION;
GO
