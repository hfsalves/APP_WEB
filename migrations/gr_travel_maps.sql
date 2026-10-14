/* Explicit deployment only. Never run from a web request or against PHC. */
SET XACT_ABORT ON;
IF DB_NAME() <> 'GR360_CORE'
    THROW 51000, 'Esta migracao destina-se apenas a GR360_CORE.', 1;
BEGIN TRANSACTION;
IF OBJECT_ID('dbo.GR_TRAVEL_MAP', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.GR_TRAVEL_MAP (
        id varchar(36) NOT NULL PRIMARY KEY,
        scope_hash varchar(64) NOT NULL UNIQUE,
        feid int NOT NULL, phc_db varchar(128) NOT NULL,
        employee_key varchar(250) NOT NULL,
        [year] int NOT NULL, [month] int NOT NULL,
        version int NOT NULL,
        CONSTRAINT CK_GR_TRAVEL_PERIOD CHECK ([year] BETWEEN 2000 AND 2100 AND [month] BETWEEN 1 AND 12),
        CONSTRAINT CK_GR_TRAVEL_VERSION CHECK (version >= 0)
    );
    CREATE INDEX IX_GR_TRAVEL_MONTH ON dbo.GR_TRAVEL_MAP(feid, [year], [month]);
END;
IF OBJECT_ID('dbo.GR_TRAVEL_MAP_VERSION', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.GR_TRAVEL_MAP_VERSION (
        map_id varchar(36) NOT NULL REFERENCES dbo.GR_TRAVEL_MAP(id),
        version int NOT NULL,
        request_id varchar(36) NOT NULL UNIQUE,
        request_hash varchar(64) NOT NULL,
        action varchar(16) NOT NULL,
        state varchar(16) NOT NULL,
        actor varchar(100) NOT NULL, user_stamp varchar(25) NOT NULL,
        created_at datetime2(6) NOT NULL,
        reason nvarchar(max) NOT NULL,
        document nvarchar(max) NOT NULL,
        previous_hash varchar(64) NOT NULL,
        content_hash varchar(64) NOT NULL,
        CONSTRAINT PK_GR_TRAVEL_MAP_VERSION PRIMARY KEY(map_id, version),
        CONSTRAINT CK_GR_TRAVEL_ACTION CHECK (action IN ('GENERATE','EDIT','VALIDATE','REJECT')),
        CONSTRAINT CK_GR_TRAVEL_STATE CHECK (state IN ('POR_VALIDAR','VALIDADO','REJEITADO')),
        CONSTRAINT CK_GR_TRAVEL_DOCUMENT CHECK (ISJSON(document) = 1)
    );
END;
EXEC(N'CREATE OR ALTER TRIGGER dbo.TR_GR_TRAVEL_VERSION_IMMUTABLE
ON dbo.GR_TRAVEL_MAP_VERSION INSTEAD OF UPDATE, DELETE AS
BEGIN
    THROW 51001, ''As versoes de mapas sao imutaveis. Crie uma nova versao.'', 1;
END;');
COMMIT TRANSACTION;
