SET XACT_ABORT ON;
BEGIN TRANSACTION;

DECLARE @login varchar(60) = 'aguimaraes';
DECLARE @usstamp varchar(25);

SELECT TOP 1 @usstamp = LTRIM(RTRIM(USSTAMP))
FROM dbo.US
WHERE LOWER(LTRIM(RTRIM(LOGIN))) = @login
  AND ISNULL(INATIVO, 0) = 0;

IF ISNULL(@usstamp, '') = ''
    THROW 50001, 'Utilizador aguimaraes ativo nao encontrado.', 1;

IF EXISTS (
    SELECT 1
    FROM dbo.ACESSOS
    WHERE LOWER(LTRIM(RTRIM(UTILIZADOR))) = @login
      AND UPPER(LTRIM(RTRIM(TABELA))) = 'TK'
)
BEGIN
    UPDATE dbo.ACESSOS
       SET CONSULTAR = 1,
           INSERIR = 1,
           EDITAR = 1,
           ELIMINAR = 1,
           USSTAMP = @usstamp
     WHERE LOWER(LTRIM(RTRIM(UTILIZADOR))) = @login
       AND UPPER(LTRIM(RTRIM(TABELA))) = 'TK';
END
ELSE
BEGIN
    INSERT INTO dbo.ACESSOS
    (
        ACESSOSSTAMP, UTILIZADOR, TABELA,
        CONSULTAR, INSERIR, EDITAR, ELIMINAR, USSTAMP
    )
    VALUES
    (
        LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
        @login, 'TK', 1, 1, 1, 1, @usstamp
    );
END;

COMMIT TRANSACTION;
