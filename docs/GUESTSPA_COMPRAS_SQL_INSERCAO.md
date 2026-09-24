# Inserção direta de compras GuestSpa por SQL

## Objetivo e âmbito

Este guia descreve como criar uma compra que siga o circuito normal da GuestSpa.

**Não inserir diretamente em `GUEST_SPA_TUR`.** A origem é a base `GESTAO`:

```text
GESTAO.dbo.FO (cabeçalho)
  + GESTAO.dbo.FN (linhas)
  -> Guest_SPA_TUR.dbo.sp_sync_compras
  -> GUEST_SPA_TUR.dbo.FO, FO2, FN e FOT
  -> contabilização posterior no PHC
```

O `FOSTAMP` é a chave comum entre o cabeçalho e todas as linhas.

## Regra operacional essencial

Executar o `INSERT` do cabeçalho e de todas as linhas **numa única transação**. Só no final o documento deve ficar com:

```text
SYNC = 0
SYNC_ERRO = 0            -- se a coluna existir
OBS = 'Ok - Tudo validado'
```

O job de sincronização só trata compras que cumpram estes critérios. Nunca usar `SYNC = 1`: esse estado é atribuído pela procedure depois de sincronizar com sucesso.

## Pré-requisitos a validar

Antes de inserir, confirmar:

1. O fornecedor existe em `V_FL`/`FL` e recolher `NO`, `NOME`, `NCONT`, `MORADA`, `LOCAL` e `CODPOST`.
2. O artigo existe em `ST` e recolher `REF`, `DESIGN`, `UNIDADE`, `FAMILIA` e `TABIVA`.
3. O centro de custo existe em `V_CCT`/`CCT`.
4. O modo de pagamento existe em `V_TP`; usar o respetivo `TPSTAMP` e `TPDESC`.
5. Não existe já uma compra equivalente para o fornecedor, tipo e número do documento.
6. O documento não é uma segunda representação do mesmo valor: não combinar linhas-resumo de IVA com linhas de detalhe.

Exemplo de consultas de apoio:

```sql
SELECT NO, NOME, NCONT, MORADA, LOCAL, CODPOST
FROM dbo.V_FL
WHERE NO = @NoFornecedor;

SELECT REF, DESIGN, UNIDADE, FAMILIA, TABIVA
FROM dbo.ST
WHERE REF = @RefArtigo;

SELECT CCUSTO FROM dbo.V_CCT WHERE CCUSTO = @CCusto;

SELECT TPSTAMP, TPDESC, DIAS, OLLOCAL
FROM dbo.V_TP
WHERE TPSTAMP = @TpStamp;
```

## `GESTAO.dbo.FO`: cabeçalho

### Campos funcionais obrigatórios

| Campo | Preenchimento |
| --- | --- |
| `FOSTAMP` | Identificador único, até 25 caracteres. |
| `DOCNOME` | Tipo: por exemplo `V/Fatura`, `V/Fatura Recibo`, `V/Nt. Crédito`, `V/Nt. Crédito DD` ou `V/Fatura Comissões`. |
| `ADOC` | Número do documento do fornecedor. |
| `DATA` | Data contabilística/operacional. |
| `DOCDATA` | Data constante no documento. |
| `PDATA` | Data de vencimento. |
| `NO`, `NOME`, `NCONT` | Identificação do fornecedor. |
| `MORADA`, `LOCAL`, `CODPOST` | Morada do fornecedor. |
| `CCUSTO` | Centro de custo do cabeçalho. |
| `TPSTAMP`, `TPDESC` | Condição/modo de pagamento. |
| `ETTILIQ` | Base sem IVA. |
| `ETTIVA` | Total de IVA. |
| `ETOTAL` | Total, igual a `ETTILIQ + ETTIVA`. |
| `TIPO` | Sempre `FO`. |
| `FOANO` | Ano de `DATA`. |
| `PLANO` | `0`; não marcar como contabilizado. |
| `SYNC` | `0`; pendente de sincronização. |
| `OBS` | Exatamente `Ok - Tudo validado`. |
| `OUSRINIS`, `OUSRDATA`, `OUSRHORA` | Auditoria de criação. |

### Defaults que devem ser enviados explicitamente

Para reproduzir o comportamento do formulário/importador, preencher também:

```text
DOCCODE, EIVAIN, EFINV, EIVAV1..EIVAV9,
NMAPROV, DTAPROV, APROVADO, NOME2,
OLLOCAL, QR_CODE, COLAB,
IMPUTAR, IMPUTMES, IMPUTANO, IMPUTVALOR, IMPUTDESIGN, NIMPUTAR.
```

Valores usuais:

