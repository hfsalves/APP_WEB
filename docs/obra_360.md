# Hub de Obra 360º

## Objetivo e isolamento

O Hub de Obra 360º parte do registo sincronizado de `dbo.OPC` na `GR360_CORE`.
Não cria tabelas, não altera sincronizações nem grava informação nas bases PHC.
Só responde quando o alvo ativo é `client` e a base configurada é explicitamente
`GR360_CORE`; em GuestSpaTur as rotas devolvem `404` antes de consultar dados e o
widget não é incluído no dashboard.

## Fontes ativas

| Card / indicador | Origem | Estado |
| --- | --- | --- |
| Identificação da obra | `GR360_CORE.dbo.OPC` (`PROCESSO`, `DESCRICAO`, `NOME`, `U_ORIGEM`) | Ativo |
| Orçamento | Serviço existente `opc_phc_info_service`, dossiers PHC de orçamento | Ativo, carregamento progressivo |
| Autos de cliente | Serviço existente `opc_phc_info_service`, autos PHC | Ativo, carregamento progressivo |
| Faturas de cliente / faturado | Serviço existente `opc_phc_info_service`, `FT`/`FT2` PHC | Ativo, carregamento progressivo |
| BL fornecedor | Dossiers internos PHC `BO`/`BO2`, série `TS` cujo nome é “Bon Livraison Fourn.” | Ativo, carregamento progressivo e linhas `BI` |
| BC fornecedor | Dossiers internos PHC `BO`/`BO2`, série `TS` cujo nome é “Bon Commande Fournisseur” | Ativo, carregamento progressivo e linhas `BI` |

Os valores financeiros não disponíveis são devolvidos como `null` com o estado
`sem_dados`, nunca como `0,00 €` confirmado.

## Em preparação

Contrato/adjudicado, adicionais, compras, faturas de fornecedor,
autos de subempreiteiro, fornecedores, materiais, produção, custos, proveitos,
recebimentos, pagamentos, anexos e margem ficam identificados como **Em
preparação** até existir uma fonte e regra de cálculo confirmadas.

## Rotas

- `GET /obra-360/<codigo>`: dossiê de obra.
- `GET /api/obra-360/search?q=...`: pesquisa por processo, centro de custo,
  cliente, origem ou designação.
- `GET /api/obra-360/<codigo>/overview`: identificação e estrutura inicial.
- `GET /api/obra-360/<codigo>/cards/<card_code>`: detalhe de um card.
- `GET /api/obra-360/recent`: obras recentemente abertas na sessão do utilizador.

Todas exigem permissão de consulta a `OPC`. A pesquisa também filtra as obras
pelas empresas ativas atribuídas ao utilizador.
