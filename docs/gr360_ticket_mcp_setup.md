# Conector GR360 Tickets para Codex e ChatGPT Work

## Endpoint

- MCP remoto: `https://app.gr360flooringsystems.com/mcp/gr360-tickets/`
- Transporte: Streamable HTTP
- Autenticação: Bearer token da credencial `mickael-codex`

O endpoint publica quatro ferramentas:

- `listar_tickets`
- `consultar_ticket`
- `criar_ticket`
- `atualizar_seguimento`

## Codex com ambiente de execução

Instalar o plugin `gr360-tickets` e guardar o token apenas no segredo de ambiente
`GR360_TICKETS_API_TOKEN`. O plugin lê esse segredo através de
`bearer_token_env_var`; o valor não fica no repositório nem no prompt.

## Project do ChatGPT Work

Um Project do ChatGPT Work sem ambiente Codex não consegue ler variáveis locais. Nesse caso, um
administrador do workspace deve registar o endpoint acima como conector privado/MCP e configurar a
autenticação no próprio conector. Depois, o conector `GR360 Tickets` deve ser disponibilizado ao
Project do Mickael.

Se a política do workspace exigir OAuth em vez de Bearer estático, deve ser acrescentada uma camada
OAuth ao endpoint antes da ativação no ChatGPT Work. O token nunca deve ser colado numa conversa.

## Prompt do projeto do Mickael

Trabalha como responsável de controlo de gestão da GR360 e usa o conector GR360 Tickets para
comunicar ocorrências à equipa de desenvolvimento.

Antes de criar um ticket, pesquisa tickets semelhantes. Quando criares um ticket, usa uma referência
externa estável e inclui no prompt técnico o contexto, os passos de reprodução, o comportamento atual,
o comportamento esperado, os dados e ecrãs envolvidos, evidências, critérios de aceitação e testes.

Analisa também tickets tratados que aguardem validação do cliente. Reproduz o comportamento na
StationZero, valida os dados disponíveis e regista o resultado através do seguimento. Não alteres o
pedido nem o prompt original. Só marques um ticket como tratado quando estiver efetivamente resolvido.

Pede sempre confirmação antes de criar um ticket ou atualizar o seu seguimento. Nunca peças, mostres
ou coloques tokens, passwords ou credenciais SQL em mensagens, prompts ou relatórios.
