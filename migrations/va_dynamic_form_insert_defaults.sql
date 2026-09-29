SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

/*
    The VA dynamic form only submits fields registered in CAMPOS.  These legacy
    columns are NOT NULL in dbo.VA, have no default, and are intentionally not
    exposed in the form.  Give them the neutral values already used by legacy
    VA records so that SQL Server can complete inserts made by the generic form.
*/

IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c
        ON c.object_id = dc.parent_object_id
       AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA')
      AND c.name = N'ANO'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_ANO DEFAULT ((0)) FOR ANO;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'MOTOR'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_MOTOR DEFAULT ('') FOR MOTOR;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'CHASSIS'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_CHASSIS DEFAULT ('') FOR CHASSIS;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'CILIND'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_CILIND DEFAULT ((0)) FOR CILIND;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'LIVRETE'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_LIVRETE DEFAULT ('') FOR LIVRETE;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'COMPANHIA'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_COMPANHIA DEFAULT ('') FOR COMPANHIA;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'SEGTIPO'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_SEGTIPO DEFAULT ('') FOR SEGTIPO;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'NOAPOL'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_NOAPOL DEFAULT ('') FOR NOAPOL;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'SEGVALINI'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_SEGVALINI DEFAULT (CONVERT(datetime, '19000101', 112)) FOR SEGVALINI;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'SEGVALFIM'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_SEGVALFIM DEFAULT (CONVERT(datetime, '19000101', 112)) FOR SEGVALFIM;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'FRANQUIA'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_FRANQUIA DEFAULT ((0)) FOR FRANQUIA;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'VARLORIUC'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_VARLORIUC DEFAULT ((0)) FOR VARLORIUC;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'ALUGADO'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_ALUGADO DEFAULT ((0)) FOR ALUGADO;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints AS dc
    INNER JOIN sys.columns AS c ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.VA') AND c.name = N'MATGENERICA'
)
    ALTER TABLE dbo.VA ADD CONSTRAINT DF_VA_MATGENERICA DEFAULT ((0)) FOR MATGENERICA;

COMMIT TRANSACTION;
