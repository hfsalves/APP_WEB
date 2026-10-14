# Mapas de deslocações — PHC, reconstrução e versões

Painel `/mapas-deslocacoes` e editor `/mapas-deslocacoes/reconstrucao`, com link na
sidebar em contexto `client` / `GR360_CORE`. Administradores e developers têm
acesso; os restantes utilizadores precisam de `ACESSOS.TABELA = 'RH_MAPAS'`,
`CONSULTAR = 1`, além de uma associação ativa em `US_FE` à empresa consultada.
Permissão sobre obras ou autos não concede acesso a remunerações.

A leitura PHC não requer migração. A gravação de propostas requer executar
`migrations/gr_travel_maps.sql` explicitamente em **GR360_CORE**, durante a
instalação. O script recusa outras bases. Não foi aplicado à produção nesta
implementação. Sem as tabelas, a consulta salarial continua disponível e a
interface explica que o armazenamento está por instalar.

Não se criam tabelas ao abrir páginas, não se grava no PHC e não se importa
nem consulta o planeamento. O acesso PHC usa ligações de leitura com
rollback/close. As versões usam o engine da sessão encaminhada para `client`,
nunca o `db.engine` padrão. Não iniciar a aplicação completa para testar o
módulo: o arranque legado tem outras rotinas de inicialização.

Permissões adicionais: `RH_MAPAS.EDITAR = 1` para gerar, alterar e rejeitar;
`RH_MAPAS_VALIDAR.CONSULTAR = 1` para validar, sempre com consulta salarial e
acesso às empresas de origem. ADMIN/DEV mantêm o acesso administrativo.
Os POST exigem JSON e o token de sessão enviado em `X-Travel-CSRF`.

## Rotas

- `GET /api/gr_mapas/empresas`: empresas autorizadas, sem divulgar servidor.
- `GET /api/gr_mapas/mensal?feid=2&ano=2026&mes=9`: valores e linhas originais.
- `GET /api/gr_mapas/autos?feid=1&ano=2026&mes=9`: autos da empresa selecionada.

Todos os endpoints exigem autenticação, contexto GR360 e ACL salarial. Os dois
últimos revalidam o âmbito da empresa. As respostas usam `private, no-store`.
- `GET /api/gr_mapas/contexto?feid=2&ano=2026&mes=9&employee_key=...`:
  trabalhador, ficha atual PE/PE2 (`payroll.employee_profile`), obras candidatas
  e versão guardada. `autos_feid` pode repetir-se
  para selecionar até oito empresas. Se houver versão anterior, a seleção
  original é recuperada por omissão.
- `GET /api/gr_mapas/propostas?feid=2&ano=2026&mes=9`: resumos das versões atuais.
- `GET /api/gr_mapas/propostas/<id>?version=1`: versão e histórico autorizado.
- `POST /api/gr_mapas/propostas`: gera e guarda uma proposta inferida.
- `POST /api/gr_mapas/propostas/<id>/editar`: nova versão com alterações humanas.
- `POST /api/gr_mapas/propostas/<id>/rejeitar`: nova versão rejeitada.
- `POST /api/gr_mapas/propostas/<id>/validar`: decisão humana explícita.

Os POST recebem `request_id` (UUID), `expected_version` (0 para o primeiro
mapa) e `reason`. A geração recebe empresa, ano, mês, chave do trabalhador,
empresas dos autos e `inputs`; os dados PHC e dos autos são sempre relidos no
servidor. Campos enviados pelo cliente não substituem esses valores. A edição
aceita apenas campos permitidos nas linhas existentes. Não há endpoint PDF.

## Contrato de leitura salarial

- O mês é selecionado por `PR.DATA >= início AND PR.DATA < mês_seguinte`.
- Incluem-se todos os recibos do período, com ou sem as rubricas configuradas.
- Ligações: `PRRE.PRSTAMP = PR.PRSTAMP`; identidade: empresa/base + `PE.PESTAMP`.
  Números sem uma única correspondência em `PE` ficam explicitamente por resolver.
