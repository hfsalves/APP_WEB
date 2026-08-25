# API de tickets GR360

Esta API permite que integrações externas criem tickets na `GR360_CORE.dbo.TK` e acompanhem o respetivo estado sem receberem acesso SQL à aplicação.

## Isolamento e segurança

- A API usa sempre o bind `client` e valida que `DB_NAME()` é `GR360_CORE`.
- A autenticação é feita por `Authorization: Bearer <token>`.
- O token é apresentado apenas na criação da credencial. Na base fica apenas SHA-256.
- Cada cliente consulta, por defeito, apenas os tickets que criou.
- A credencial do Mickael pode consultar todos os tickets para apoiar a análise transversal.
- Apenas credenciais com `PODE_ATUALIZAR = 1` podem escrever o seguimento do cliente.
- A atualização preserva sempre o pedido, a descrição e o `PROMPT_HUGO` originais.
- `referencia_externa` torna a criação idempotente: repetir a mesma referência devolve o ticket existente.
- Todos os tickets criados pela API ficam associados à HSOLS France (`FEID = 1`); o cliente não escolhe o FEID.

## Configuração

- `GR360_TICKET_API_ENABLED`: ativa/desativa a API. Valor predefinido: `1`.
- `GR360_TICKET_API_EXPECTED_DATABASE`: base obrigatória. Valor predefinido: `GR360_CORE`.
- `GR360_TICKET_API_FEID`: entidade fixa dos tickets. Valor predefinido: `1` (HSOLS France).
- `GR360_TICKET_MCP_ENABLED`: publica ou oculta o conector MCP. Valor predefinido: `0`; ativar apenas depois de instalar as dependências.
- `GR360_TICKET_MCP_HOST`: hostname público autorizado para o conector. Valor predefinido: `app.gr360flooringsystems.com`.

Aplicar primeiro `migrations/gr360_ticket_api.sql` na `GR360_CORE`.

## Endpoints

- `POST /api/gr360/tickets`: cria um ticket.
- `GET /api/gr360/tickets?status=pending&limit=50`: lista tickets da credencial.
- `GET /api/gr360/tickets/<numero>`: consulta o ticket completo e o seguimento.
- `PATCH /api/gr360/tickets/<numero>/followup`: atualiza apenas o seguimento permitido.

O mesmo serviço está disponível, para clientes MCP autenticados, em
`/mcp/gr360-tickets/`, com as ferramentas `listar_tickets`, `consultar_ticket`,
`criar_ticket` e `atualizar_seguimento`.

Exemplo de criação:

```json
{
  "pedido": "Título curto do problema",
  "descricao": "Resumo factual até 250 caracteres",
  "prompt_hugo": "Prompt técnico completo, com reprodução, evidências e resultado esperado.",
  "prioridade": "Normal",
  "utilizador": "Pessoa que reportou o problema",
  "referencia_externa": "identificador-estável-no-cloud-gpt"
}
```

Prioridades aceites: `Baixa`, `Normal`, `Alta` e `Urgente`.

Exemplo de seguimento:

```json
{
  "estado": "Validado",
  "seguimento": "Reproduzido na aplicação e confirmado após a correção.",
  "tratado": true
}
```

O token deve ser guardado como segredo do ambiente (`GR360_TICKETS_API_TOKEN`).
Nunca deve ser incluído em prompts, mensagens, ficheiros versionados ou logs.
