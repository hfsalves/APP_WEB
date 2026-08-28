---
name: gr360-ticket-workflow
description: Consulta, cria e acompanha tickets da aplicação GR360 através do conector GR360 Tickets ou, quando autorizado, diretamente na base de dados.
---

# Fluxo de tickets GR360

Prefere as ferramentas do servidor `gr360_tickets`, porque preservam o fluxo de autenticação e
seguimento. Se o conector estiver indisponível e o utilizador autorizar ou pedir explicitamente,
podes consultar os tickets diretamente na base de dados GR360 configurada para a aplicação.

Nunca mostres passwords, tokens, connection strings ou outras credenciais na conversa, em logs ou
em tickets. Nas consultas SQL, começa em modo de leitura. Só alteres tickets quando o utilizador o
pedir ou quando já tiver autorizado claramente o tratamento dos tickets em causa.

## Consultar e analisar

1. Usa `listar_tickets` para obter os tickets relevantes; se estiver indisponível e houver
   autorização, consulta a tabela de tickets da GR360 por SQL.
2. Usa `consultar_ticket` antes de concluir qualquer diagnóstico; no modo SQL, lê o registo completo
   e confirma o schema atual antes de interpretar campos de estado ou seguimento.
3. Distingue factos observados, inferências e informação ainda necessária.
4. Para tickets tratados sem seguimento, valida o comportamento atual antes de os considerar resolvidos.

## Criar

1. Pesquisa primeiro tickets semelhantes para evitar duplicados.
2. Usa uma `referencia_externa` estável e única no projeto do cliente.
3. Inclui em `prompt_hugo`: contexto, passos de reprodução, resultado atual, resultado esperado,
   dados e ecrãs envolvidos, evidências, critérios de aceitação e testes necessários.
4. Pede confirmação ao utilizador antes de chamar `criar_ticket`.

## Dar seguimento

1. Preserva sempre o pedido e o `prompt_hugo` originais.
2. Usa `atualizar_seguimento` apenas com uma conclusão suportada por evidências.
3. Usa estados claros, como `Validado`, `Requer PHC`, `Requer aplicação`,
   `Parcialmente resolvido`, `Precisa de dados do utilizador` ou `Impossível validar`.
4. Define `tratado=true` apenas quando o assunto estiver efetivamente resolvido ou formalmente substituído.
5. Pede confirmação ao utilizador antes de atualizar o seguimento.
