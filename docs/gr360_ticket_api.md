# API de tickets GR360

Esta API permite que integrações externas criem tickets na `GR360_CORE.dbo.TK` e acompanhem o respetivo estado sem receberem acesso SQL à aplicação.

## Isolamento e segurança

- A API usa sempre o bind `client` e valida que `DB_NAME()` é `GR360_CORE`.
- A autenticação é feita por `Authorization: Bearer <token>`.
- O token é apresentado apenas na criação da credencial. Na base fica apenas SHA-256.
- Cada cliente consulta, por defeito, apenas os tickets que criou.
- A API não permite marcar tickets como tratados nem alterar o seguimento interno.
- `referencia_externa` torna a criação idempotente: repetir a mesma referência devolve o ticket existente.

## Configuração

- `GR360_TICKET_API_ENABLED`: ativa/desativa a API. Valor predefinido: `1`.
- `GR360_TICKET_API_EXPECTED_DATABASE`: base obrigatória. Valor predefinido: `GR360_CORE`.

Aplicar primeiro `migrations/gr360_ticket_api.sql` na `GR360_CORE`.

## Endpoints

- `POST /api/gr360/tickets`: cria um ticket.
- `GET /api/gr360/tickets?status=pending&limit=50`: lista tickets da credencial.
- `GET /api/gr360/tickets/<numero>`: consulta o ticket completo e o seguimento.

Exemplo de criação:

```json
{
  "pedido": "Título curto do problema",
  "descricao": "Resumo factual até 250 caracteres",
  "prompt_hugo": "Prompt técnico completo, com reprodução, evidências e resultado esperado.",
  "prioridade": "Normal",
  "feid": 8,
  "utilizador": "Pessoa que reportou o problema",
  "referencia_externa": "identificador-estável-no-cloud-gpt"
}
```

Prioridades aceites: `Baixa`, `Normal`, `Alta` e `Urgente`.
