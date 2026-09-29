/*
    Fila global de email da GR360.

    - As aplicações apenas inserem mensagens na fila.
    - O SQL Agent processa até três mensagens a cada cinco minutos.
    - SUBMETIDO significa aceite pelo Database Mail.
    - ENVIADO só é atribuído depois de msdb confirmar sent_status = 'sent'.
*/

USE [GR360_CORE];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

IF OBJECT_ID(N'dbo.GR360_EMAIL_OUTBOX', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.GR360_EMAIL_OUTBOX
    (
        EMAIL_ID               bigint IDENTITY(1,1) NOT NULL,
        ASSUNTO                nvarchar(255) NOT NULL,
        PARA                   nvarchar(max) NOT NULL,
        CC                     nvarchar(max) NULL,
        BCC                    nvarchar(max) NULL,
        CORPO                  nvarchar(max) NOT NULL,
        FORMATO_CORPO          varchar(10) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_FORMATO DEFAULT ('HTML'),
        ANEXOS                 nvarchar(max) NULL,
        PERFIL_DBMAIL          sysname NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_PERFIL DEFAULT (N'PHC GR360'),
        ESTADO                 varchar(20) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_ESTADO DEFAULT ('PENDENTE'),
        PRIORIDADE             tinyint NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_PRIORIDADE DEFAULT ((5)),
        TENTATIVAS             smallint NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_TENTATIVAS DEFAULT ((0)),
        MAX_TENTATIVAS         smallint NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_MAX_TENTATIVAS DEFAULT ((3)),
        AGENDADO_EM            datetime2(0) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_AGENDADO DEFAULT (SYSDATETIME()),
        PROXIMA_TENTATIVA_EM   datetime2(0) NULL,
        CRIADO_EM              datetime2(0) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_CRIADO DEFAULT (SYSDATETIME()),
        CRIADO_POR             nvarchar(128) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_CRIADO_POR DEFAULT (SUSER_SNAME()),
        ATUALIZADO_EM          datetime2(0) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_ATUALIZADO DEFAULT (SYSDATETIME()),
        INICIADO_EM            datetime2(0) NULL,
        ULTIMA_TENTATIVA_EM    datetime2(0) NULL,
        SUBMETIDO_EM           datetime2(0) NULL,
        ENVIADO_EM             datetime2(0) NULL,
        MAILITEM_ID            int NULL,
        LOCK_TOKEN             uniqueidentifier NULL,
        LOCKED_AT              datetime2(0) NULL,
        ULTIMO_ERRO            nvarchar(max) NULL,
        OBSERVACOES            nvarchar(max) NULL,
        TIPO_ORIGEM            varchar(80) NULL,
        CHAVE_IDEMPOTENCIA     nvarchar(200) NULL,
        VERSAO                 rowversion NOT NULL,

        CONSTRAINT PK_GR360_EMAIL_OUTBOX PRIMARY KEY CLUSTERED (EMAIL_ID),
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_PARA
            CHECK (LEN(LTRIM(RTRIM(PARA))) > 0),
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_FORMATO
            CHECK (FORMATO_CORPO IN ('HTML', 'TEXT')),
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_ESTADO
            CHECK (ESTADO IN ('PENDENTE', 'EM_PROCESSAMENTO', 'SUBMETIDO', 'ENVIADO', 'ERRO', 'FALHADO', 'CANCELADO')),
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_TENTATIVAS
            CHECK (TENTATIVAS >= 0 AND MAX_TENTATIVAS BETWEEN 1 AND 100),
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_PERFIL
            CHECK (PERFIL_DBMAIL = N'PHC GR360')
    );
END;
GO

IF OBJECT_ID(N'dbo.GR360_EMAIL_OUTBOX_ANEXO', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.GR360_EMAIL_OUTBOX_ANEXO
    (
        EMAIL_ANEXO_ID     bigint IDENTITY(1,1) NOT NULL,
        EMAIL_ID           bigint NOT NULL,
        BASE_DADOS         sysname NULL,
        ANEXOSSTAMP        varchar(25) NULL,
        CAMINHO            nvarchar(2048) NULL,
        NOME_FICHEIRO      nvarchar(255) NULL,
        ORDEM              smallint NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_ANEXO_ORDEM DEFAULT ((1)),
        OBSERVACOES        nvarchar(500) NULL,
        CRIADO_EM          datetime2(0) NOT NULL
            CONSTRAINT DF_GR360_EMAIL_OUTBOX_ANEXO_CRIADO DEFAULT (SYSDATETIME()),

        CONSTRAINT PK_GR360_EMAIL_OUTBOX_ANEXO PRIMARY KEY CLUSTERED (EMAIL_ANEXO_ID),
        CONSTRAINT FK_GR360_EMAIL_OUTBOX_ANEXO_EMAIL
            FOREIGN KEY (EMAIL_ID)
            REFERENCES dbo.GR360_EMAIL_OUTBOX (EMAIL_ID)
            ON DELETE CASCADE,
        CONSTRAINT CK_GR360_EMAIL_OUTBOX_ANEXO_ORIGEM
            CHECK
            (
                LEN(LTRIM(RTRIM(ISNULL(CAMINHO, N'')))) > 0
                OR
                (
                    LEN(LTRIM(RTRIM(ISNULL(BASE_DADOS, N'')))) > 0
                    AND LEN(LTRIM(RTRIM(ISNULL(ANEXOSSTAMP, '')))) > 0
                )
            )
    );
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.GR360_EMAIL_OUTBOX')
      AND name = N'IX_GR360_EMAIL_OUTBOX_PROCESSAR'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_GR360_EMAIL_OUTBOX_PROCESSAR
        ON dbo.GR360_EMAIL_OUTBOX
        (
            ESTADO,
            AGENDADO_EM,
            PROXIMA_TENTATIVA_EM,
            PRIORIDADE,
            EMAIL_ID
        )
        INCLUDE (TENTATIVAS, MAX_TENTATIVAS, LOCKED_AT);
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.GR360_EMAIL_OUTBOX')
      AND name = N'UX_GR360_EMAIL_OUTBOX_IDEMPOTENCIA'
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_GR360_EMAIL_OUTBOX_IDEMPOTENCIA
        ON dbo.GR360_EMAIL_OUTBOX (CHAVE_IDEMPOTENCIA)
        WHERE CHAVE_IDEMPOTENCIA IS NOT NULL;
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.GR360_EMAIL_OUTBOX_ANEXO')
      AND name = N'IX_GR360_EMAIL_OUTBOX_ANEXO_EMAIL'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_GR360_EMAIL_OUTBOX_ANEXO_EMAIL
        ON dbo.GR360_EMAIL_OUTBOX_ANEXO (EMAIL_ID, ORDEM, EMAIL_ANEXO_ID);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_GR360_EmailOutbox_Processar
    @Limite int = 3
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @Limite IS NULL OR @Limite < 1
        SET @Limite = 3;
    IF @Limite > 100
        SET @Limite = 100;

    DECLARE @Agora datetime2(0) = SYSDATETIME();

    /* Confirma mensagens que o Database Mail já enviou. */
    UPDATE Q
       SET Q.ESTADO = 'ENVIADO',
           Q.ENVIADO_EM = COALESCE(CONVERT(datetime2(0), M.sent_date), @Agora),
           Q.ATUALIZADO_EM = @Agora,
           Q.ULTIMO_ERRO = NULL,
           Q.PROXIMA_TENTATIVA_EM = NULL
      FROM dbo.GR360_EMAIL_OUTBOX AS Q
      INNER JOIN msdb.dbo.sysmail_allitems AS M
              ON M.mailitem_id = Q.MAILITEM_ID
     WHERE Q.ESTADO = 'SUBMETIDO'
       AND M.sent_status = 'sent';

    /* Reabre falhas confirmadas pelo Database Mail ou fecha-as no limite. */
    UPDATE Q
       SET Q.ESTADO = CASE WHEN Q.TENTATIVAS >= Q.MAX_TENTATIVAS THEN 'FALHADO' ELSE 'ERRO' END,
           Q.ATUALIZADO_EM = @Agora,
           Q.ULTIMO_ERRO = COALESCE(E.description, N'O Database Mail marcou a mensagem como failed.'),
           Q.PROXIMA_TENTATIVA_EM = CASE
               WHEN Q.TENTATIVAS >= Q.MAX_TENTATIVAS THEN NULL
               ELSE DATEADD(MINUTE, 5, @Agora)
           END,
           Q.MAILITEM_ID = NULL,
           Q.SUBMETIDO_EM = NULL
      FROM dbo.GR360_EMAIL_OUTBOX AS Q
      INNER JOIN msdb.dbo.sysmail_allitems AS M
              ON M.mailitem_id = Q.MAILITEM_ID
      OUTER APPLY
      (
          SELECT TOP (1) L.description
          FROM msdb.dbo.sysmail_event_log AS L
          WHERE L.mailitem_id = M.mailitem_id
          ORDER BY L.log_date DESC
      ) AS E
     WHERE Q.ESTADO = 'SUBMETIDO'
       AND M.sent_status = 'failed';

    /* Recupera mensagens abandonadas por uma execução interrompida. */
    UPDATE dbo.GR360_EMAIL_OUTBOX
       SET ESTADO = CASE WHEN TENTATIVAS >= MAX_TENTATIVAS THEN 'FALHADO' ELSE 'ERRO' END,
           ATUALIZADO_EM = @Agora,
           PROXIMA_TENTATIVA_EM = CASE
               WHEN TENTATIVAS >= MAX_TENTATIVAS THEN NULL
               ELSE @Agora
           END,
           ULTIMO_ERRO = COALESCE(ULTIMO_ERRO + CHAR(13) + CHAR(10), N'')
                         + N'Processamento anterior abandonado há mais de 30 minutos.',
           LOCK_TOKEN = NULL,
           LOCKED_AT = NULL
     WHERE ESTADO = 'EM_PROCESSAMENTO'
       AND LOCKED_AT < DATEADD(MINUTE, -30, @Agora);

    DECLARE @Token uniqueidentifier = NEWID();
    DECLARE @Selecionados TABLE
    (
        EMAIL_ID bigint NOT NULL PRIMARY KEY
    );

    ;WITH Candidatos AS
    (
        SELECT TOP (@Limite) Q.*
        FROM dbo.GR360_EMAIL_OUTBOX AS Q WITH (UPDLOCK, READPAST, ROWLOCK)
        WHERE Q.ESTADO IN ('PENDENTE', 'ERRO')
          AND Q.TENTATIVAS < Q.MAX_TENTATIVAS
          AND Q.AGENDADO_EM <= @Agora
          AND (Q.PROXIMA_TENTATIVA_EM IS NULL OR Q.PROXIMA_TENTATIVA_EM <= @Agora)
        ORDER BY Q.PRIORIDADE ASC, Q.AGENDADO_EM ASC, Q.EMAIL_ID ASC
    )
    UPDATE Candidatos
       SET ESTADO = 'EM_PROCESSAMENTO',
           INICIADO_EM = @Agora,
           ATUALIZADO_EM = @Agora,
           LOCK_TOKEN = @Token,
           LOCKED_AT = @Agora
    OUTPUT inserted.EMAIL_ID INTO @Selecionados (EMAIL_ID);

    DECLARE
        @EmailId bigint,
        @Assunto nvarchar(255),
        @Para nvarchar(max),
        @Cc nvarchar(max),
        @Bcc nvarchar(max),
        @Corpo nvarchar(max),
        @Formato varchar(10),
        @AnexosFinais nvarchar(max),
        @MailItemId int,
        @Erro nvarchar(max);

    DECLARE EmailCursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT
            Q.EMAIL_ID,
            Q.ASSUNTO,
            Q.PARA,
            Q.CC,
            Q.BCC,
            Q.CORPO,
            Q.FORMATO_CORPO,
            NULLIF(LTRIM(RTRIM(Q.ANEXOS)), N'')
        FROM dbo.GR360_EMAIL_OUTBOX AS Q
        INNER JOIN @Selecionados AS S ON S.EMAIL_ID = Q.EMAIL_ID
        WHERE Q.LOCK_TOKEN = @Token
        ORDER BY Q.PRIORIDADE ASC, Q.AGENDADO_EM ASC, Q.EMAIL_ID ASC;

    OPEN EmailCursor;
    FETCH NEXT FROM EmailCursor
        INTO @EmailId, @Assunto, @Para, @Cc, @Bcc, @Corpo, @Formato, @AnexosFinais;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            DECLARE
                @BaseDados sysname,
                @AnexosStamp varchar(25),
                @Caminho nvarchar(2048),
                @CaminhoResolvido nvarchar(2048),
                @Sql nvarchar(max);

            DECLARE AnexoCursor CURSOR LOCAL FAST_FORWARD FOR
                SELECT
                    NULLIF(LTRIM(RTRIM(BASE_DADOS)), N''),
                    NULLIF(LTRIM(RTRIM(ANEXOSSTAMP)), ''),
                    NULLIF(LTRIM(RTRIM(CAMINHO)), N'')
                FROM dbo.GR360_EMAIL_OUTBOX_ANEXO
                WHERE EMAIL_ID = @EmailId
                ORDER BY ORDEM ASC, EMAIL_ANEXO_ID ASC;

            OPEN AnexoCursor;
            FETCH NEXT FROM AnexoCursor INTO @BaseDados, @AnexosStamp, @Caminho;

            WHILE @@FETCH_STATUS = 0
            BEGIN
                SET @CaminhoResolvido = @Caminho;

                IF @CaminhoResolvido IS NULL
                BEGIN
                    IF NOT EXISTS
                    (
                        SELECT 1
                        FROM HSOLS_MASTER.dbo.u_mercados
                        WHERE LTRIM(RTRIM(ISNULL(basedados, ''))) = @BaseDados
                    )
                        THROW 51001, N'A base de dados indicada no anexo não está autorizada.', 1;

                    IF NOT EXISTS
                    (
                        SELECT 1
                        FROM sys.databases
                        WHERE name = @BaseDados
                          AND state = 0
                          AND database_id > 4
                    )
                        THROW 51002, N'A base de dados indicada no anexo não está disponível.', 1;

                    SET @Sql = N'
                        SELECT TOP (1)
                            @Resultado = NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(2048), FULLNAME))), N'''')
                        FROM ' + QUOTENAME(@BaseDados) + N'.dbo.ANEXOS
                        WHERE LTRIM(RTRIM(CONVERT(varchar(25), ANEXOSSTAMP))) = @Stamp;';

                    EXEC sys.sp_executesql
                        @Sql,
                        N'@Stamp varchar(25), @Resultado nvarchar(2048) OUTPUT',
                        @Stamp = @AnexosStamp,
                        @Resultado = @CaminhoResolvido OUTPUT;
                END;

                IF @CaminhoResolvido IS NULL
                    THROW 51003, N'Não foi possível resolver o caminho de um anexo.', 1;

                SET @AnexosFinais = CASE
                    WHEN NULLIF(@AnexosFinais, N'') IS NULL THEN @CaminhoResolvido
                    ELSE @AnexosFinais + N';' + @CaminhoResolvido
                END;

                FETCH NEXT FROM AnexoCursor INTO @BaseDados, @AnexosStamp, @Caminho;
            END;

            CLOSE AnexoCursor;
            DEALLOCATE AnexoCursor;

            SET @MailItemId = NULL;
            SET @Cc = NULLIF(LTRIM(RTRIM(@Cc)), N'');
            SET @Bcc = NULLIF(LTRIM(RTRIM(@Bcc)), N'');
            SET @AnexosFinais = NULLIF(LTRIM(RTRIM(@AnexosFinais)), N'');

            EXEC msdb.dbo.sp_send_dbmail
                @profile_name = N'PHC GR360',
                @recipients = @Para,
                @copy_recipients = @Cc,
                @blind_copy_recipients = @Bcc,
                @subject = @Assunto,
                @body = @Corpo,
                @body_format = @Formato,
                @file_attachments = @AnexosFinais,
                @mailitem_id = @MailItemId OUTPUT;

            UPDATE dbo.GR360_EMAIL_OUTBOX
               SET ESTADO = 'SUBMETIDO',
                   TENTATIVAS = TENTATIVAS + 1,
                   ULTIMA_TENTATIVA_EM = SYSDATETIME(),
                   SUBMETIDO_EM = SYSDATETIME(),
                   MAILITEM_ID = @MailItemId,
                   ATUALIZADO_EM = SYSDATETIME(),
                   ULTIMO_ERRO = NULL,
                   PROXIMA_TENTATIVA_EM = NULL,
                   LOCK_TOKEN = NULL,
                   LOCKED_AT = NULL
             WHERE EMAIL_ID = @EmailId
               AND LOCK_TOKEN = @Token;
        END TRY
        BEGIN CATCH
            IF CURSOR_STATUS('local', 'AnexoCursor') >= 0
                CLOSE AnexoCursor;
            IF CURSOR_STATUS('local', 'AnexoCursor') > -3
                DEALLOCATE AnexoCursor;

            SET @Erro = CONCAT(
                N'Erro ', ERROR_NUMBER(), N', linha ', ERROR_LINE(), N': ', ERROR_MESSAGE()
            );

            UPDATE dbo.GR360_EMAIL_OUTBOX
               SET ESTADO = CASE
                       WHEN TENTATIVAS + 1 >= MAX_TENTATIVAS THEN 'FALHADO'
                       ELSE 'ERRO'
                   END,
                   TENTATIVAS = TENTATIVAS + 1,
                   ULTIMA_TENTATIVA_EM = SYSDATETIME(),
                   ATUALIZADO_EM = SYSDATETIME(),
                   ULTIMO_ERRO = @Erro,
                   PROXIMA_TENTATIVA_EM = CASE
                       WHEN TENTATIVAS + 1 >= MAX_TENTATIVAS THEN NULL
                       WHEN TENTATIVAS = 0 THEN DATEADD(MINUTE, 5, SYSDATETIME())
                       WHEN TENTATIVAS = 1 THEN DATEADD(MINUTE, 10, SYSDATETIME())
                       WHEN TENTATIVAS = 2 THEN DATEADD(MINUTE, 20, SYSDATETIME())
                       ELSE DATEADD(MINUTE, 60, SYSDATETIME())
                   END,
                   LOCK_TOKEN = NULL,
                   LOCKED_AT = NULL
             WHERE EMAIL_ID = @EmailId
               AND LOCK_TOKEN = @Token;
        END CATCH;

        FETCH NEXT FROM EmailCursor
            INTO @EmailId, @Assunto, @Para, @Cc, @Bcc, @Corpo, @Formato, @AnexosFinais;
    END;

    CLOSE EmailCursor;
    DEALLOCATE EmailCursor;

    SELECT
        EMAIL_ID,
        ESTADO,
        TENTATIVAS,
        MAILITEM_ID,
        SUBMETIDO_EM,
        ENVIADO_EM,
        ULTIMO_ERRO
    FROM dbo.GR360_EMAIL_OUTBOX
    WHERE EMAIL_ID IN (SELECT EMAIL_ID FROM @Selecionados)
    ORDER BY EMAIL_ID;
END;
GO

USE [msdb];
GO

IF NOT EXISTS (SELECT 1 FROM dbo.sysjobs WHERE name = N'GR360 - Processar fila de emails')
BEGIN
    EXEC dbo.sp_add_job
        @job_name = N'GR360 - Processar fila de emails',
        @enabled = 1,
        @description = N'Processa até três mensagens pendentes da GR360_EMAIL_OUTBOX.',
        @owner_login_name = N'sa';
END
ELSE
BEGIN
    EXEC dbo.sp_update_job
        @job_name = N'GR360 - Processar fila de emails',
        @enabled = 1,
        @description = N'Processa até três mensagens pendentes da GR360_EMAIL_OUTBOX.';
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM dbo.sysjobsteps AS S
    INNER JOIN dbo.sysjobs AS J ON J.job_id = S.job_id
    WHERE J.name = N'GR360 - Processar fila de emails'
      AND S.step_id = 1
)
BEGIN
    EXEC dbo.sp_add_jobstep
        @job_name = N'GR360 - Processar fila de emails',
        @step_name = N'Processar até 3 emails',
        @subsystem = N'TSQL',
        @database_name = N'GR360_CORE',
        @command = N'EXEC dbo.usp_GR360_EmailOutbox_Processar @Limite = 3;',
        @retry_attempts = 1,
        @retry_interval = 1,
        @on_success_action = 1,
        @on_fail_action = 2;
END
ELSE
BEGIN
    EXEC dbo.sp_update_jobstep
        @job_name = N'GR360 - Processar fila de emails',
        @step_id = 1,
        @step_name = N'Processar até 3 emails',
        @subsystem = N'TSQL',
        @database_name = N'GR360_CORE',
        @command = N'EXEC dbo.usp_GR360_EmailOutbox_Processar @Limite = 3;',
        @retry_attempts = 1,
        @retry_interval = 1,
        @on_success_action = 1,
        @on_fail_action = 2;
END;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.sysschedules WHERE name = N'GR360_EmailOutbox_5min')
BEGIN
    DECLARE @Hoje int = CONVERT(int, CONVERT(char(8), GETDATE(), 112));

    EXEC dbo.sp_add_schedule
        @schedule_name = N'GR360_EmailOutbox_5min',
        @enabled = 1,
        @freq_type = 4,
        @freq_interval = 1,
        @freq_subday_type = 4,
        @freq_subday_interval = 5,
        @active_start_date = @Hoje,
        @active_start_time = 0;
END
ELSE
BEGIN
    EXEC dbo.sp_update_schedule
        @name = N'GR360_EmailOutbox_5min',
        @enabled = 1,
        @freq_type = 4,
        @freq_interval = 1,
        @freq_subday_type = 4,
        @freq_subday_interval = 5,
        @active_start_time = 0;
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM dbo.sysjobs AS J
    INNER JOIN dbo.sysjobschedules AS JS ON JS.job_id = J.job_id
    INNER JOIN dbo.sysschedules AS S ON S.schedule_id = JS.schedule_id
    WHERE J.name = N'GR360 - Processar fila de emails'
      AND S.name = N'GR360_EmailOutbox_5min'
)
BEGIN
    EXEC dbo.sp_attach_schedule
        @job_name = N'GR360 - Processar fila de emails',
        @schedule_name = N'GR360_EmailOutbox_5min';
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM dbo.sysjobs AS J
    INNER JOIN dbo.sysjobservers AS JS ON JS.job_id = J.job_id
    WHERE J.name = N'GR360 - Processar fila de emails'
)
BEGIN
    EXEC dbo.sp_add_jobserver
        @job_name = N'GR360 - Processar fila de emails';
END;
GO

USE [GR360_CORE];
GO
