# Mapas de deslocações — PHC, reconstrução e versões

Painel `/mapas-deslocacoes` e editor `/mapas-deslocacoes/reconstrucao`, com link na
sidebar em contexto `client` / `GR360_CORE`. Administradores e developers têm
acesso; os restantes utilizadores precisam de `ACESSOS.TABELA = 'RH_MAPAS'`,
`CONSULTAR = 1`, além de uma associação ativa em `US_FE` à empresa consultada.
Permissão sobre obras ou autos não concede acesso a remunerações.

A leitura PHC não requer migração. A gravação de propostas requer executar
`migrations/gr_travel_maps.sql` explicitamente em **GR360_CORE**, durante a
instalação. O script recusa outras bases. Aplicado em 14/10/2026 à base
**GR360_CORE** da ligação `client` configurada na aplicação: tabelas
`GR_TRAVEL_MAP`, `GR_TRAVEL_MAP_VERSION` e trigger que impede alterar ou apagar
versões. Sem as tabelas, a consulta salarial continua disponível e a
interface permite calcular uma pré-visualização não guardada, sem possibilidade
de validação, e informa que a gravação está indisponível.

Não se criam tabelas ao abrir páginas nem se grava no PHC ou no planeamento.
As novas reconstruções automáticas consultam as afetações em HSOLS_MASTER,
sem importar/inicializar a aplicação legada. O acesso às fontes usa ligações de leitura com
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
- `POST /api/gr_mapas/prever`: calcula o calendário sem guardar nem validar.
- `POST /api/gr_mapas/propostas/<id>/editar`: nova versão com alterações humanas.
- `POST /api/gr_mapas/propostas/<id>/rejeitar`: nova versão rejeitada.
- `POST /api/gr_mapas/propostas/<id>/validar`: decisão humana explícita.

Os POST recebem `request_id` (UUID), `expected_version` (0 para o primeiro
mapa) e `reason`. A geração recebe empresa, ano, mês, chave do trabalhador,
empresas dos autos e `inputs`. `mode: "AUTOMATIC"` seleciona o calendário;
o contrato anterior mantém-se por compatibilidade. Os dados PHC e dos autos são sempre relidos no
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

## Planeamento das equipas e evidência adicional dos autos

As novas propostas automáticas usam `HSOLS_MASTER.U_TEAM` para ligar o número
PHC e a base de origem (`NO` + `ORIGEM`) à equipa, dentro de `DATAINI`/`DATAFIM`.
`U_PLANO` liga essa equipa (`FREF`) à obra (`PROCESSO`) numa data concreta.
Fim de pertença nulo ou 1900-01-01 significa intervalo aberto. Não há associação
por semelhança de nomes, nem por número de trabalhador sem empresa de origem.

O `OPCSTAMP` liga a obra de HSOLS_MASTER às fichas OPC das empresas selecionadas
e autorizadas. Isto permite, por exemplo, ligar HS1822 a PT1822 quando partilham
esse identificador, sem presumir que códigos com o mesmo sufixo são equivalentes.
Cópias com o mesmo stamp em várias empresas representam uma obra física; a ficha
da empregadora tem preferência. Duplicados dentro da mesma empresa são recusados.

O calendário apresenta equipa/obra em cada data, mesmo sem viagem proposta.
Só se propõem percursos e AC nas datas associadas; obras planeadas sem autos
positivos podem entrar, com aviso de ausência dessa evidência de produção.
Sem ligação utilizável não há fallback silencioso para obras arbitrárias dos autos.
Conflitos entre equipas, `U_TEAM.AUSENTE`, e obras sem ligação segura bloqueiam
os dias afetados. `U_AUSENCIAS` só é associado quando V_PE dá uma identidade única
para o número, com base e PESTAMP correspondentes; nos restantes casos avisa-se
para confirmar exclusões. Não são guardados motivos pessoais das ausências.

