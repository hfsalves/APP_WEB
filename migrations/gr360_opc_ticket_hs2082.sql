IF OBJECT_ID('dbo.OPC', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.OPC', 'U_NMARCHE') IS NULL
    ALTER TABLE dbo.OPC ADD U_NMARCHE varchar(50) NOT NULL CONSTRAINT DF_OPC_U_NMARCHE DEFAULT ('');

IF OBJECT_ID('dbo.OPC', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.OPC', 'U_NMARCHE') BETWEEN 1 AND 49
    ALTER TABLE dbo.OPC ALTER COLUMN U_NMARCHE varchar(50) NOT NULL;

IF OBJECT_ID('dbo.OPC', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.OPC', 'U_CONTAFAC') IS NULL
    ALTER TABLE dbo.OPC ADD U_CONTAFAC varchar(50) NOT NULL CONSTRAINT DF_OPC_U_CONTAFAC DEFAULT ('');

IF OBJECT_ID('dbo.OPC', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.OPC', 'U_CONTAFAC') BETWEEN 1 AND 49
    ALTER TABLE dbo.OPC ALTER COLUMN U_CONTAFAC varchar(50) NOT NULL;

IF OBJECT_ID('dbo.OPC', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.OPC', 'OBS') IS NOT NULL
BEGIN
    DECLARE @opc_obs_length int;

    SELECT @opc_obs_length =
        CASE
            WHEN c.max_length = -1 THEN -1
            WHEN ty.name IN ('nvarchar', 'nchar') THEN c.max_length / 2
            ELSE c.max_length
        END
    FROM sys.columns c
    INNER JOIN sys.types ty
        ON ty.user_type_id = c.user_type_id
    WHERE c.object_id = OBJECT_ID('dbo.OPC')
      AND c.name = 'OBS';

    IF ISNULL(@opc_obs_length, 0) > 0 AND @opc_obs_length < 250
        ALTER TABLE dbo.OPC ALTER COLUMN OBS varchar(250) NOT NULL;
END;

IF OBJECT_ID('dbo.CAMPOS', 'U') IS NOT NULL
BEGIN
    UPDATE dbo.CAMPOS
       SET VISIVEL = 1
     WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'OPC'
       AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) IN ('U_NMARCHE', 'U_CONTAFAC');
END;
