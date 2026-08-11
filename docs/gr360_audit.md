# Auditoria GR360

A auditoria transversal da operação GR360 escreve em `GR360_LOG.dbo.LOGAPP`.
Está desligada por defeito e falha fechada: se o pedido não for inequivocamente
GR360, não abre ligação à base de log e não grava qualquer registo.

## Isolamento GuestSpaTur

A mesma aplicação serve GuestSpaTur e GR360. A auditoria só é avaliada quando:

- `GR360_AUDIT_ENABLED` está ativo;
- o target atual da aplicação é `client`;
- a base configurada para o target GR360 é `GR360_CORE`;
- a tabela está abrangida por `GR360_AUDIT_TABLES`, que por defeito é `*`.

Em contexto GuestSpaTur, normalmente target `prod`, o serviço retorna de imediato.
Não usa nem reutiliza ligações GuestSpaTur e não chama `GR360_LOG`.

## Variáveis de ambiente

Obrigatórias para ativar:

```bash
GR360_AUDIT_ENABLED=1
GR360_AUDIT_LOG_SERVER=10.0.1.12
GR360_AUDIT_LOG_DATABASE=GR360_LOG
GR360_AUDIT_LOG_USER=sa
GR360_AUDIT_LOG_PASSWORD=...
```

Opcionais:

```bash
GR360_AUDIT_LOG_PORT=
GR360_AUDIT_TARGET=client
GR360_AUDIT_EXPECTED_DATABASE=GR360_CORE
GR360_AUDIT_SOURCE_DATABASE=GR360_CORE
GR360_AUDIT_TABLES=*
GR360_AUDIT_SELECT_ENABLED=0
GR360_AUDIT_ENVIRONMENT=production
GR360_AUDIT_APP_NAME=APP_WEB
GR360_AUDIT_LOG_CONN_STR=
```

`GR360_AUDIT_LOG_CONN_STR` pode ser usado em alternativa aos campos separados,
mas deve apontar sempre para `GR360_LOG`.

## Dados sensíveis

O serviço mascara campos cujo nome indique passwords, hashes, reset tokens,
cookies, API keys, tokens, secrets, connection strings ou URLs de base de dados.
Estes valores não são gravados em `BEFORE_DATA`, `AFTER_DATA` nem
`CHANGED_DATA`.

## Cobertura inicial

A camada está ligada aos endpoints genéricos de escrita:

- `POST /generic/api/<table>`;
- `PUT /generic/api/<table>/<stamp>`;
- `DELETE /generic/api/<table>/<stamp>`.

Por defeito, `GR360_AUDIT_TABLES=*` audita todos os `dynamic_form` que gravam
pelos endpoints genéricos. Para restringir a cobertura, definir uma lista
explícita, por exemplo:

```bash
GR360_AUDIT_TABLES=CL,OPC,VA,FL,ST
```

A auditoria de `SELECT` está preparada em `audit_select`, mas fica desativada
por defeito.