O mapa guarda a fotografia dos registos, referências, bloqueios e fingerprint.
Validar relê estas fontes; uma mudança exige reconstruir. A origem dos percursos
continua INFERIDO, com associação de equipa/data documentada como PLANEAMENTO.
Nem o planeamento nem a aprovação tornam a viagem comprovada.

A empresa dos autos pode diferir da empregadora, sempre dentro das empresas
autorizadas. São consultadas séries `TS` com nome exato, sem diferenças de acento
ou caixa, `Situation de Travaux` e `Auto de Medição`. São excluídos documentos
anulados (`BO2.ANULADO`) e não se incluem séries de crédito/subempreitada.

Os documentos são selecionados por `BO.DATAOBRA`. Uma linha atual `BI.QTT > 0`
ou `BI.ETTDEB > 0` sinaliza medição positiva; não se somam campos acumulados.
Os autos sem medição positiva continuam visíveis, mas não acrescentam evidência
de produção. A data documental ainda não confirma o período real da produção.

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

A matrícula particular vem de **`PE.U_MATPRO`**, com fallback para
`PE2.MATRICULA` (`PE2.PE2STAMP = PE.PESTAMP`). A leitura de 14/10/2026 confirmou
`U_MATPRO` preenchido em 34 dos 61 trabalhadores com recibos de setembro em
HSOLS_PT; `PE2.MATRICULA` não tinha valores nesse conjunto. Valores divergentes
geram aviso e a proveniência identifica exatamente o campo escolhido. Campos
ou valores ausentes permitem indicação manual. Correspondências múltiplas são recusadas.
Não se deduz o proprietário da viatura nem o país de residência da nacionalidade.

Cada proposta guarda os valores originais, base, tabela, stamp, campos e instante
da leitura. São dados da **ficha atual**, cuja aplicação ao mês histórico exige
revisão. Valores mantidos têm proveniência PHC; correções têm proveniência
DECLARADO e conservam a fonte anterior. As deslocações continuam INFERIDAS.
Propostas existentes conservam os pressupostos guardados ao reabrir, sem serem
substituídos pela ficha atual. Uma mudança de morada/matrícula PHC usada nas
linhas impede validar a proposta antiga; é necessário gerar uma nova versão.

## Motor determinístico

`engine.py` e `itinerary.py` recebem fotografias dos dados PHC/autos e dos
percursos; não usam LLM, rede ou base de dados. `distances.py` trata apenas dos
serviços geográficos. Obras com vários autos são deduplicadas por empresa/base/
processo; metros executados e número de autos não determinam visitas.

O editor apresenta todos os dias do mês. A seleção de empresas fica em
`localStorage`, por utilizador e navegador, filtrada pelas permissões atuais.
O botão de reconstrução relê os autos e o planeamento, localiza as obras
associadas ao trabalhador e calcula os percursos. A morada e a matrícula vêm do PHC;
o proprietário requer confirmação. País da casa/referência AC, dias excluídos,
taxas e política de regresso são pressupostos ajustáveis. Fins de semana com
afetação registada são considerados; exclusões explícitas prevalecem.
Não existe campo «Máx. visitas» neste fluxo. O modal do detalhe mensal e o
editor de um dia ficam centrados no ecrã.

Durante a reconstrução, a interface apresenta a fase atual, a obra/morada em
curso, os locais verificados/encontrados/por resolver e o tempo decorrido. A
barra mede locais verificados durante a localização; nas fases sem um total
mensurável (percursos, combinações, gravação) fica indeterminada. Não representa
uma estimativa de tempo nem a percentagem de reconciliação com o PHC.

Os POST de geração e pré-visualização aceitam `Accept: application/x-ndjson`
para transmitir eventos `progress`, seguidos de um único `result` ou `error`.
Mantêm autenticação, ACL por empresa, CSRF, versões e idempotência. Clientes
JSON continuam a receber a resposta anterior. O progresso pertence ao pedido,
sem tabela, fila ou processo em segundo plano; `stream_with_context` conserva
o contexto de autorização. `X-Accel-Buffering: no` evita buffering em proxies
compatíveis; outros proxies também devem permitir streaming neste endpoint.
Uma ligação interrompida não é apresentada como sucesso: o utilizador deve
atualizar os dados para verificar se a versão chegou a ser guardada.