```text
DOCCODE = 55 para V/Fatura
EIVAIN = ETTILIQ
EFINV = 0
APROVADO = 0
PLANO = 0
SYNC = 0
QR_CODE = ''
COLAB = ''
IMPUTAR = IMPUTMES = IMPUTANO = NIMPUTAR = 0
IMPUTVALOR = 0
IMPUTDESIGN = ''
```

## `GESTAO.dbo.FN`: linhas

Criar pelo menos uma linha por compra.

| Campo | Preenchimento |
| --- | --- |
| `FNSTAMP` | Identificador único por linha. |
| `FOSTAMP` | O mesmo valor do cabeçalho. |
| `REF` | Referência do artigo. |
| `DESIGN` | Designação do artigo/serviço. |
| `UNIDADE` | Unidade. |
| `QTT` | Quantidade. |
| `EPV` | Preço unitário sem IVA. |
| `ETILIQUIDO` | Normalmente `QTT * EPV`. |
| `TABIVA` | Código interno da taxa, não a percentagem. |
| `TAXAIVA` | Percentagem da taxa: `23.00`, `13.00`, `6.00` ou `0.00`. |
| `IVA` | IVA monetário da linha, para manter consistência com o importador atual. |
| `IVAINCL` | `0` se o preço não inclui IVA; `1` se inclui. |
| `FNCCUSTO` | Centro de custo da linha. |
| `DTCUSTO` | Data de custo. |
| `FAMILIA` | Família do artigo. |
| `LORDEM` | Ordem sequencial: 1, 2, 3, ... |

Mapeamento de `TABIVA` atualmente usado pelo processo QR:

| `TABIVA` | Taxa |
| --- | --- |
| `1` | 6% |
| `2` | 23% |
| `3` | 13% |
| `4` | 0%/isenção |

`REF`, `FAMILIA` e `FNCCUSTO` são obrigatórios para a validação funcional. Se algum faltar, o documento não deve receber `OBS = 'Ok - Tudo validado'`.

## Coerência fiscal e de totais

Antes do `COMMIT`, validar:

```text
FO.ETTILIQ = soma das bases líquidas das FN
FO.ETTIVA  = soma dos IVAs das FN, considerando IVAINCL
FO.ETOTAL  = FO.ETTILIQ + FO.ETTIVA
```

Para `IVAINCL = 0`:

```text
base líquida da linha = ETILIQUIDO
IVA da linha = ETILIQUIDO * TAXAIVA / 100
```

Para `IVAINCL = 1`:

```text
base líquida da linha = ETILIQUIDO / (1 + TAXAIVA / 100)
IVA da linha = ETILIQUIDO - base líquida da linha
```

A sincronização recalcula `EIVAV1` a `EIVAV4` a partir das linhas, mas copia `ETTILIQ`, `ETTIVA` e `ETOTAL` do cabeçalho. Logo, um cabeçalho incoerente será transmitido ao PHC.

## Script parametrizado de exemplo

O exemplo cria uma fatura de 100,00 EUR + IVA a 23%. Substituir todos os parâmetros `@...` por valores existentes e válidos.

