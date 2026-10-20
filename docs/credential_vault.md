# Cofre de credenciais

O cofre guarda metadados em `dbo.CREDENCIAL_VAULT` e cifra cada password com AES-256-GCM. A base de dados nunca recebe a chave nem a password em texto simples.

## Chaves

A aplicação procura, por esta ordem:

1. `CREDENTIAL_VAULT_KEYS_JSON`;
2. `CREDENTIAL_VAULT_MASTER_KEY` e `CREDENTIAL_VAULT_KEY_VERSION`;
3. `instance/credential_vault.keys.json`.

O ficheiro local deve ter permissões `0600`, não pode entrar no Git e deve ser copiado separadamente para recuperação segura. Formato:

```json
{"current_version":1,"keys":{"1":"base64-url-de-32-bytes"}}
```

Não remover versões antigas enquanto existirem cópias de segurança com ciphertext produzido por essas versões.

Para criar uma chave e recifrar todos os registos:

```bash
flask --app app credential-vault-rotate-key
```

A operação adiciona primeiro a nova chave ao ficheiro, recifra tudo numa transação e só depois torna a versão nova corrente. Uma falha intermédia mantém as duas chaves disponíveis.

## Permissões e reautenticação

Os utilizadores com `US.ADMIN=1` têm acesso total ao cofre e veem automaticamente o respetivo atalho no menu. Para os restantes utilizadores, as permissões vivem em `dbo.CREDENCIAL_VAULT_PERMISSAO`; sem linha explícita, o acesso é negado. Existem permissões separadas para consultar, criar, editar, desativar, revelar, copiar e administrar.

Revelar ou copiar exige nova confirmação da password da aplicação. A confirmação vale cinco minutos e fica vinculada ao utilizador da sessão. Após cinco falhas, novas tentativas ficam bloqueadas durante cinco minutos.

## Auditoria e exposição

`dbo.CREDENCIAL_VAULT_AUDIT` regista consultas, alterações, revelações, cópias, permissões, reautenticações e recusas, incluindo utilizador, data UTC, IP, user-agent e rota. A auditoria nunca guarda passwords, ciphertext, formulários ou chaves.

As respostas que podem conter um segredo usam `Cache-Control: no-store`. As listagens nunca selecionam nem devolvem ciphertext, nonce ou versão da chave. Não existe exportação de passwords.

## Recuperação

Sem uma das chaves correspondentes a `SEGREDO_KEY_VERSION`, a password não pode ser recuperada. A cópia segura do ficheiro de chaves deve, por isso, ser testada fora da base de dados e ter acesso mais restrito do que o próprio SQL Server.
