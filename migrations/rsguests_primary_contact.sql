/* Contactos opcionais do hóspede principal, reutilizados nos pedidos de transfer. */
IF COL_LENGTH('dbo.RSGUESTS', 'TELEFONE') IS NULL
BEGIN
    ALTER TABLE dbo.RSGUESTS
        ADD TELEFONE varchar(50) NOT NULL
            CONSTRAINT DF_RSGUESTS_TELEFONE DEFAULT ('') WITH VALUES;
END;

IF COL_LENGTH('dbo.RSGUESTS', 'EMAIL') IS NULL
BEGIN
    ALTER TABLE dbo.RSGUESTS
        ADD EMAIL varchar(255) NOT NULL
            CONSTRAINT DF_RSGUESTS_EMAIL DEFAULT ('') WITH VALUES;
END;
