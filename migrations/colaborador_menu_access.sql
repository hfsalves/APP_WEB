SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET XACT_ABORT ON
GO

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @FeriasMenuStamp varchar(25);
    DECLARE @AdminModuleStamp varchar(25) = 'KKLAJFKLAJFK';

    SELECT TOP 1 @FeriasMenuStamp = MENUSTAMP
    FROM dbo.MENU
    WHERE UPPER(LTRIM(RTRIM(ISNULL(URL, '')))) = '/FERIAS';

    IF ISNULL(@FeriasMenuStamp, '') = ''
    BEGIN
        SET @FeriasMenuStamp = LEFT(CONVERT(varchar(36), NEWID()), 25);
        INSERT INTO dbo.MENU
        (
            MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM,
            NOVO, [ORDERBY], INATIVO, LARGURAS_EXATAS, LARGURAS_EXATAS_LISTA
        )
        VALUES
        (
            @FeriasMenuStamp, 1315, 'Marcação de férias', 'FERIAS', '/ferias', 0,
            'fa-solid fa-calendar-days', '', 0, '', 0, 0, 0
        );
    END
    ELSE
    BEGIN
        UPDATE dbo.MENU
        SET ORDEM = 1315,
            NOME = 'Marcação de férias',
            TABELA = 'FERIAS',
            URL = '/ferias',
            ADMIN = 0,
            ICONE = 'fa-solid fa-calendar-days',
            INATIVO = 0
        WHERE MENUSTAMP = @FeriasMenuStamp;
    END;

    IF OBJECT_ID('dbo.MOD_OBJETOS', 'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.MODULOS WHERE MODSTAMP = @AdminModuleStamp)
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM dbo.MOD_OBJETOS
            WHERE MODSTAMP = @AdminModuleStamp
              AND OBJKEY = 'MENU:FERIAS_COLABORADOR'
        )
        BEGIN
            UPDATE dbo.MOD_OBJETOS
            SET OBJNOME = 'Marcação de férias',
                OBJROTA = '/ferias',
                MENUSTAMP = @FeriasMenuStamp,
                ORDEM = 11,
                ATIVO = 1,
                DTALT = GETDATE(),
                USERALTERACAO = 'codex'
            WHERE MODSTAMP = @AdminModuleStamp
              AND OBJKEY = 'MENU:FERIAS_COLABORADOR';
        END
        ELSE
        BEGIN
            INSERT INTO dbo.MOD_OBJETOS
            (
                MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA,
                MENUSTAMP, ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO
            )
            VALUES
            (
                LEFT(CONVERT(varchar(36), NEWID()), 25), @AdminModuleStamp,
                'MENU', 'MENU:FERIAS_COLABORADOR', 'Marcação de férias', '/ferias',
                @FeriasMenuStamp, 11, 1, GETDATE(), 'codex', 'codex'
            );
        END;
    END;

    UPDATE A
    SET CONSULTAR = 1,
        INSERIR = 1,
        EDITAR = 1,
        ELIMINAR = 1
    FROM dbo.ACESSOS A
    INNER JOIN dbo.US U
        ON UPPER(LTRIM(RTRIM(ISNULL(U.LOGIN, '')))) = UPPER(LTRIM(RTRIM(ISNULL(A.UTILIZADOR, ''))))
    WHERE ISNULL(U.INATIVO, 0) = 0
      AND UPPER(LTRIM(RTRIM(ISNULL(A.TABELA, '')))) IN ('DESPESAS', 'FERIAS');

    INSERT INTO dbo.ACESSOS
    (
        ACESSOSSTAMP, UTILIZADOR, TABELA, CONSULTAR, INSERIR, EDITAR, ELIMINAR, USSTAMP, FEID
    )
    SELECT
        LEFT(CONVERT(varchar(36), NEWID()), 25),
        U.LOGIN, T.TABELA, 1, 1, 1, 1, U.USSTAMP, 1
    FROM dbo.US U
    CROSS JOIN (VALUES ('DESPESAS'), ('FERIAS')) T(TABELA)
    WHERE ISNULL(U.INATIVO, 0) = 0
      AND LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) <> ''
      AND NOT EXISTS
      (
          SELECT 1
          FROM dbo.ACESSOS A
          WHERE UPPER(LTRIM(RTRIM(ISNULL(A.UTILIZADOR, '')))) = UPPER(LTRIM(RTRIM(U.LOGIN)))
            AND UPPER(LTRIM(RTRIM(ISNULL(A.TABELA, '')))) = T.TABELA
      );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH
GO
