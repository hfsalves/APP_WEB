IF COL_LENGTH('dbo.AL', 'ICAL_BOOKING') IS NULL
BEGIN
    ALTER TABLE dbo.AL
    ADD ICAL_BOOKING VARCHAR(1000) NOT NULL
        CONSTRAINT DF_AL_ICAL_BOOKING DEFAULT ('');
END;

MERGE dbo.CAMPOS AS target
USING (
    SELECT
        'ICAL_BOOKING' AS NMCAMPO,
        'Calendário iCal Booking' AS DESCRICAO,
        'TEXT' AS TIPO,
        185 AS ORDEM,
        25 AS TAM,
        904 AS ORDEM_MOBILE,
        25 AS TAM_MOBILE
) AS source
   ON UPPER(LTRIM(RTRIM(ISNULL(target.TABELA, '')))) = 'AL'
  AND UPPER(LTRIM(RTRIM(ISNULL(target.NMCAMPO, '')))) = source.NMCAMPO
WHEN MATCHED THEN
    UPDATE SET
        DESCRICAO = source.DESCRICAO,
        TIPO = source.TIPO,
        ORDEM = source.ORDEM,
        TAM = source.TAM,
        ORDEM_MOBILE = source.ORDEM_MOBILE,
        TAM_MOBILE = source.TAM_MOBILE,
        VISIVEL = 1
WHEN NOT MATCHED THEN
    INSERT (
        CAMPOSSTAMP, ORDEM, NMCAMPO, DESCRICAO, TIPO, TABELA,
        LISTA, FILTRO, FILTRODEFAULT, ADMIN, RONLY, COMBO, VIRTUAL,
        TAM, ORDEM_MOBILE, TAM_MOBILE, CONDICAO_VISIVEL, OBRIGATORIO,
        VISIVEL
    )
    VALUES (
        LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
        source.ORDEM, source.NMCAMPO, source.DESCRICAO, source.TIPO, 'AL',
        0, 0, '', 0, 0, '', '',
        source.TAM, source.ORDEM_MOBILE, source.TAM_MOBILE, '', 0,
        1
    );