### Localização e distâncias

Por omissão usam-se [Photon](https://github.com/komoot/photon) para localizar
moradas e [OSRM](https://project-osrm.org/docs/v5.24.0/api/) para a matriz
rodoviária dirigida. Não exigem chave nesta integração. São serviços públicos
sem garantia de disponibilidade. Configuração Flask ou ambiente permite trocar
`GR_TRAVEL_PHOTON_URL` e `GR_TRAVEL_OSRM_URL`, incluindo instâncias próprias;
estes URLs nunca vêm do pedido do navegador. A política do serviço escolhido
deve ser adequada ao volume da instalação.

Só moradas/locais são enviados ao Photon e coordenadas ao OSRM; nomes,
identificadores de trabalhadores e salários não são enviados. Há identificação
da aplicação, atribuição OpenStreetMap na interface, chamadas geográficas
sequenciais, intervalo mínimo de 1,05 s entre consultas Photon por processo,
timeouts e pausa de 120 s após falha de um fornecedor. A localização de um
conjunto tem limite de 90 s; repetições aproveitam os resultados já obtidos.
Cache em `instance/gr_travel_geo`, durante 30 dias, com permissões privadas e
substituição atómica. Não cria tabelas. O volume deve manter-se moderado;
instalações com vários processos ou maior utilização precisam de um serviço
adequado e controlo global de pedidos.

Correspondências ambíguas ou com pouca semelhança são recusadas. Se uma morada
não for encontrada, tenta-se a localidade do registo com o mesmo fornecedor:
o resultado fica explicitamente `LOCALIDADE`, com a morada não resolvida na
proveniência. Nunca se usa a antiga localidade PHC para uma morada alterada pelo
utilizador.

Se o fornecedor estiver indisponível ou não resolver o local, `postal.py` procura
no catálogo público [GeoNames](https://download.geonames.org/export/zip/readme.txt),
guardado localmente. Descarrega apenas ficheiros públicos por país; não envia
moradas ou dados de trabalhadores. Os países de pesquisa são PT, FR, ES, DE, BE
e LU, configuráveis por `GR_TRAVEL_POSTAL_COUNTRIES` (ISO2 separados por vírgulas).
O país explícito restringe a pesquisa; sem país exige compatibilidade entre
código postal e nome do local. Sem código postal, só pesquisa a localidade
explicitamente registada, nunca uma cidade deduzida do nome de uma rua.
Correspondências ambíguas ou em países diferentes são recusadas.

Os pontos GeoNames são sempre `CODIGO_POSTAL`/`LOCALIDADE`, nunca a posição
comprovada de uma casa ou obra. A interface assinala os troços afetados como
aproximados. A fonte guarda país, código, local, coordenadas, precisão reportada,
ficheiro, hash SHA-256, data de descarga e atribuição CC BY 4.0. Os ZIP públicos
ficam em `instance/gr_travel_geo/postal`, com limite de tamanho, validação antes
da substituição e sem extrair caminhos do arquivo. Atualizam-se após 30 dias;
se a atualização falhar, a versão anterior continua utilizável com
`cache_stale: true`. Há cache em memória por processo durante uma hora.

Coordenadas declaradas permitem corrigir o ponto e exigem país. Se nenhuma
alternativa resolver o local, este fica excluído e os respetivos km por reconciliar.

Os sentidos de ida e regresso são calculados separadamente, usando a distância
rodoviária do percurso mais rápido, com metros/segundos originais e arredondamento
a 0,01 km. Células sem percurso são excluídas; não há distância em linha reta,
simetria automática nem correção baseada no total PHC. Pontos a mais de 2 km da
rede rodoviária são excluídos. Cada versão guarda os locais e os troços usados,
fornecedor, instante, precisão, fontes e versão do motor; não duplica toda a
matriz de alternativas não usadas.

Na verificação de 14/10/2026 o OSRM respondeu e a alternativa postal produziu,
com fontes reais do caso reportado, 445,83 dos 446 km e 15 dos 15 dias de AC.
Foram considerados 48 obras, resolvidos 36 locais aproximados (incluindo a casa)
e excluídos 13 locais sem dados suficientes. Estes números verificam o fluxo,
não comprovam deslocações, presença ou precisão das moradas.

Cada proposta automática inclui `result` e diagnósticos de locais e percursos.
Sem linhas e com valores PHC positivos, o resultado é `BLOCKED`, com explicação
visível e os locais por resolver abertos. Resultados incompletos/aproximados são
`PARTIAL`. A interface deixa de apresentar uma pré-visualização vazia como
calculada com sucesso e desloca a vista para o resultado após reconstruir.
A indisponibilidade do cálculo rodoviário não impede propor AC quando o local
e o país já estão identificados.

### Combinações e calendário

Nas novas propostas `planning-calendar-v2`, `scheduled.py` procura combinações
de viagens já atribuídas a datas elegíveis, em vez de escolher obras livremente
e espalhar visitas pelo mês. Programação dinâmica por data/total/base impede
sobreposições e mudanças de base sem percurso. Limites: 80 alternativas por dia
e 1 600 estados por camada; cortes são assinalados. Um regresso diferido não pode
atravessar ausências, dias úteis sem associação ou afetações a outra obra.
Transferências entre obras exigem destino registado e origem apoiada no mesmo
dia ou na afetação imediatamente anterior; a presença inicial continua inferida.
As AC só usam datas e países de obras associadas, compatíveis com os percursos;
o excedente PHC fica por reconciliar. Edições devem respeitar estas ligações.

Quando existe uma única obra associada ao trabalhador, as obras de outras equipas
registadas nas mesmas datas, dentro das empresas autorizadas, entram como opções
de visita. O motor pode propor A → B → A no mesmo dia, ou incorporar essa visita
num percurso desde casa. Essas linhas têm `hypothesis=true`, confiança BAIXA e
referências separadas à equipa própria e à outra equipa; não alteram os registos
originais do trabalhador. As AC continuam limitadas às obras da sua própria equipa.
Entre soluções com a mesma diferença, preferem-se menos troços/viagens e datas
distribuídas pelo calendário. Não existe um número de visitas derivado dos metros
produzidos, nem um limite arbitrário de visitas por obra.

Para totais maiores, também se considera casa em Portugal → obra no estrangeiro
→ casa, com distâncias rodoviárias calculadas. Um troço superior ao limite diário
de condução é repartido por dias consecutivos elegíveis. Cada troço mantém os km
integrais da rota e a distribuição diária soma exatamente esse valor. Os dias
de condução e a distribuição diária são inferidos; não se inventam locais de
pernoita. Dias intermédios sem local conhecido não recebem AC automaticamente.
Entre viagens internacionais equivalentes, prefere-se a ida no início e o regresso
no fim do período disponível. As AC dessa obra ficam dentro da permanência proposta.
Ida e regresso têm de caber no mês e no calendário disponível. Datas/distâncias
destes troços repartidos são alteradas por nova reconstrução; exclusão, motivo,
taxa, matrícula e proprietário continuam editáveis com histórico.

Visitas a outras equipas e viagens internacionais desde Portugal aparecem como
**HIPÓTESE — sem registo da deslocação**. Para validar é necessário confirmar
explicitamente que ocorreram, ou excluí-las. A validação guarda os identificadores
das linhas confirmadas e nunca as converte em evidência COMPROVADA.

As regras seguintes descrevem o motor histórico `autos-calendar-v1`, conservado
para consultar e editar versões anteriores e para o contrato manual legado:

**KM:** programação dinâmica em centésimos de km, limitada pelo calendário e
por um máximo diário de condução (10 h por omissão, pressuposto ajustável,
não uma regra legal). Tenta primeiro casa → obra → casa. Se restar diferença,
considera casa → A → B → A → casa, com troços rodoviários reais. Para totais
baixos, considera A → B → A, mantendo uma única obra-base e avisando que a
presença inicial e a chegada a essa obra não estão demonstradas.

Minimiza a diferença absoluta; em empate prefere não exceder o PHC, menos
troços entre obras, menos viagens e ordem estável. Até 99 obras, 100 alternativas,
1 600 estados por camada e oito bases nas transferências locais. Limites de
pesquisa geram aviso de solução aproximada, sem garantia de ótimo. Nunca se
cria uma linha residual nem se altera a distância para atingir 100%.

As viagens completas são distribuídas pelos dias disponíveis. Conforme a
política escolhida e o tempo de condução, a ida e o regresso podem ocorrer no
mesmo dia ou em dias diferentes. `journey_id`, ordem dos troços e percurso
ligam os regressos às idas. O editor de um dia mostra também os troços ligados
noutras datas. Alterar datas cria nova versão; regressos anteriores à ida,
viagens sobrepostas ou exclusão de apenas parte de uma viagem são recusados.
O calendário mostra a permanência inferida entre ida e regresso.

**AC:** o país localizado/declarado da obra é comparado com o país de referência
da rubrica, sem o inferir pela empresa ou nacionalidade. Usa primeiro dias e
obras compatíveis com as viagens. Quando é necessária outra permanência, reserva
um bloco dos últimos dias disponíveis e recalcula os KM nos dias restantes,
assinalando que a deslocação até essa obra continua por confirmar. Entre obras
elegíveis a escolha é determinística e inferida. Dias/frações sem capacidade
ficam por reconciliar. Cada linha guarda início/fim, quantidade, local, taxa e
montante; taxas únicas PHC podem ser reutilizadas, sem médias de taxas diferentes.
A taxa PHC não confirma elegibilidade fiscal.

Segunda a sexta por omissão, com fins de semana opcionais e exclusões explícitas.
Não se consultam planeamento, férias, feriados ou presenças. O auto apenas torna
a obra candidata no mês; não prova atividade num dia. AC e KM partilham datas
apenas em obras compatíveis com o percurso/permanência; duas AC no mesmo dia são
recusadas. Alterações humanas ficam declaradas com autor e motivo, sem converter
inferências em prova. O motor anterior continua disponível para consultar e
editar as versões históricas, preservando os respetivos pressupostos.

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

Cada linha mantém `evidence_type = INFERIDO`, fontes por campo e confiança MEDIA
quando apoiada na equipa/data, ou BAIXA nas hipóteses adicionais e no motor legado,
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
684 → 676 km (−8, 98,83%) no motor anterior e 684 → 684 km com dois troços reais
de 4 km entre obras no calendário automático; 4 → 4 dias de AC. Verificaram-se
regresso noutra data, edição, consulta da versão original, validação, empresas
memorizadas e centragem do modal. Nenhum desses mapas de teste foi gravado no PHC
ou na base GR360 de produção.

O fluxo com planeamento foi verificado com dados fictícios no navegador: duas
visitas a outra equipa assinaladas como hipóteses, confirmação obrigatória para
validar, origem INFERIDO mantida após validação, e viagem internacional de 3 000 km
com ida/regresso de três dias cada. A integração também foi verificada por leitura
real, sem guardar mapas, incluindo a conferência das fontes atuais. Os locais
aproximados e por resolver continuam assinalados.

## Próxima entrega

Geração de PDF a partir de uma versão validada. Não existem taxas fiscais
legais embutidas, certificação fiscal automática nem atribuição comprovada de
trabalhadores às obras nesta implementação.
