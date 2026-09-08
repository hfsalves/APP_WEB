# Dicionário Funcional GR360

**Versão:** 0.1  
**Âmbito:** StationZero e circuitos PHC do Grupo GR360  
**Objetivo:** permitir consulta, reconciliação e interpretação de informação sem atribuir permissões de alteração de dados produtivos.

Este documento descreve a implementação efetiva do Grupo, e não o modelo teórico do PHC. Deve ser mantido juntamente com o mapa de integrações em [PHC_STATIONZERO_GOVERNANCE_P0_1.md](PHC_STATIONZERO_GOVERNANCE_P0_1.md).

## 1. Regras de consulta

- **PHC** é a referência para entidades comerciais, dossiers, contabilidade, tesouraria, obras e documentos financeiros, salvo indicação contrária.
- **StationZero** é a referência operacional para despesas submetidas, Documents AI, widgets, configurações de utilização e alguns processos de planeamento e oficina.
- O valor apresentado num ecrã pode ser calculado ou agregado. Em caso de reconciliação, deve confirmar-se sempre a origem indicada no próprio módulo e, se necessário, o registo PHC de origem.
- A consulta é feita com perfis de leitura e `SELECT`. Não estão incluídos alterações de parametrização, execução de procedures, triggers, jobs, ou escrita em dados produtivos.
- Dados pessoais, salários, IBAN e anexos exigem necessidade funcional e aplicação das regras de confidencialidade aplicáveis.

## 2. Entidades e bases PHC

| Entidade na StationZero | Base PHC | Nota funcional |
| --- | --- | --- |
| Betãoconcept | `HSOLS_PT` | Operação portuguesa. |
| GR360 | `GR360` | Entidade central do Grupo. |
| HSOLS DE | `HSOLS_DE` | Operação alemã. |
| HSOLS France | `HSOLS_FR` | Operação francesa. |
| INTERSOL SAS | `INTERSOL` | Operação francesa Intersol. |
| MG SOLERAS | `HSOLS_ES` | Operação espanhola. |
| HSOLS Maroc | `HSOLS_MA` | Operação marroquina. |
| Serviços centrais PHC | `HSOLS_MASTER` | Informação e automatismos partilhados quando explicitamente identificados. |
| Aplicação StationZero | `GR360_CORE` | Utilizadores, menus, acessos, widgets, dados próprios da aplicação e catálogo de integrações. |

## 3. Mapa funcional por área