```sql
USE GESTAO;
SET XACT_ABORT ON;
BEGIN TRAN;

DECLARE @FOSTAMP varchar(25) =
  LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25);

DECLARE @Data date = '2026-09-24';
DECLARE @DataVencimento date = '2026-10-24';
DECLARE @NoFornecedor int = 123;
DECLARE @NomeFornecedor varchar(55) = 'FORNECEDOR, LDA';
DECLARE @Nif varchar(20) = '123456789';
DECLARE @Morada varchar(55) = 'Morada do fornecedor';
DECLARE @Local varchar(43) = 'Localidade';
DECLARE @CodPost varchar(45) = '0000-000 Localidade';
DECLARE @CCusto varchar(50) = 'CCUSTO-VALIDO';
DECLARE @TpStamp varchar(25) = 'TPSTAMP-VALIDO';
DECLARE @TpDesc varchar(50) = 'DÉBITO DIRETO';
DECLARE @Utilizador varchar(30) = 'SQL_IMPORT';

INSERT dbo.FO (
  FOSTAMP, DOCNOME, ADOC, NOME,
  ETOTAL, DATA, TIPO, DOCDATA, FOANO, DOCCODE,
  NO, CCUSTO, PDATA, PLANO,
  EIVAIN, ETTIVA, EFINV, ETTILIQ,
  MORADA, LOCAL, CODPOST, NCONT,
  NMAPROV, DTAPROV, APROVADO, NOME2,
  TPSTAMP, TPDESC, OLLOCAL,
  OUSRINIS, OUSRDATA, OUSRHORA,
  OBS, QR_CODE, COLAB, SYNC,
  IMPUTAR, IMPUTMES, IMPUTANO, IMPUTVALOR, IMPUTDESIGN, NIMPUTAR,
  EIVAV1, EIVAV2, EIVAV3, EIVAV4, EIVAV5, EIVAV6, EIVAV7, EIVAV8, EIVAV9
)
VALUES (
  @FOSTAMP, 'V/Fatura', 'FT 2026/123', @NomeFornecedor,
  123.00, @Data, 'FO', @Data, YEAR(@Data), 55,
  @NoFornecedor, @CCusto, @DataVencimento, 0,
  100.00, 23.00, 0, 100.00,
  @Morada, @Local, @CodPost, @Nif,
  '', @Data, 0, '',
  @TpStamp, @TpDesc, 'WEB',
  @Utilizador, @Data, CONVERT(varchar(5), GETDATE(), 108),
  'Ok - Tudo validado', '', '', 0,
  0, 0, 0, 0, '', 0,
  0, 23.00, 0, 0, 0, 0, 0, 0, 0
);

INSERT dbo.FN (
  FNSTAMP, FOSTAMP, REF, DESIGN, UNIDADE,
  TAXAIVA, QTT, IVA, IVAINCL, TABIVA,
  LORDEM, ETILIQUIDO, EPV,
  FNCCUSTO, FAMILIA, DTCUSTO
)
VALUES (
  LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
  @FOSTAMP, 'REF-VALIDA', 'Artigo/serviço válido', 'UN',
  23.00, 1.00, 23.00, 0, 2,
  1, 100.00, 100.00,
  @CCusto, 'FAMILIA-VALIDA', @Data
);

COMMIT;

SELECT FOSTAMP, DOCNOME, ADOC, ETTILIQ, ETTIVA, ETOTAL, OBS, SYNC
FROM dbo.FO
WHERE FOSTAMP = @FOSTAMP;

SELECT FNSTAMP, FOSTAMP, REF, DESIGN, QTT, EPV, ETILIQUIDO,
       TABIVA, TAXAIVA, IVAINCL, FNCCUSTO, FAMILIA
FROM dbo.FN
WHERE FOSTAMP = @FOSTAMP
ORDER BY LORDEM;
```

## Depois do `COMMIT`

1. Aguardar a sincronização.
2. Confirmar na `GESTAO.dbo.FO` que `SYNC = 1` e `SYNC_ERRO = 0`.
3. Se houver erro, consultar `SYNC_MSG`.
4. Confirmar no PHC a existência de `FO`, `FO2`, `FN` e `FOT` com o mesmo `FOSTAMP`.
5. Confirmar que a soma de `FOT.EBASEINC` e `FOT.EVALOR` coincide com o cabeçalho.

```sql
SELECT FOSTAMP, SYNC, SYNC_ERRO, SYNC_MSG, SYNC_DATA
FROM GESTAO.dbo.FO
WHERE FOSTAMP = @FOSTAMP;

SELECT FOSTAMP, ETTILIQ, ETTIVA, ETOTAL, EIVAIN, EIVAV1, EIVAV2, EIVAV3, EIVAV4
FROM GUEST_SPA_TUR.dbo.FO
WHERE FOSTAMP = @FOSTAMP;

SELECT FOSTAMP, CODIGO, TAXA, EBASEINC, EVALOR
FROM GUEST_SPA_TUR.dbo.FOT
WHERE FOSTAMP = @FOSTAMP;
```

## Não fazer

- Não inserir diretamente em `GUEST_SPA_TUR.dbo.FO`, `FO2`, `FN` ou `FOT`.
- Não definir `SYNC = 1` manualmente.
- Não definir `PLANO = 1` numa compra nova.
- Não criar linhas com `REF`, `FAMILIA` ou `FNCCUSTO` vazios quando se pretende sincronização.
- Não inserir o cabeçalho, fazer `COMMIT`, e só depois inserir as linhas.
- Não usar uma linha por taxa de IVA juntamente com linhas reais do documento: isso duplica a base e o IVA em `FOT`.
- Não tentar corrigir uma compra já contabilizada só por SQL: exige um circuito específico de correção contabilística.

## Referências no repositório

- Formulário e gravação: `static/js/fo_compras_form.js`.
- Contrato de inserção já usado pela importação: `services/airbnb_commission_import_service.py`.
- Procedure de sincronização analisada: `outputs/phc_integration_analysis_20260917/Guest_SPA_Tur.sp_sync_compras.snapshot.sql`.
- Diagnóstico de incoerências de linhas/totais: `outputs/phc_integration_analysis_20260917/diagnostico.md`.
