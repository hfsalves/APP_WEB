SET XACT_ABORT ON;

BEGIN TRANSACTION;

IF COL_LENGTH('dbo.VA', 'CILINDRADA') IS NULL
    ALTER TABLE dbo.VA ADD CILINDRADA int NULL;

IF COL_LENGTH('dbo.VA', 'COMBUSTIVEL') IS NULL
    ALTER TABLE dbo.VA ADD COMBUSTIVEL varchar(30) NULL;

IF COL_LENGTH('dbo.VA', 'DTMATRICULA') IS NULL
    ALTER TABLE dbo.VA ADD DTMATRICULA date NULL;

IF COL_LENGTH('dbo.VA', 'VERSAO') IS NULL
    ALTER TABLE dbo.VA ADD VERSAO varchar(60) NULL;

IF COL_LENGTH('dbo.VA', 'POTENCIAKW') IS NULL
    ALTER TABLE dbo.VA ADD POTENCIAKW decimal(10,2) NULL;

IF COL_LENGTH('dbo.VA', 'PESOBRUTO') IS NULL
    ALTER TABLE dbo.VA ADD PESOBRUTO decimal(12,2) NULL;

IF COL_LENGTH('dbo.VA', 'TARA') IS NULL
    ALTER TABLE dbo.VA ADD TARA decimal(12,2) NULL;

IF COL_LENGTH('dbo.VA', 'NRLUGARES') IS NULL
    ALTER TABLE dbo.VA ADD NRLUGARES int NULL;

IF COL_LENGTH('dbo.VA', 'CATEGORIA') IS NULL
    ALTER TABLE dbo.VA ADD CATEGORIA varchar(30) NULL;

IF COL_LENGTH('dbo.VA', 'CARROCARIA') IS NULL
    ALTER TABLE dbo.VA ADD CARROCARIA varchar(60) NULL;

IF COL_LENGTH('dbo.VA', 'COR') IS NULL
    ALTER TABLE dbo.VA ADD COR varchar(40) NULL;

IF COL_LENGTH('dbo.VA', 'CO2_GKM') IS NULL
    ALTER TABLE dbo.VA ADD CO2_GKM decimal(10,3) NULL;

IF COL_LENGTH('dbo.VA', 'NORMAEURO') IS NULL
    ALTER TABLE dbo.VA ADD NORMAEURO varchar(30) NULL;

IF COL_LENGTH('dbo.VA', 'MATRICULAANTERIOR') IS NULL
    ALTER TABLE dbo.VA ADD MATRICULAANTERIOR varchar(20) NULL;

IF COL_LENGTH('dbo.VA', 'PAISPROCEDENCIA') IS NULL
    ALTER TABLE dbo.VA ADD PAISPROCEDENCIA varchar(60) NULL;

IF COL_LENGTH('dbo.VA', 'DTAQUISICAO') IS NULL
    ALTER TABLE dbo.VA ADD DTAQUISICAO date NULL;

IF COL_LENGTH('dbo.VA', 'VALORAQUISICAO') IS NULL
    ALTER TABLE dbo.VA ADD VALORAQUISICAO decimal(18,2) NULL;

DECLARE @CamposVA TABLE
(
    NMCAMPO varchar(25) NOT NULL,
    DESCRICAO varchar(60) NOT NULL,
    TIPO varchar(20) NOT NULL,
    ORDEM int NOT NULL,
    TAM int NOT NULL,
    DECIMAIS int NOT NULL
);

INSERT INTO @CamposVA (NMCAMPO, DESCRICAO, TIPO, ORDEM, TAM, DECIMAIS)
VALUES
    ('CILINDRADA',        'Cilindrada',            'INT',     71, 10, 0),
    ('COMBUSTIVEL',       'Combustível',           'TEXT',    72, 15, 0),
    ('DTMATRICULA',       'Data primeira matrícula','DATE',   73, 10, 0),
    ('VERSAO',            'Versão',                'TEXT',    74, 20, 0),
    ('POTENCIAKW',        'Potência (kW)',         'DECIMAL', 75, 10, 2),
    ('PESOBRUTO',         'Peso bruto (kg)',       'DECIMAL', 76, 10, 2),
    ('TARA',              'Tara (kg)',             'DECIMAL', 77, 10, 2),
    ('NRLUGARES',         'N.º lugares',           'INT',     78, 10, 0),
    ('CATEGORIA',         'Categoria',             'TEXT',    79, 15, 0),
    ('CARROCARIA',        'Carroçaria',            'TEXT',    81, 15, 0),
    ('COR',               'Cor',                   'TEXT',    82, 15, 0),
    ('CO2_GKM',           'CO2 (g/km)',            'DECIMAL', 83, 10, 3),
    ('NORMAEURO',         'Norma Euro',            'TEXT',    84, 15, 0),
    ('MATRICULAANTERIOR', 'Matrícula anterior',    'TEXT',    85, 15, 0),
    ('PAISPROCEDENCIA',   'País de procedência',   'TEXT',    86, 15, 0),
    ('DTAQUISICAO',       'Data de aquisição',     'DATE',    87, 10, 0),
    ('VALORAQUISICAO',    'Valor de aquisição',    'DECIMAL', 88, 10, 2);

INSERT INTO dbo.CAMPOS
(
    CAMPOSSTAMP, ORDEM, NMCAMPO, DESCRICAO, TIPO, TABELA,
    LISTA, FILTRO, FILTRODEFAULT, ADMIN, RONLY, COMBO, VIRTUAL, VISIVEL,
    DECIMAIS, TAM, ORDEM_MOBILE, TAM_MOBILE, CONDICAO_VISIVEL, OBRIGATORIO
)
SELECT
    LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
    C.ORDEM, C.NMCAMPO, C.DESCRICAO, C.TIPO, 'VA',
    0, 0, '', 0, 0, '', '', 1,
    C.DECIMAIS, C.TAM, C.ORDEM, C.TAM, '', 0
FROM @CamposVA C
WHERE NOT EXISTS
(
    SELECT 1
    FROM dbo.CAMPOS E
    WHERE UPPER(LTRIM(RTRIM(ISNULL(E.TABELA, '')))) = 'VA'
      AND UPPER(LTRIM(RTRIM(ISNULL(E.NMCAMPO, '')))) = C.NMCAMPO
);

COMMIT TRANSACTION;