| Área StationZero | Finalidade | Fonte de referência | Objetos PHC principais | Regras de leitura |
| --- | --- | --- | --- | --- |
| Dashboard | Indicadores e atalhos por utilizador | StationZero e fontes dos widgets | Varia conforme o widget | Um indicador deve identificar período, entidade e origem antes de ser usado para controlo. |
| Monitor de Trabalho | Acompanhamento de trabalho operacional | StationZero | Varia consoante a tarefa | Não é uma fonte contabilística. Deve ser reconciliado com o dossier ou obra de origem. |
| Clientes | Consulta e gestão de entidades de clientes | PHC | `CL`, extensões de cliente quando aplicável | A chave técnica é `CLSTAMP`; o número de cliente e NIF são chaves funcionais de controlo. |
| Fornecedores | Consulta e gestão de fornecedores | PHC | `FL` | Validar entidade PHC e NIF antes de cruzar fornecedores entre países. |
| Artigos | Catálogo de artigos, referências e famílias | PHC | `ST`, `STOBS`, `FREF` quando aplicável | Nem todos os mappings de artigos/referências estão ativos; confirmar sempre a base e a origem. |
| Centros de custo | Estrutura analítica de custos | PHC | `CCT` e campos de centro de custo nos dossiers/linhas | O centro de custo é uma dimensão de análise e pode ser obrigatório por circuito. |
| Obras | Consulta da obra, dados de planeamento e manutenção | PHC, publicado/controlado na app | `OPC`, extensões e informação de planeamento | `PROCESSO` é a chave funcional da obra. `U_PLAN` indica elegibilidade para planeamento. |
| Equipas e encarregados | Equipas operacionais e responsáveis | PHC / StationZero | `FREF`, `CT` | A associação deve ser lida no contexto da obra, período e planeamento. |
| Planeamento | Planeamento diário, macro, equipas e produção | StationZero com origem PHC | `OPC`, linhas de Estudo e Execução e dados de planeamento | Uma obra só apresenta postos/m² quando as linhas de orçamento/Estudo e Execução chegam à fonte de planeamento. |
| Folha mensal Intersol | Consolidação mensal para salários/produção Intersol | StationZero e dados operacionais | Dados de planeamento e colaboradores | É uma camada de apuramento; confirmar período, equipa e regras salariais antes de exportar ou fechar. |
| Orçamentos | Lista, detalhe, linhas, estrutura de custos e ciclo comercial | PHC | `BO` (cabeçalho), `BO2` (extensão), `BI` (linhas), `OCI` (estrutura de custos) | O dossier é identificado por `BOSTAMP`; as linhas por `BISTAMP`. Séries relevantes: Devis, Étude et Exécution e Devis Perdu. |
| Autos de clientes | Medições/autos de obra para cliente | PHC | Dossiers e linhas PHC do circuito de autos | Confirmar obra, período, estado e ligação ao dossier comercial. |
| Autos de subempreitada | Medições de subempreiteiros | PHC | Dossiers e linhas PHC associados a contratos SE | Os contratos `SE` são contratos de subempreitada. A leitura deve distinguir contrato, auto, faturação e estado. |
| Compras | Consulta de dossiers de compra | PHC | Dossiers internos `BO`/`BO2` e linhas `BI` | BC, BL e PF são dossiers ligados por `OBISTAMP` na linha de destino. |
| BC, BL e pré-faturas | Cadeia de encomenda, guia e fatura de fornecedor | PHC | `BO`, `BO2`, `BI` | A ligação BC -> BL e BL -> PF é feita pelo `OBISTAMP` da `BI` de destino. Linhas com quantidade satisfeita devem ser avaliadas com cuidado. |
| Faturação | Faturas, notas de crédito e documentos de venda | PHC | `FT` e tabelas relacionadas | A fonte contabilística e fiscal é o PHC. Confirmar série, estado, data e entidade. |
| Recibos e recebimentos | Liquidação de clientes | PHC | Dossiers e movimentos de tesouraria/recibos | A análise deve distinguir emissão, recebimento, anulação e reconciliação. |
| Agenda de tesouraria | Previsão e controlo de tesouraria | PHC | Documentos de compras, vendas e tesouraria | É uma visão de controlo; validar documento, vencimento, entidade e estado de liquidação. |
| Reconciliação bancária | Conciliação de movimentos bancários | PHC / StationZero conforme o fluxo | Movimentos e extratos associados | Não alterar ou validar reconciliações fora do circuito autorizado. |
| SAF-T | Preparação/emissão de ficheiros fiscais | PHC | Dados fiscais e contabilísticos PHC | Processo sensível: apenas consulta e preparação; emissão final segue o procedimento fiscal definido. |
| Frota e oficina | Viaturas, motoristas, manutenção e intervenções | PHC e StationZero | `VA`, `MO` e objetos de oficina | A importação de viaturas está configurada; a chave imutável deve ser validada antes de qualquer fluxo de retorno. |
| Registos de produção | Central, camião, bomba e materiais de obra | PHC / StationZero | `RCENTRAL`, `RCAMIAO`, `RBOMBA`, `OPCMAT` | Ler sempre com obra, data, material e unidade associados. |
| Despesas | Submissão e processamento de despesas de colaboradores | StationZero; publicação controlada no PHC | Dados de despesas na app; Notes de Frais no PHC | Depois de processada, uma despesa deixa de ser editável pelo colaborador. Despesas DKV seguem o circuito específico de Notes de Frais com valores contabilísticos definidos para esse tipo. |
| Recibos de colaboradores | Consulta de recibos disponibilizados ao colaborador | StationZero / PHC | Dados de recibos e anexos | Acesso limitado ao colaborador e perfis de RH autorizados. |
| Férias | Marcação e aprovação de férias | StationZero | Dados de férias e colaboradores | A aprovação tem ACL explícita, inclusive para administradores da app. |
| Documents AI | Receção, extração, classificação, associação e validação documental | StationZero | Anexos e publicação para PHC quando aplicável | As vistas `home`, `management` e `accounting` têm permissões próprias e podem ter acesso por entidade. |
| Anexos | Consulta de documentos associados a registos | PHC / StationZero | `ANEXOS` e tabela de destino | Verificar sempre se o ficheiro existe e se o caminho/anexo é acessível. Anexar um registo não garante que o ficheiro esteja disponível. |
| CRM | Pipeline, entidades e importação comercial | StationZero e importação PHC | Objetos CRM e `CL` quando aplicável | Distinguir dados de prospeção de cliente PHC efetivo. |
| Mapa de gestão | Controlo de gestão e análise transversal | StationZero e fontes PHC | Varia por indicador | Cada indicador deve ser lido com origem, período, entidade e regra de cálculo visíveis. |

