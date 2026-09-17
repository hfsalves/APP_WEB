# Diagnóstico da integração de compras GESTAO → PHC

Análise em 17/09/2026, por consultas de leitura e inspeção do código. Nenhuma procedure foi executada e nenhum dado, job, trigger ou código funcional foi alterado. Os ficheiros *.snapshot.sql são cópias das definições consultadas, não migrações para executar.

## Conclusão

A fatura 387 contém na app uma linha adicional com o valor integral da base, além das 13 linhas reais de renda. A procedure de sincronização usa todas as linhas para calcular o IVA por taxa, mas copia os totais gerais do cabeçalho. Assim, aceita e transmite duas representações incompatíveis do mesmo documento.

Foi identificado no formulário um bug que permite esta situação: substituir linhas por um contrato ou por uma nova importação QR descarta as linhas antigas da memória sem agendar a sua eliminação na base de dados.

## Documento confirmado

- Base da app: GESTAO; destino: Guest_SPA_Tur, no mesmo servidor.
- FOSTAMP comum: `4CE5EDE6-6D02-4741-8C03-E`.
- V/Fatura 387, data 15/05/2026, fornecedor PEDRO NUNO SIMÃO ALVES.
- PHC FOID: 38741.
- Integração registada na app: 18/05/2026 11:29:22.550.
- Documento contabilístico: diário Compras, lançamento 5000039.
- DOSTAMP: `ADM26060954012,362921077`; criado em 09/06/2026 às 15:00:12.

| Origem/campo | Base € | IVA € | Total € |
|---|---:|---:|---:|
| FO da app e do PHC: ETTILIQ/EIVAIN, ETTIVA, ETOTAL | 14 107,16 | 3 244,65 | 17 351,81 |
| 13 linhas reais de renda | 14 107,16 | 3 244,65 calculado | 17 351,81 |
| Linha adicional na app | 14 107,16 | 3 244,65 calculado | — |
| Agregado das 14 FN da app, arredondado no fim | 28 214,32 | 6 489,29 | — |
| Único registo FOT no PHC, código 2, taxa 23% | 28 214,32 | 6 489,29 | — |

A linha adicional tem FNSTAMP `77540FE2-5A2B-4194-A32D-C`, REF e DESIGN vazios, QTT=1, EPV=ETILIQUIDO=14107.16, TAXAIVA=23, TABIVA=2 e LORDEM=1. Tanto GESTAO.FO.EIVAV2 como PHC.FO.EIVAV2 contêm 6489.29.

O IVA 6489.29 corresponde exatamente a ROUND(28214.32 × 0.23, 2). A diferença de um cêntimo relativamente a 2 × 3244.65 resulta de arredondar apenas depois da soma.

Não existem dois registos FOT para este documento: existe um registo com os valores duplicados. Atualmente o PHC tem apenas as 13 FN de renda. A linha adicional permanece na app, mas já não está em PHC.FN; o agregado FOT ficou divergente das linhas atuais. Sem histórico de alterações, não é possível determinar quem/quando removeu essa linha no PHC, nem reconstruir integralmente a sequência histórica. Os triggers nativos de FN não disponibilizam definição em sys.sql_modules nesta consulta.

## Procedure responsável

`Guest_SPA_Tur.dbo.sp_sync_compras`, última alteração 15/05/2026 11:54:08.663. O job SQL Agent `SYNC COMPRAS` executa `EXEC DBO.sp_sync_compras`; o horário chama-se MINUTO, mas está configurado para **cada 10 segundos**.

Referências à [definição consultada](/Users/hugoalves/Projects/APP_WEB/outputs/phc_integration_analysis_20260917/Guest_SPA_Tur.sp_sync_compras.snapshot.sql:1):

- Linhas 12–18: seleciona até 20 FO com SYNC=0, sem erro, e OBS='Ok - Tudo validado'.
- Linhas 44–51: calcula EIVAV1…EIVAV4 sobre **todas** as GESTAO.FN do documento. Não distingue linha-resumo de linhas de detalhe.
- Linhas 94–100: copia ETTILIQ, ETTIVA e ETOTAL do cabeçalho; simultaneamente copia os EIVAV calculados com as linhas. A divergência passa para o PHC.
- Linhas 129–165: copia FN da app para PHC. Mapeia TAXAIVA da app para IVA no PHC.
- Linhas 167–190: gera FOT agrupando as FN do PHC por TABIVA/IVA.
- Linhas 192–214: valida apenas que FO, FO2 e pelo menos uma FN existem. Não valida igualdade entre bases e IVA das linhas, do cabeçalho e da FOT.
- Linhas 216–223: marca SYNC=1 e confirma a transação, mesmo quando esses totais não coincidem.

A procedure não escreve DO/ML. O lançamento contabilístico é uma fase posterior no PHC.

## Origem provável da linha adicional e bug confirmado na app

A [sp_FO_ApplyQrCode](/Users/hugoalves/Projects/APP_WEB/outputs/phc_integration_analysis_20260917/GESTAO.sp_FO_ApplyQrCode.snapshot.sql:245) gera uma linha por taxa com REF/DESIGN vazios, QTT=1 e EPV=ETILIQUIDO=base. O QR deste documento contém I7:14107.16 e I8:3244.65. O stamp com hífen da linha adicional corresponde ao formato produzido por esta procedure; as rendas têm stamps no formato hexadecimal usado pelo JavaScript.

