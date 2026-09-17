# Correção de dados PHC — 17 de setembro de 2026

Estado: **COMMIT concluído e verificação integral pós-commit aprovada**.

## Âmbito

População fechada dos 200 documentos identificados na análise anterior. Os oito documentos da PETROGAL foram excluídos de todas as alterações. Intervenção nos outros 192 documentos, ligados entre GESTAO e Guest_SPA_Tur pelo mesmo FOSTAMP.

| Operação | Registos |
|---|---:|
| Eliminação de linhas-resumo QR duplicadas em GESTAO.FN | 156 |
| Eliminação das mesmas linhas ainda existentes em Guest_SPA_Tur.FN | 96 |
| Atualização de grupos de IVA em Guest_SPA_Tur.FOT | 195 |
| Eliminação de grupos FOT obsoletos, sem linhas válidas correspondentes | 3 |
| Atualização dos campos de IVA por tabela em GESTAO.FO | 192 |
| Atualização dos campos de IVA por tabela em Guest_SPA_Tur.FO | 192 |
| Atualização de montantes em Guest_SPA_Tur.ML | 113 |

As 113 linhas ML pertencem a 56 documentos: 56 linhas de base e 57 linhas de IVA. O IVA contabilizado a mais foi reduzido em **8.588,46 €**, com aumento correspondente das bases. Totais e contrapartidas foram preservados.

## Verificações

- Foi feito um ensaio integral com rollback antes da execução definitiva.
- Na execução definitiva, bloqueio e comparação integral dos registos com a cópia anterior antes de qualquer escrita.
- Todas as eliminações foram feitas por FNSTAMP/FOTSTAMP exatos, dentro dos FOSTAMP definidos; nenhuma eliminação genérica de linhas sem referência.
- As linhas FN eliminadas foram comprovadas como resumos QR duplicados. As linhas de detalhe válidas foram mantidas.
- FOT e campos FO de IVA por tabela reconciliam com a base, IVA e total corretos dos 192 documentos.
- ML dos 56 documentos reconcilia com FO; débito e crédito mantêm-se equilibrados em euros e moeda local.
- FO2, DO, contrapartidas ML, IM, PC e restantes campos dos registos abrangidos ficaram inalterados.
- Os oito documentos da PETROGAL ficaram integralmente inalterados.
- Os triggers existentes permaneceram ativos; não foi executada a procedure de integração.
- A verificação pós-commit usou uma nova ligação SQL e comparou todas as colunas das tabelas abrangidas com o estado esperado.

Exemplo: fatura 387, FOSTAMP `4CE5EDE6-6D02-4741-8C03-E`: FOT e contabilidade com base **14.107,16 €**, IVA **3.244,65 €**, total **17.351,81 €**.

## Cópias e rastreabilidade

- `before.json`: cópia integral anterior dos registos abrangidos, incluindo os eliminados e o esquema das tabelas. Permite preparar reposição pontual dos dados, se necessária; não executar uma reposição genérica sem verificar alterações posteriores.
- `repair_plan.json`: operações exatas sobre FN, FO e FOT.
- `ml_plan_review.json`: valores anteriores e finais por MLSTAMP, com evidências de atribuição às contas.
- `execute_repair.py`: executor transacional; sem argumentos faz rollback. O modo `--apply` recusa repetição quando existe relatório de aplicação.
- `dry_run_report.json`: ensaio concluído com rollback.
- `apply_report.json`: commit concluído e checksums das fontes.
- `post_commit_verification.json`: resultados da verificação após commit.
- `post_commit_after.json`: cópia integral do estado observado após commit.

## Limite desta intervenção

Esta intervenção corrigiu os dados solicitados. Não alterou o código da app nem a procedure de integração; a origem identificada das linhas-resumo duplicadas necessita de correção separada para evitar recorrências. O Excel produzido antes desta intervenção é um retrato anterior, não o estado atual da contabilidade.
