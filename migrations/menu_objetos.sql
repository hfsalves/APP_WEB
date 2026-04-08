SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET XACT_ABORT ON
GO

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.MENU_OBJETOS', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.MENU_OBJETOS
        (
            MENUOBJSTAMP      varchar(25)   NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_STAMP DEFAULT LEFT(CONVERT(varchar(36), NEWID()), 25),
            MENUSTAMP         varchar(25)   NOT NULL,
            NMCAMPO           varchar(50)   NOT NULL,
            DESCRICAO         varchar(100)  NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_DESCRICAO DEFAULT '',
            TIPO              varchar(20)   NOT NULL,
            ORDEM             int           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_ORDEM DEFAULT 0,
            TAM               int           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_TAM DEFAULT 5,
            ORDEM_MOBILE      int           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_ORDEM_MOBILE DEFAULT 0,
            TAM_MOBILE        int           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_TAM_MOBILE DEFAULT 5,
            VISIVEL           bit           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_VISIVEL DEFAULT 1,
            RONLY             bit           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_RONLY DEFAULT 0,
            OBRIGATORIO       bit           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_OBRIGATORIO DEFAULT 0,
            CONDICAO_VISIVEL  varchar(200)  NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_CONDICAO_VISIVEL DEFAULT '',
            COMBO             nvarchar(max) NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_COMBO DEFAULT N'',
            DECIMAIS          int           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_DECIMAIS DEFAULT 0,
            MINIMO            decimal(18,6) NULL,
            MAXIMO            decimal(18,6) NULL,
            PROPRIEDADES      nvarchar(max) NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_PROPRIEDADES DEFAULT N'{}',
            ATIVO             bit           NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_ATIVO DEFAULT 1,
            DTCRI             datetime2(0)  NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_DTCRI DEFAULT GETDATE(),
            DTALT             datetime2(0)  NULL,
            USERCRIACAO       varchar(50)   NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_USERCRIACAO DEFAULT '',
            USERALTERACAO     varchar(50)   NOT NULL
                CONSTRAINT DF_MENU_OBJETOS_USERALTERACAO DEFAULT '',

            CONSTRAINT PK_MENU_OBJETOS PRIMARY KEY CLUSTERED (MENUOBJSTAMP),
            CONSTRAINT FK_MENU_OBJETOS_MENU FOREIGN KEY (MENUSTAMP) REFERENCES dbo.MENU(MENUSTAMP),
            CONSTRAINT UQ_MENU_OBJETOS_MENU_NMCAMPO UNIQUE (MENUSTAMP, NMCAMPO)
        );

        CREATE INDEX IX_MENU_OBJETOS_MENU_ORDEM
            ON dbo.MENU_OBJETOS (MENUSTAMP, ORDEM, NMCAMPO);

        CREATE INDEX IX_MENU_OBJETOS_MENU_ORDEM_MOBILE
            ON dbo.MENU_OBJETOS (MENUSTAMP, ORDEM_MOBILE, NMCAMPO);
    END

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH
GO