## 4. Dossiers internos PHC: convenções relevantes

| Conceito | Regra no Grupo |
| --- | --- |
| Cabeçalho de dossier | `BO`; a chave técnica é `BOSTAMP`. |
| Extensão de dossier | `BO2`; é usada para informação complementar e estados específicos do circuito. |
| Linha de dossier | `BI`; a chave técnica é `BISTAMP`. |
| Ligação entre dossiers | Em cadeias BC -> BL -> PF, a origem é ligada no `OBISTAMP` da linha `BI` de destino. |
| Quantidade satisfeita | `BI.QTT2` deve ser inserida a zero nos desenvolvimentos de criação de dossiers, salvo uma regra funcional expressa em contrário. |
| Estrutura de custos | `OCI` contém componentes de custo das linhas de orçamento. Componentes técnicos especiais podem ter tratamento distinto na apresentação. |
| Orçamento ganho | Um Devis ganho pode criar obra nova ou ser associado a obra existente como aditamento. O destino é a série Étude et Exécution. |
| Orçamento perdido | O dossier é encaminhado para a série Devis Perdu. |

## 5. Integrações e fontes de verdade

| Domínio | Sentido em produção | Chave/critério principal | Nota |
| --- | --- | --- |
| Clientes | PHC <-> StationZero | `CLSTAMP` | Mapping ativo; devem ser definidas regras de conflito por campo. |
| Obras/processos | PHC -> StationZero | `PROCESSO` | Sincronização operacional via worker/fila; o estado apresentado no Database Manager deve refletir a execução real. |
| Viaturas | PHC -> StationZero | Matrícula em uso; `VASTAMP` transportado | A chave de negócio deve ser confirmada antes de qualquer escrita de retorno. |
| Fornecedores | Configurado, não ativo | A confirmar | Não assumir sincronização automática entre PHC e app. |
| Artigos e referências | Configurado, não ativo | A confirmar | Não assumir sincronização automática entre PHC e app. |
| Despesas | StationZero -> PHC, quando processadas | Registo de despesa e colaborador/entidade | A publicação obedece ao tipo de despesa e à entidade selecionada. |
| Documents AI | StationZero -> PHC, quando aplicável | Documento, entidade e associação | A validação de documento deve preceder qualquer publicação financeira. |

## 6. Consultas de validação seguras

As consultas devem ser sempre `SELECT`, executadas na base da entidade correta e com filtros explícitos. O conjunto operacional mínimo deverá cobrir:

1. Localização de obra por `PROCESSO`, descrição e entidade.
2. Localização de dossier por série, número, ano e `BOSTAMP`.
3. Linhas de dossier por `BISTAMP`, referência, designação, quantidade, preço e centro de custo.
4. Cadeia BC -> BL -> PF por `BI.OBISTAMP`.
5. Cliente/fornecedor por número, NIF e `CLSTAMP`/chave de fornecedor.
6. Estado de faturação, recebimentos e pagamentos por entidade, data e documento.
7. Estrutura de custos de orçamento por linha e componentes `OCI`.
8. Despesa por colaborador, entidade, estado de processamento e ligação a Notes de Frais.
9. Anexos por chave do registo e verificação de disponibilidade do ficheiro.

As versões SQL concretas destas consultas devem ser mantidas num repositório controlado, com indicação da base, parâmetros necessários, colunas devolvidas e exemplos de interpretação.

## 7. Administração e limites

- Os perfis administrativos da StationZero dão visibilidade sobre menus e funcionalidades, mas alguns módulos têm ACL própria: férias, Documents AI, acessos por entidade e widgets são exemplos relevantes.
- As permissões devem ser revistas por necessidade funcional, sobretudo em RH, tesouraria, documentos e dados bancários.
- Acesso administrativo à aplicação não equivale a credenciais administrativas do SQL Server ou do PHC.
- Alterações de dados, parametrizações, jobs, triggers, procedures ou integrações continuam a exigir intervenção técnica e registo da alteração.

## 8. Manutenção do documento

Cada novo desenvolvimento com impacto em dados deve atualizar este dicionário com: ecrã afetado, base/tabelas de origem, chave de ligação, direção de integração, regras funcionais e exceções. O objetivo é que a documentação permaneça uma referência de operação e controlo, não um retrato histórico desatualizado.
