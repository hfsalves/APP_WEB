# TP047 / TK 164 - Pre-Fatura no Controlo de Gestao

## Implementacao local (2026-09-09)

- `workflow/validate` chama a integracao antes de concluir/distribuir CdG.
- Permissao servidor: `proforma_invoice`. O antigo `control-ok` confirma a
  revisao mas ja nao conclui CdG por si so.
- Servico: `services/document_ai_preinvoice_service.py`; coordenador TP041,
  operacao `preinvoice`, metadados `phc_preinvoice`. Nao substitui
  `phc_integration` da Rececao.
- Serie identificada por TS.NMDOS; BO/BO2/BO3/BI/BI2/BOT e ANEXOS na mesma
  transacao PHC, com bloqueios de numeracao, origens e identificacao de FO.
- Chave idempotente `DOC_AI_PF:<FOSTAMP>` em ANEXOS.UNIQUEID. Fingerprint dos
  dados impede recuperar silenciosamente uma operacao com conteudo diferente.
- Linhas e sublinhas usam a origem imediata. BI.OBISTAMP e BI.OOBISTAMP apontam
  para o BISTAMP fonte; BI.OOBOSTAMP conserva o valor herdado da fonte.
  O BI.BOSTAMP pertence a nova Pre-Fatura. QTT2 das novas linhas e zero.
- Na fonte, QTT2/FECHADA refletem a quantidade retomada; NDOC/NMDOC/FNO
  identificam a Pre-Fatura, conforme exemplos nativos INTERSOL consultados.
- Quantidades parciais, disponibilidade concorrente, fornecedor/estabelecimento,
  entidade/moeda, Obra, artigo, preco/descontos, IVA e totais sao verificados.
- PDF original confirmado no GED da FO e associado ao novo BO sem mover ou
  apagar o ficheiro. PDFs das origens sao ligados ao BO; GdR exige PDF.
- A associacao por linha permite quantidades explicitas para NdE, Contrato,
  GdR e STSE. A disponibilidade visual desconta BI.QTT2; o servidor revalida.

## Evidencia consultada em leitura

- TK 164: prompt completo; sem anexos TK associados na consulta efetuada.
- `scripts/import_bmso_hsols_fr.py` e criacao de STSE no modulo
  `gr_subcontractor_measurements`.
- TS/BO/BI de HSOLS_FR, INTERSOL e GR360 em 10.0.1.12:
  serie 218 denominada Pre-Facture nas tres bases; NdE GR360 usa serie 2,
  denominada Bon Commande Fournisseur, contra 102 nas outras duas.
- Exemplos PHC confirmam OOBOSTAMP vazio na maioria das origens NdE/Contrato/
  GdR; quando preenchido nas STSE, coincide com o OOBOSTAMP herdado e aponta
  ao Contrato Sub.Emp. Nao equivale em geral ao BOSTAMP da origem imediata.

## Verificacao e limites

- 19 testes novos; 266 testes Document AI aprovados. Falhas SQL/PDF, repeticao,
  quantidades parciais, multiplas origens e bloqueio de conclusao CdG cobertos.
- JavaScript verificado; modal e quantidade testados com Playwright em
  1440px e 390px (fixture isolada com codigo/template/CSS reais).
- Nao foram criados documentos de teste nas bases PHC de producao.
- Falta teste funcional autorizado com um documento real por familia e
  verificacao da distribuicao/visualizacao PHC na instalacao publicada.
- Moedas diferentes de EUR/EURO, origens com IVA incluido e linhas de
  quantidade nao positiva bloqueiam explicitamente; nao se inventam cambios,
  normalizacoes de IVA ou movimentos sem quantidade.
- Este registo nao certifica producao nem justifica fechar TK 164 antes dessa
  validacao. Os restantes tickets nao foram tratados neste passo.
