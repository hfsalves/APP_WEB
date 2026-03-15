# Plano de testes — migração progressiva de autenticação

## Pré-condições
- Executar `migrations/us_auth_hardening.sql`
- Instalar dependências (`pip install -r requirements.txt`)
- Confirmar que a tabela `dbo.US` mantém a coluna legacy `PASSWORD`

## Cenários obrigatórios

### 1. Utilizador antigo com password correta
1. Garantir utilizador com `PASSWORD_HASH` vazio e `PASSWORD` legacy preenchida.
2. Fazer login com a password correta.
3. Validar:
   - login bem-sucedido;
   - `PASSWORD_HASH` preenchido;
   - `PASSWORD_ALGO` preenchido;
   - `PASSWORD_MIGRADA = 1`;
   - `PASSWORD_CHANGED_AT` preenchido;
   - `PASSWORD` legacy mantém o valor anterior;
   - `FAILED_LOGIN_COUNT = 0`;
   - `LOCKED_UNTIL = NULL`;
   - `LAST_LOGIN_AT` atualizado.

### 2. Utilizador antigo com password errada
1. Garantir utilizador com `PASSWORD_HASH` vazio.
2. Fazer login com password errada.
3. Validar:
   - erro controlado;
   - `PASSWORD_HASH` continua vazio;
   - `FAILED_LOGIN_COUNT` incrementa.

### 3. Utilizador já migrado com password correta
1. Garantir utilizador com `PASSWORD_HASH` preenchido.
2. Fazer login com a password correta.
3. Validar:
   - login bem-sucedido;
   - autenticação por hash;
   - `FAILED_LOGIN_COUNT = 0`;
   - `LOCKED_UNTIL = NULL`;
   - `LAST_LOGIN_AT` atualizado.

### 4. Utilizador já migrado com password errada
1. Garantir utilizador com `PASSWORD_HASH` preenchido.
2. Fazer login com password errada.
3. Validar:
   - erro controlado;
   - `FAILED_LOGIN_COUNT` incrementa;
   - `PASSWORD` legacy não é alterada.

### 5. Bloqueio após 5 falhas
1. Executar 5 tentativas falhadas consecutivas para o mesmo utilizador ativo.
2. Validar:
   - `FAILED_LOGIN_COUNT >= 5`;
   - `LOCKED_UNTIL` preenchido com aproximadamente `+15 minutos`;
   - nova tentativa durante esse período devolve mensagem de conta bloqueada.

### 6. Login após expiração do bloqueio
1. Expirar `LOCKED_UNTIL` manualmente ou aguardar 15 minutos.
2. Fazer login com password correta.
3. Validar:
   - login bem-sucedido;
   - `FAILED_LOGIN_COUNT = 0`;
   - `LOCKED_UNTIL = NULL`.

### 7. Alteração de password mantém compatibilidade legacy
1. Usar `POST /api/profile/change_password`.
2. Validar:
   - `PASSWORD` legacy atualizado;
   - `PASSWORD_HASH` atualizado;
   - `PASSWORD_MIGRADA = 1`;
   - `PASSWORD_CHANGED_AT` atualizado;
   - login continua a funcionar no código novo;
   - a password legacy não é apagada nesta fase.

## Observações
- Os logs não devem conter passwords nem hashes.
- Se o ambiente ainda não tiver `argon2-cffi`, o sistema faz fallback para `scrypt` do Werkzeug até a dependência estar instalada.
