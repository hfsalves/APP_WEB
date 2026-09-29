SET NOCOUNT ON;

IF OBJECT_ID('dbo.LP', 'U') IS NULL
    THROW 50000, 'A tabela dbo.LP não existe.', 1;

IF COL_LENGTH('dbo.LP', 'NOITES') IS NULL
    THROW 50000, 'A coluna dbo.LP.NOITES não existe.', 1;

IF EXISTS (
    SELECT 1
    FROM sys.columns AS C
    WHERE C.object_id = OBJECT_ID('dbo.LP')
      AND C.name = 'NOITES'
      AND (
          TYPE_NAME(C.user_type_id) <> 'numeric'
          OR C.precision <> 12
          OR C.scale <> 0
      )
)
BEGIN
    ALTER TABLE dbo.LP
        ALTER COLUMN NOITES numeric(12, 0) NOT NULL;
END;