Na [substituição por contrato](/Users/hugoalves/Projects/APP_WEB/static/js/fo_compras_form.js:1214), o código executa:

```js
linesData = [];
deletedLineIds = [];
```

Em seguida cria as novas linhas. Os IDs persistidos das linhas anteriores não são conservados para eliminação. [saveAllLines](/Users/hugoalves/Projects/APP_WEB/static/js/fo_compras_form.js:2382) só apaga os IDs contidos em deletedLineIds, que ficou vazio. O [cálculo do cabeçalho](/Users/hugoalves/Projects/APP_WEB/static/js/fo_compras_form.js:2427) percorre apenas linesData, pelo que pode gravar totais corretos para as linhas novas enquanto as antigas continuam na base de dados.

A [substituição por linhas importadas do QR](/Users/hugoalves/Projects/APP_WEB/static/js/fo_compras_form.js:719) tem o mesmo defeito. O bug de substituição por contrato já existia no commit 2914534a de 25/03/2026, anterior ao registo analisado.

A sequência QR → substituição por contrato → conservação indevida da linha-resumo é fortemente sustentada por estes dados, mas a ação concreta do utilizador não foi confirmada num histórico de auditoria.

Existe ainda uma janela de concorrência: a app [grava FO e liberta SYNC antes de gravar FN](/Users/hugoalves/Projects/APP_WEB/static/js/fo_compras_form.js:2205), e grava linhas em pedidos separados. Como o job corre a cada 10 segundos, pode ler um documento entre essas operações. Trata-se de um risco adicional confirmado no desenho do fluxo; não é necessário invocá-lo para reproduzir a duplicação desta fatura.

## Efeito contabilístico confirmado em ML

| Conta | Movimento atual € | Movimento coerente com a compra € |
|---|---:|---:|
| 62611112 — Rendas | Débito 10 862,52 | Débito 14 107,16 |
| 24323131 — IVA | Débito 6 489,29 | Débito 3 244,65 |
| 278100002 — Fornecedor | Crédito 17 351,81 | Crédito 17 351,81 |

A aritmética do lançamento confirma o efeito descrito: 17351.81 − 6489.29 = 10862.52. O excesso de IVA e a redução da base são ambos 3244.64. O documento fica equilibrado contabilisticamente, mas a distribuição entre rendas e IVA fica errada.

## Extensão observada

Triagem dos documentos da app com DATA >= 01/01/2026 e FOSTAMP existente no PHC. Comparação de SUM(FOT.EBASEINC/EVALOR) com FO.EIVAIN/ETTIVA, tolerância de 0,02 €. Estes são candidatos a revisão; não foi confirmado o movimento ML de todos eles.

- 3612 documentos comuns analisados.
- 215 com divergência FOT/cabeçalho.
- 200 com base FOT igual ao dobro da base do cabeçalho.
- Desses 200, 162 ainda têm na app o mesmo padrão de linha(s) sem REF/DESIGN com a base integral, mais linhas de detalhe, duplicando a soma.
- Os outros 38 casos com base duplicada não correspondem atualmente a esse padrão na app; requerem análise histórica/individual.
- 15 divergências não têm base exatamente duplicada.

| Grupo entre os 215 | PLANO=1 | PLANO=0 | Total |
|---|---:|---:|---:|
| Base duplicada e padrão resumo+detalhe ainda na app | 60 | 102 | 162 |
| Base duplicada sem esse padrão atual | 38 | 0 | 38 |
| Outras divergências | 5 | 10 | 15 |
| Total | 103 | 112 | 215 |

PLANO=1 indica documentos assinalados como integrados contabilisticamente; não demonstra isoladamente que cada lançamento contabilístico esteja errado. A amostra acima é de documentos comuns e não constitui auditoria integral de todas as compras PHC.

## Correção recomendada, ainda não aplicada

1. Corrigir a substituição de linhas no formulário, preservando os IDs antigos e eliminando-os efetivamente. Não excluir indiscriminadamente todas as linhas com REF vazia: podem ser legítimas.
2. Gravar cabeçalho e conjunto final de linhas numa única transação, tornando o documento elegível para sincronização apenas depois de concluída essa gravação.
3. Na procedure, usar um conjunto final coerente de linhas para calcular FO.EIVAV* e FOT; validar bases, IVA e total contra o cabeçalho antes do COMMIT. Divergências devem interromper a integração e ficar em SYNC_ERRO/SYNC_MSG.
4. Tratar explicitamente documentos já contabilizados: a rotina atual só apaga FO com PLANO=0, mas tenta inserir FO2/FO de novo sem um desvio explícito para PLANO=1. A reparação de documentos contabilizados requer um percurso próprio.
5. Para a fatura 387, reconciliar a linha adicional na app e recalcular os totais por taxa em FO/FOT; depois corrigir/regerar no PHC o documento contabilístico associado. Corrigir apenas FOT não retifica o ML já criado, e corrigir apenas ML deixa a origem inconsistente.
6. Rever os restantes candidatos com a mesma validação antes de qualquer correção em lote.

As [consultas de diagnóstico](/Users/hugoalves/Projects/APP_WEB/outputs/phc_integration_analysis_20260917/diagnostico_readonly.sql:1) reproduzem o caso e listam os candidatos. Não foi aplicada nenhuma destas correções.

