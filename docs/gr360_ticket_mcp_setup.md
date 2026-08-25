# Conector GR360 Tickets para Codex e ChatGPT

## Arquitetura isolada

O MCP não é carregado pelo Flask nem pelo Waitress da aplicação. Existem três componentes separados:

1. `GR360 Application`, porta 8001: aplicação e API autenticada de tickets;
2. `GR360 Tickets MCP`, porta local 8002: adaptador MCP sem acesso direto à base de dados;
3. `GR360 Nginx`: publica `/mcp/gr360-tickets/` e encaminha apenas esse caminho para a porta 8002.

Uma falha ou dependência em falta no MCP não impede o arranque da aplicação principal.

## Endpoint e ferramentas

- URL pública: `https://app.gr360flooringsystems.com/mcp/gr360-tickets/`
- Transporte: Streamable HTTP
- Autenticação: Bearer token da credencial API `mickael-codex`

Ferramentas:

- `listar_tickets`
- `consultar_ticket`
- `criar_ticket`
- `atualizar_seguimento`

O Bearer recebido pelo MCP é encaminhado para a API. A validação da credencial, permissões,
idempotência, acesso à `GR360_CORE` e auditoria continuam centralizados na API Flask.

## Instalação no Windows

Depois de atualizar o repositório, executar numa PowerShell de administrador:

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\APP_WEB\tools\install_gr360_ticket_mcp_service.ps1
```

O script cria o ambiente virtual isolado `.venv-mcp`, instala apenas as dependências de
`requirements-mcp.txt` e cria o serviço automático `GR360 Tickets MCP`. Não altera o ambiente da
aplicação, `GR360 Application` nem `GR360 Nginx`.

Inserir o conteúdo de `tools/nginx_gr360_ticket_mcp_location.conf` dentro do bloco `server` de
`app.gr360flooringsystems.com`, validar com `nginx -t` e só depois recarregar o Nginx.

## Ativação no ChatGPT

Criar uma app MCP privada no workspace com a URL pública acima, efetuar o scan das ferramentas,
rever as ações de escrita e disponibilizar a app ao Mickael. Este registo é feito por um
administrador/owner ou por um utilizador autorizado em developer mode. Criar o endpoint no servidor
não adiciona automaticamente ferramentas a um Project existente.

## Codex com ambiente de execução

Instalar o plugin `gr360-tickets` e guardar o token apenas no segredo de ambiente
`GR360_TICKETS_API_TOKEN`. O plugin lê esse segredo através de `bearer_token_env_var`; o valor não
fica no repositório nem no prompt.

## Regras de utilização

Antes de criar um ticket, pesquisar tickets semelhantes. Usar uma referência externa estável e
incluir no prompt técnico o contexto, passos de reprodução, comportamento atual e esperado,
evidências, critérios de aceitação e testes.

Pedir confirmação antes de criar tickets ou atualizar seguimentos. Nunca mostrar nem colocar tokens,
passwords ou credenciais SQL em mensagens, prompts ou relatórios.
