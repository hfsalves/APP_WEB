/* Permissão pontual para a Susana gerir apenas o planeamento externo da OPC. */
DECLARE @login varchar(60) = 'srferreira';
DECLARE @usstamp varchar(100);

SELECT TOP 1 @usstamp = USSTAMP
FROM dbo.US
WHERE LOWER(LTRIM(RTRIM(LOGIN))) = @login;

IF @usstamp IS NULL
    THROW 50000, 'Utilizadora srferreira não encontrada em dbo.US.', 1;

IF EXISTS (
    SELECT 1
    FROM dbo.ACESSOS
    WHERE UTILIZADOR = @login
      AND TABELA = 'OPC_PLANEXT_VIEW'
)
BEGIN
    UPDATE dbo.ACESSOS
       SET CONSULTAR = 1,
           EDITAR = 1
     WHERE UTILIZADOR = @login
       AND TABELA = 'OPC_PLANEXT_VIEW';
END
ELSE
BEGIN
    INSERT INTO dbo.ACESSOS
        (ACESSOSSTAMP, UTILIZADOR, TABELA, CONSULTAR, INSERIR, EDITAR, ELIMINAR, USSTAMP)
    VALUES
        (CONVERT(varchar(25), NEWID()), @login, 'OPC_PLANEXT_VIEW', 1, 0, 1, 0, @usstamp);
END
