/* GR360_CORE — Menus do módulo forfait-jours, em Colaboradores */
SET XACT_ABORT ON;
GO
BEGIN TRANSACTION;

IF NOT EXISTS (
    SELECT 1 FROM dbo.MENU
    WHERE TABELA = 'FORFAIT_JOURS' AND URL = '/forfait-jours/registo'
)
BEGIN
    INSERT INTO dbo.MENU (ORDEM, NOME, TABELA, URL, FORM, ICONE, ADMIN, NOVO, INATIVO)
    VALUES (1350, 'Registo diário forfait-jours', 'FORFAIT_JOURS', '/forfait-jours/registo', '', 'fa-solid fa-calendar-day', 0, 0, 0);
END;

IF NOT EXISTS (
    SELECT 1 FROM dbo.MENU
    WHERE TABELA = 'FORFAIT_JOURS' AND URL = '/forfait-jours/mapa-anual'
)
BEGIN
    INSERT INTO dbo.MENU (ORDEM, NOME, TABELA, URL, FORM, ICONE, ADMIN, NOVO, INATIVO)
    VALUES (1351, 'Mapa anual forfait-jours', 'FORFAIT_JOURS', '/forfait-jours/mapa-anual', '', 'fa-solid fa-calendar-days', 0, 0, 0);
END;

COMMIT TRANSACTION;
GO