- Preservam-se quantidade (`RQTT`), valor unitário (`ERVU`), valor (`ERE`), sinais,
  referências originais e estado original do recibo. Os valores são somados com
  `Decimal` e serializados como strings, sem ajustar montantes ao produto quantidade × taxa.
- `PRRE.DTREF` é referência salarial, não data de deslocação. Referências fora
  do mês, origens de regularização e valores divergentes geram avisos.
- Ainda não existe regra confirmada de exclusão por `PR.STATUS`: a página
  apresenta valores registados para conferência, sem certificar fecho salarial.
- Falhas de ligação/esquema, valores inválidos, duplicação de linhas ou excesso
  do limite de 20 000 linhas devolvem erro, nunca totais parciais/zeros aparentes.
- Categoria não configurada = `null`; categoria configurada sem movimentos = 0.
  Mapa/diferença/reconciliação são `null` até existir reconstrução.

## Mapeamento explícito de rubricas

O padrão é restrito a `HSOLS_PT`, ano 2026, após inspeção de dados: KM = CR 60,
AC estrangeiro = CR 40, AC nacional = desconhecido (`null`). Outras bases e anos
ficam por configurar; não há classificação por semelhança das descrições.

Para substituir o padrão, definir `GR_TRAVEL_MAPS_CONFIG` na configuração Flask
ou como variável de ambiente JSON. A configuração substitui o conjunto completo:

```json
{
  "HSOLS_PT": [{
    "version": "hsols-pt-2026-v1",
    "valid_from": "2026-01-01",
    "valid_to": "2026-12-31",
    "currency": "EUR",
    "codes": {"km": [60], "ac_nacional": null, "ac_estrangeiro": [40]}
  }]
}
```

`null` significa desconhecido; `[]` significa confirmação explícita de que a
categoria não tem rubricas. Não configurar `[]` para eliminar o aviso de falta
de configuração. Não repetir códigos entre categorias, nem sobrepor vigências.
Uma mudança a meio do mês é recusada: exige futura leitura segmentada.
Este adaptador usa `ERE/ERVU` em EUR; outras moedas requerem adaptação explícita.

## Autos como única fonte operacional

A empresa dos autos pode diferir da empregadora, sempre dentro das empresas
autorizadas. São consultadas séries `TS` com nome exato, sem diferenças de acento
ou caixa, `Situation de Travaux` e `Auto de Medição`. São excluídos documentos
anulados (`BO2.ANULADO`) e não se incluem séries de crédito/subempreitada.

Os documentos são selecionados por `BO.DATAOBRA`. Uma linha atual `BI.QTT > 0`
ou `BI.ETTDEB > 0` sinaliza medição positiva; não se somam campos acumulados.
Os autos sem medição positiva continuam visíveis, mas não contam como obras
candidatas. A data documental ainda não confirma o período real da produção.

A obra é localizada por `BO2.PROCESSO = OPC.PROCESSO`. Correspondências ausentes
ou múltiplas não escolhem uma morada arbitrária. `CCUSTO` é preservado como fonte,
sem o transformar automaticamente numa associação inequívoca à obra.
O leitor de autos não deduz o país da base PHC nem uma presença individual na obra.

## Morada e viatura da ficha PHC

Uma nova proposta usa a casa do trabalhador como origem: `PE.MORADA`,
`PE.CODPOST` e `PE.LOCAL`, pela identidade `PE.PESTAMP` já resolvida no recibo.
Código postal que já contenha a localidade não a repete. Sem morada, a origem
fica por indicar; uma localidade isolada não é tratada como endereço de casa.
O leitor consulta apenas a ficha do trabalhador selecionado, após autorização
da empresa, sem acrescentar moradas ao painel mensal de todos os trabalhadores.

