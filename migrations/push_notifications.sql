SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.PUSH_DEVICE', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.PUSH_DEVICE
        (
            PUSHDEVSTAMP     VARCHAR(25) NOT NULL,
            USERSTAMP        VARCHAR(25) NOT NULL,
            ENDPOINT         NVARCHAR(MAX) NOT NULL,
            ENDPOINT_HASH    VARCHAR(64) NOT NULL,
            P256DH           NVARCHAR(MAX) NOT NULL,
            AUTH             NVARCHAR(MAX) NOT NULL,
            PLATFORM         VARCHAR(30) NULL,
            USERAGENT        NVARCHAR(500) NULL,
            DEVICE_LABEL     NVARCHAR(100) NULL,
            IS_ACTIVE        BIT NOT NULL CONSTRAINT DF_PUSH_DEVICE_IS_ACTIVE DEFAULT (1),
            LAST_SEEN        DATETIME NULL,
            CREATED_AT       DATETIME NOT NULL CONSTRAINT DF_PUSH_DEVICE_CREATED_AT DEFAULT (GETDATE()),
            UPDATED_AT       DATETIME NULL,
            LAST_PUSH_AT     DATETIME NULL,
            LAST_ERROR_AT    DATETIME NULL,
            LAST_ERROR_MSG   NVARCHAR(1000) NULL,
            CONSTRAINT PK_PUSH_DEVICE PRIMARY KEY CLUSTERED (PUSHDEVSTAMP)
        );
    END;

    IF OBJECT_ID('dbo.PUSH_LOG', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.PUSH_LOG
        (
            PUSHLOGSTAMP       VARCHAR(25) NOT NULL,
            USERSTAMP          VARCHAR(25) NULL,
            PUSHDEVSTAMP       VARCHAR(25) NULL,
            SENT_BY_USERSTAMP  VARCHAR(25) NULL,
            EVENT_TYPE         VARCHAR(50) NULL,
            TITLE              NVARCHAR(200) NOT NULL,
            BODY               NVARCHAR(1000) NOT NULL,
            TARGET_URL         NVARCHAR(500) NULL,
            PAYLOAD            NVARCHAR(MAX) NULL,
            STATUS             VARCHAR(20) NOT NULL,
            RESPONSE_INFO      NVARCHAR(2000) NULL,
            CREATED_AT         DATETIME NOT NULL CONSTRAINT DF_PUSH_LOG_CREATED_AT DEFAULT (GETDATE()),
            SENT_AT            DATETIME NULL,
            CONSTRAINT PK_PUSH_LOG PRIMARY KEY CLUSTERED (PUSHLOGSTAMP)
        );
    END;

    IF OBJECT_ID('dbo.NOTIF_PREF', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.NOTIF_PREF
        (
            NOTIFPREFSTAMP  VARCHAR(25) NOT NULL,
            USERSTAMP       VARCHAR(25) NOT NULL,
            EVENT_TYPE      VARCHAR(50) NOT NULL,
            PUSH_ENABLED    BIT NOT NULL CONSTRAINT DF_NOTIF_PREF_PUSH_ENABLED DEFAULT (1),
            CREATED_AT      DATETIME NOT NULL CONSTRAINT DF_NOTIF_PREF_CREATED_AT DEFAULT (GETDATE()),
            UPDATED_AT      DATETIME NULL,
            CONSTRAINT PK_NOTIF_PREF PRIMARY KEY CLUSTERED (NOTIFPREFSTAMP)
        );
    END;

    IF OBJECT_ID('dbo.PUSH_DEVICE', 'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_PUSH_DEVICE_US'
        )
       AND OBJECT_ID('dbo.US', 'U') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.PUSH_DEVICE
        ADD CONSTRAINT FK_PUSH_DEVICE_US
            FOREIGN KEY (USERSTAMP) REFERENCES dbo.US (USSTAMP);
    END;

    IF OBJECT_ID('dbo.NOTIF_PREF', 'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_NOTIF_PREF_US'
        )
       AND OBJECT_ID('dbo.US', 'U') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.NOTIF_PREF
        ADD CONSTRAINT FK_NOTIF_PREF_US
            FOREIGN KEY (USERSTAMP) REFERENCES dbo.US (USSTAMP);
    END;

    IF OBJECT_ID('dbo.PUSH_LOG', 'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_PUSH_LOG_USER'
        )
       AND OBJECT_ID('dbo.US', 'U') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.PUSH_LOG
        ADD CONSTRAINT FK_PUSH_LOG_USER
            FOREIGN KEY (USERSTAMP) REFERENCES dbo.US (USSTAMP);
    END;

    IF OBJECT_ID('dbo.PUSH_LOG', 'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_PUSH_LOG_SENT_BY_USER'
        )
       AND OBJECT_ID('dbo.US', 'U') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.PUSH_LOG
        ADD CONSTRAINT FK_PUSH_LOG_SENT_BY_USER
            FOREIGN KEY (SENT_BY_USERSTAMP) REFERENCES dbo.US (USSTAMP);
    END;

    IF OBJECT_ID('dbo.PUSH_LOG', 'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_PUSH_LOG_DEVICE'
        )
       AND OBJECT_ID('dbo.PUSH_DEVICE', 'U') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.PUSH_LOG
        ADD CONSTRAINT FK_PUSH_LOG_DEVICE
            FOREIGN KEY (PUSHDEVSTAMP) REFERENCES dbo.PUSH_DEVICE (PUSHDEVSTAMP);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.PUSH_DEVICE') AND name = 'IX_PUSH_DEVICE_USERSTAMP'
    )
    BEGIN
        CREATE INDEX IX_PUSH_DEVICE_USERSTAMP
            ON dbo.PUSH_DEVICE (USERSTAMP, IS_ACTIVE, LAST_SEEN DESC);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.PUSH_DEVICE') AND name = 'IX_PUSH_DEVICE_IS_ACTIVE'
    )
    BEGIN
        CREATE INDEX IX_PUSH_DEVICE_IS_ACTIVE
            ON dbo.PUSH_DEVICE (IS_ACTIVE, LAST_SEEN DESC);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.PUSH_DEVICE') AND name = 'UX_PUSH_DEVICE_ENDPOINT_HASH'
    )
    BEGIN
        CREATE UNIQUE INDEX UX_PUSH_DEVICE_ENDPOINT_HASH
            ON dbo.PUSH_DEVICE (ENDPOINT_HASH);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.PUSH_LOG') AND name = 'IX_PUSH_LOG_USERSTAMP'
    )
    BEGIN
        CREATE INDEX IX_PUSH_LOG_USERSTAMP
            ON dbo.PUSH_LOG (USERSTAMP, CREATED_AT DESC);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.PUSH_LOG') AND name = 'IX_PUSH_LOG_EVENT_STATUS'
    )
    BEGIN
        CREATE INDEX IX_PUSH_LOG_EVENT_STATUS
            ON dbo.PUSH_LOG (EVENT_TYPE, STATUS, CREATED_AT DESC);
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.NOTIF_PREF') AND name = 'UX_NOTIF_PREF_USER_EVENT'
    )
    BEGIN
        CREATE UNIQUE INDEX UX_NOTIF_PREF_USER_EVENT
            ON dbo.NOTIF_PREF (USERSTAMP, EVENT_TYPE);
    END;

    IF OBJECT_ID('dbo.PARAG', 'U') IS NOT NULL
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM dbo.PARAG WHERE UPPER(LTRIM(RTRIM(GRUPO))) = 'PUSH'
        )
        BEGIN
            INSERT INTO dbo.PARAG (GRUPO) VALUES ('PUSH');
        END;
    END;

    IF OBJECT_ID('dbo.PARA', 'U') IS NOT NULL
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM dbo.PARA WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = 'VAPID_PUBLIC_KEY'
        )
        BEGIN
            INSERT INTO dbo.PARA
            (
                PARASTAMP, PARAMETRO, DESCRICAO, TIPO,
                CVALOR, DVALOR, NVALOR, LVALOR, GRUPO
            )
            VALUES
            (
                UPPER(CONVERT(VARCHAR(25), REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''))),
                'VAPID_PUBLIC_KEY',
                'Chave publica VAPID para notificacoes push web',
                'C',
                '',
                CAST(GETDATE() AS DATE),
                0,
                0,
                'PUSH'
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM dbo.PARA WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = 'VAPID_PRIVATE_KEY'
        )
        BEGIN
            INSERT INTO dbo.PARA
            (
                PARASTAMP, PARAMETRO, DESCRICAO, TIPO,
                CVALOR, DVALOR, NVALOR, LVALOR, GRUPO
            )
            VALUES
            (
                UPPER(CONVERT(VARCHAR(25), REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''))),
                'VAPID_PRIVATE_KEY',
                'Chave privada VAPID para notificacoes push web',
                'C',
                '',
                CAST(GETDATE() AS DATE),
                0,
                0,
                'PUSH'
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM dbo.PARA WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = 'VAPID_PRIVATE_KEY_B64'
        )
        BEGIN
            INSERT INTO dbo.PARA
            (
                PARASTAMP, PARAMETRO, DESCRICAO, TIPO,
                CVALOR, DVALOR, NVALOR, LVALOR, GRUPO
            )
            VALUES
            (
                UPPER(CONVERT(VARCHAR(25), REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''))),
                'VAPID_PRIVATE_KEY_B64',
                'Chave privada VAPID em base64 compacto para notificacoes push web',
                'C',
                '',
                CAST(GETDATE() AS DATE),
                0,
                0,
                'PUSH'
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM dbo.PARA WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = 'VAPID_SUBJECT'
        )
        BEGIN
            INSERT INTO dbo.PARA
            (
                PARASTAMP, PARAMETRO, DESCRICAO, TIPO,
                CVALOR, DVALOR, NVALOR, LVALOR, GRUPO
            )
            VALUES
            (
                UPPER(CONVERT(VARCHAR(25), REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', ''))),
                'VAPID_SUBJECT',
                'Subject VAPID no formato mailto: ou https://',
                'C',
                '',
                CAST(GETDATE() AS DATE),
                0,
                0,
                'PUSH'
            );
        END;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
