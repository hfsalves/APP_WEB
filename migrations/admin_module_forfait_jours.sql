/* GR360_CORE — Associa os ecrãs forfait-jours ao módulo ADMIN */
SET XACT_ABORT ON;
GO
BEGIN TRANSACTION;

DECLARE @admin_modstamp varchar(25) = (
    SELECT TOP 1 MODSTAMP
    FROM dbo.MODULOS
    WHERE UPPER(LTRIM(RTRIM(ISNULL(NOME, '')))) = 'ADMIN'
    ORDER BY MODSTAMP
);

IF @admin_modstamp IS NULL
    THROW 50001, 'Módulo ADMIN não encontrado.', 1;

INSERT INTO dbo.MOD_OBJETOS
(
    MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA,
    MENUSTAMP, ORDEM, ATIVO, DTCRI, DTALT, USERCRIACAO, USERALTERACAO
)
SELECT
    LEFT(CONVERT(varchar(36), NEWID()), 25),
    @admin_modstamp,
    'MENU',
    CONCAT('MENU:', M.MENUSTAMP),
    M.NOME,
    M.URL,
    M.MENUSTAMP,
    M.ORDEM,
    1,
    GETDATE(),
    GETDATE(),
    'sistema',
    'sistema'
FROM dbo.MENU M
WHERE M.TABELA = 'FORFAIT_JOURS'
  AND M.URL IN ('/forfait-jours/registo', '/forfait-jours/mapa-anual')
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.MOD_OBJETOS MO
      WHERE MO.MODSTAMP = @admin_modstamp
        AND MO.OBJKEY = CONCAT('MENU:', M.MENUSTAMP)
  );

COMMIT TRANSACTION;
GO
