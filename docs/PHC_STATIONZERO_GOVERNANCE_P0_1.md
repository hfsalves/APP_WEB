# P0.1 — Governação PHC ↔ StationZero

**Estado:** levantamento do Database Manager concluído em 11-08-2026. O foco são os dados nucleares e os mappings efetivamente configurados.

## Princípio de governação

| Domínio | Sistema mestre | StationZero |
| --- | --- | --- |
| Clientes, fornecedores, projetos/obras, centros de custo | PHC, salvo mapping formal aprovado | Consulta, operação e sincronização controlada |
| Compras, faturação, recebimentos, pagamentos e contabilidade | PHC | Preparação e controlo operacional |
| Documents AI, despesas, oficina e processos operacionais | StationZero | Mestre do processo; publicação controlada quando aplicável |

O Database Manager passa a ser a referência oficial do que é sincronizado entre a app e o PHC. Cada mapping tem de indicar a direção, a chave, os campos abrangidos, a precedência em conflito e o destino.

## Mapping definido no Database Manager

O catálogo está guardado na `GR360_CORE`, nas tabelas `DBM_TABLE_MAPPING`, `DBM_FIELD_MAPPING` e `DBM_TARGET_TABLE`.

| Tabela nuclear | Estado | Fluxo | Destino | Leitura |
| --- | --- | --- | --- | --- |
| Clientes (`CL`) | Ativo | 12 campos bidirecionais; 3 campos App → PHC | `CL` e `CL2` de cada empresa PHC ativa | É o único mapping mestre bidirecional ativo. A chave é `CLSTAMP`; nome, NIF, contacto, morada, email, país, estabelecimento e número são sincronizados. |
| Obras / processos (`OPC`) | Ativo pelo worker | PHC → App | `HSOLS_MASTER.dbo.OPC` → `GR360_CORE.dbo.OPC` | É o primeiro fluxo operacional implementado. O worker usa fila e trigger no PHC, processa inserts, updates e deletes e executa reconciliação. |
| Viaturas (`VA`) | Ativo | Destino → App | `HSOLS_MASTER.dbo.GR360_SYNC_VA_SOURCE` | Importação de 39 campos, incluindo matrícula, frota, responsável, centro de custo, custo e seguros. |
| Fornecedores (`FL`) | Desativado | Bidirecional | `FL` por empresa PHC | Configurado, mas não está em execução. |
| Artigos (`ST`) | Desativado | Maioritariamente bidirecional | `HSOLS_MASTER.dbo.ST` e `STOBS` | Configurado, mas não está em execução. |
| Referências (`FREF`) | Desativado | Bidirecional | `HSOLS_MASTER.dbo.FREF` | Configurado, mas não está em execução. |

No mapping de clientes, o destino é resolvido por entidade FE. Existem sete bases PHC ativas configuradas: HSOLS_FR, HSOLS_PT, GR360, HSOLS_DE, HSOLS_ES, HSOLS_MA e INTERSOL.

O projeto [GR_workers](/Users/hugoalves/Projects/GR_workers) contém o agente `phc_table_sync_monitor`, agendado de cinco em cinco minutos com `OPC`, `VA` e `CL`, em modo de aplicação, reconciliação e processamento de fila. Para `OPC`, cria `GR360_SYNC_QUEUE` e o trigger `TRG_GR360_SYNC_OPC` no `HSOLS_MASTER`; a fila conserva chave, operação, estado, tentativas e último erro.

Foi detetada uma inconsistência relevante: o mapping `OPC` está com `ENABLED = 0` no Database Manager, mas o worker não valida esse campo antes de sincronizar. Portanto, `OPC` está operacional apesar de aparecer desativado na configuração. Esta divergência deve ser eliminada: ou o worker passa a respeitar `ENABLED`, ou o estado do mapping deve ser corrigido para refletir a realidade.

## Lacuna P0.1: auditoria de sincronização

Os mappings dizem o que deve acontecer, mas falta provar o que aconteceu de ponta a ponta. A fila de `OPC` já regista a operação e o estado técnico, mas não tem identificador de lote, versão do mapping, utilizador/worker, campos alterados, valores antes/depois ou resultado de reconciliação persistente.

A proposta é criar a base separada `SZERO_AUDIT`, descrita em [`SZERO_INTEGRATION_AUDIT_ARCHITECTURE.md`](SZERO_INTEGRATION_AUDIT_ARCHITECTURE.md). A app e os `szero_workers` devem escrever no mesmo registo antes e depois de cada lote.

## Decisões prioritárias

1. Tratar `OPC`, `CL` e `VA` como os três fluxos P0.1 em produção; manter `FL`, `ST` e `FREF` desativados até validação de negócio.
2. Definir para cada campo bidirecional de `CL` a regra de conflito: PHC vence, app vence ou vence a alteração mais recente baseada numa data confiável.
3. Rever a chave de `VA`: hoje a execução usa a matrícula como chave, apesar de também transportar `VASTAMP`; a chave imutável deve ser confirmada antes de permitir sincronização de retorno.
4. Implementar auditoria comum, checkpoints e reconciliação antes de ativar novos mappings.