A matrícula vem de `PE2.MATRICULA`, com `PE2.PE2STAMP = PE.PESTAMP`.
O campo foi confirmado nas bases PHC configuradas; em HSOLS_PT, os 61
trabalhadores com recibos em setembro de 2026 tinham morada mas nenhum tinha
matrícula preenchida na consulta de 14/10/2026. Ausência de PE2/campo/valor é
explícita e permite indicação manual. Correspondências múltiplas são recusadas.
Não se deduz o proprietário da viatura nem o país de residência da nacionalidade.

Cada proposta guarda os valores originais, base, tabela, stamp, campos e instante
da leitura. São dados da **ficha atual**, cuja aplicação ao mês histórico exige
revisão. Valores mantidos têm proveniência PHC; correções têm proveniência
DECLARADO e conservam a fonte anterior. As deslocações continuam INFERIDAS.
Propostas existentes conservam os pressupostos guardados ao reabrir, sem serem
substituídos pela ficha atual. Uma mudança de morada/matrícula PHC usada nas
linhas impede validar a proposta antiga; é necessário gerar uma nova versão.

## Motor determinístico

`engine.py` não usa LLM, rede ou base de dados. Recebe fotografias dos dados
PHC/autos e pressupostos explícitos. Obras com vários autos são deduplicadas
por empresa/base/processo; um auto adicional não aumenta a frequência de visitas.

Origem e matrícula são pré-preenchidas pela ficha PHC, quando disponíveis.
Entradas humanas: eventuais correções à origem/viatura, país da origem, país
de referência das AC (PT por omissão), proprietário, obras selecionadas,
país/local de cada obra, distância de ida e de regresso, fonte da distância,
limite de deslocações por obra e mês, dias
excluídos, opção de fins de semana e eventuais valores unitários. Todos estes
pressupostos ficam guardados com autor e explicação. A fonte operacional é
exclusivamente o auto; os pressupostos humanos não são apresentados como
registos de presença.

Sem `max_trips` ou com valor `null`, o limite é o número de dias do calendário
disponível (com exclusões e opção de fins de semana), no máximo uma deslocação
KM por dia. Não existe um limite arbitrário de 10 nem cálculo a partir dos metros
executados. O campo «Limite opcional/mês» (`max_trips`, 0–31) permite indicar
uma restrição conhecida para a obra. A proposta guarda o limite efetivo e a
origem `max_trips_source = CALENDARIO` ou `DECLARADO`. Não representa visitas
comprovadas nem limita os dias de ajudas de custo. O calendário conjunto KM/AC
pode reduzir ainda mais as viagens possíveis. Versões antigas mantêm o limite
que foi guardado originalmente.

**Distâncias:** nesta entrega são declaradas com a respetiva referência; não
há geocodificação nem consulta automática a um serviço rodoviário. O cálculo
ida + regresso é determinístico. Regresso vazio usa a ida e marca expressamente
essa simetria como inferida. Distância em falta não é estimada a partir de
quilómetros PHC nem de nomes de localidades.

**KM:** procura limitada por obra e calendário, com programação dinâmica em
centésimos de km. Minimiza a diferença absoluta; em empate prefere ficar
abaixo do PHC, depois menos visitas e uma ordem estável. Até 40 obras e 6 000
estados por etapa. Se houver redução de estados, a proposta avisa que a pesquisa
é aproximada e não garante ótimo. Nunca aumenta um percurso ou cria uma linha
residual para atingir 100%.

**AC:** o país da obra é comparado com o país de referência das rubricas, que
é independente de uma base temporária no estrangeiro. Sem país declarado não
há atribuição automática de dias. Entre várias obras elegíveis usa-se a primeira
por empresa/código, com aviso para revisão. Distribuem-se dias e frações até à
capacidade do calendário, mantendo o saldo por reconciliar. Cada linha guarda
início/fim, quantidade, local, taxa e montante. Uma taxa única PHC pode ser
reutilizada; taxas diferentes não são arbitrariamente promediadas. A taxa PHC
não constitui confirmação de elegibilidade fiscal.

**Calendário conjunto:** segunda a sexta por omissão, com fins de semana
opcionais e exclusões explícitas. Não são consultados planeamento, férias ou
presenças. AC e KM podem partilhar uma data apenas na mesma obra. São rejeitadas
duas visitas KM, duas AC ou obras incompatíveis no mesmo dia. As datas continuam
inferidas. Uma correção humana fica declarada com autor e motivo, sem se tornar
prova documental de presença.

Somatórios usam `Decimal`. Diferença = mapa − PHC. Percentagem =
`max(0, 100 × (1 − abs(diferença)/abs(PHC)))`; PHC zero dá 100% apenas com mapa
zero. PHC desconhecido mantém diferença/percentagem desconhecidas. Um valor
negativo exige análise das regularizações e impede validação. Coincidência
numérica não aumenta o nível de confiança.

## Proveniência, histórico e validação

Há apenas duas tabelas novas:

- `GR_TRAVEL_MAP`: identidade empresa/base/trabalhador/mês e número da versão
  atual. `scope_hash` único impede dois mapas para a mesma identidade.
- `GR_TRAVEL_MAP_VERSION`: fotografia integral dos valores PHC originais,
  autos selecionados, pressupostos, linhas, reconciliação, versão do motor,
  evento, autor, instante UTC, motivo e decisão de validação. Cada evento
  acrescenta uma versão; não atualiza a anterior.

A gravação da versão e atualização do cabeçalho são uma transação. A comparação
atómica da versão recusa edições concorrentes com 409; UUIDs de operação evitam
repetições. Há hashes encadeados das versões para deteção de alterações e um
trigger SQL Server que impede UPDATE/DELETE das versões. Estes hashes não
substituem backups nem são uma assinatura digital qualificada.

Cada linha mantém `evidence_type = INFERIDO`, confiança BAIXA, fontes por campo
e `validation_state` separado. A primeira proposta e qualquer edição/regeneração
ficam POR_VALIDAR. VALIDADO exige permissão própria, confirmação explícita,
motivo, dados obrigatórios das linhas e nova conferência PHC/autos. Uma alteração
da fonte impede validar o estado antigo. A decisão não altera a origem inferida.
Categorias sem total PHC ficam explicitamente fora do âmbito da validação;
diferenças não nulas podem ser aceites conscientemente, mantendo o seu valor.

Uma edição de um mapa validado cria outra versão POR_VALIDAR; a versão validada
anterior continua consultável. Rejeição também é um evento, sem apagar linhas.
Se um recibo desaparecer ou o PHC ficar indisponível, as versões guardadas
continuam acessíveis com indicação de que os valores são históricos. A geração
e a validação ficam desativadas enquanto as fontes atuais não puderem ser lidas.
O acesso é revalidado para todas as empresas da evidência, inclusive em versões
históricas. Dados de empresas cujo acesso foi retirado não são devolvidos.

## Verificação

```sh
.venv/bin/python -B -m unittest discover -s tests -p 'test_gr_travel*.py'
```

Os testes usam base SQLite isolada para o mesmo código transacional: concorrência,
rollback integral, repetição de operações, versões, deteção de alterações,
ACL/CSRF e validação de fontes desatualizadas. O algoritmo é comparado com procura
exaustiva em casos pequenos. Incluem-se frações, calendários conjuntos, rubricas
em falta, diferenças positivas/negativas e imutabilidade das fotografias PHC.
A migração e o trigger destinam-se ao SQL Server e não são executados nesses testes.

O fluxo foi também exercitado no navegador com dados demonstrativos: proposta
684 → 676 km (−8, 98,83%), 4 → 4 dias de AC, edição de data, consulta da versão
original, validação e reabertura. Nenhum desses mapas de teste foi gravado no PHC
ou na base GR360 de produção.

## Próxima entrega

Geração de PDF a partir de uma versão validada e, se necessário, um adaptador
de distâncias rodoviárias com cache e proveniência. Não existem taxas fiscais
legais embutidas, certificação fiscal automática nem atribuição comprovada de
trabalhadores às obras nesta implementação.
