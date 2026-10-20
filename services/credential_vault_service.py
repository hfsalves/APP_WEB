from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app, has_app_context
from sqlalchemy import text


PERMISSION_FIELDS = (
    "consultar",
    "criar",
    "editar",
    "desativar",
    "revelar",
    "copiar",
    "administrar",
)


class VaultError(RuntimeError):
    pass


class VaultConfigurationError(VaultError):
    pass


class VaultValidationError(VaultError):
    pass


@dataclass(frozen=True)
class VaultKeyring:
    current_version: int
    keys: dict[int, bytes]


def new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _clean(value: object, max_length: int | None = None) -> str:
    result = str(value or "").strip()
    return result[:max_length] if max_length else result


def _decode_key(value: object) -> bytes:
    raw = _clean(value)
    if not raw:
        raise VaultConfigurationError("A chave do cofre não está configurada.")
    try:
        key = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:
        raise VaultConfigurationError("A chave do cofre tem um formato inválido.") from exc
    if len(key) != 32:
        raise VaultConfigurationError("A chave do cofre deve ter exatamente 32 bytes.")
    return key


def load_keyring(
    *,
    environ: Mapping[str, str] | None = None,
    key_file: str | os.PathLike[str] | None = None,
) -> VaultKeyring:
    source = environ if environ is not None else os.environ
    raw_json = _clean(source.get("CREDENTIAL_VAULT_KEYS_JSON"))
    explicit_key = _clean(source.get("CREDENTIAL_VAULT_MASTER_KEY"))
    explicit_version = _clean(source.get("CREDENTIAL_VAULT_KEY_VERSION"))

    if raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise VaultConfigurationError("CREDENTIAL_VAULT_KEYS_JSON não contém JSON válido.") from exc
    elif explicit_key:
        payload = {
            "current_version": int(explicit_version or 1),
            "keys": {str(int(explicit_version or 1)): explicit_key},
        }
    else:
        resolved_file = Path(key_file) if key_file else None
        if resolved_file is None and has_app_context():
            configured = _clean(current_app.config.get("CREDENTIAL_VAULT_KEY_FILE"))
            resolved_file = Path(configured) if configured else Path(current_app.instance_path) / "credential_vault.keys.json"
        if resolved_file is None or not resolved_file.is_file():
            raise VaultConfigurationError(
                "Configura CREDENTIAL_VAULT_MASTER_KEY ou um ficheiro de chaves do cofre."
            )
        try:
            payload = json.loads(resolved_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VaultConfigurationError("Não foi possível ler o ficheiro de chaves do cofre.") from exc

    try:
        current_version = int(payload.get("current_version") or 0)
        raw_keys = payload.get("keys") or {}
        keys = {int(version): _decode_key(value) for version, value in raw_keys.items()}
    except (TypeError, ValueError) as exc:
        raise VaultConfigurationError("A configuração de versões do cofre é inválida.") from exc
    if current_version <= 0 or current_version not in keys:
        raise VaultConfigurationError("A versão atual da chave do cofre não está disponível.")
    return VaultKeyring(current_version=current_version, keys=keys)


def _aad(stamp: str, feid: int, version: int) -> bytes:
    return f"GUESTSPATUR-CREDENTIAL-VAULT|{stamp}|{int(feid)}|v{int(version)}".encode("utf-8")


def encrypt_secret(secret: object, *, stamp: str, feid: int, keyring: VaultKeyring | None = None) -> dict[str, Any]:
    plaintext = str(secret or "")
    if not plaintext:
        raise VaultValidationError("A password é obrigatória.")
    if len(plaintext) > 4096:
        raise VaultValidationError("A password excede o tamanho máximo permitido.")
    ring = keyring or load_keyring()
    version = ring.current_version
    nonce = os.urandom(12)
    ciphertext = AESGCM(ring.keys[version]).encrypt(
        nonce,
        plaintext.encode("utf-8"),
        _aad(stamp, feid, version),
    )
    return {"ciphertext": ciphertext, "nonce": nonce, "key_version": version}


def decrypt_secret(
    ciphertext: bytes,
    nonce: bytes,
    *,
    stamp: str,
    feid: int,
    key_version: int,
    keyring: VaultKeyring | None = None,
) -> str:
    ring = keyring or load_keyring()
    key = ring.keys.get(int(key_version))
    if not key:
        raise VaultConfigurationError(f"A chave da versão {int(key_version)} não está disponível.")
    try:
        plaintext = AESGCM(key).decrypt(
            bytes(nonce),
            bytes(ciphertext),
            _aad(stamp, feid, key_version),
        )
    except Exception as exc:
        raise VaultError("Não foi possível desencriptar esta credencial.") from exc
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VaultError("O conteúdo desencriptado da credencial é inválido.") from exc


def ensure_schema(db_session) -> None:
    database_name = _clean(db_session.execute(text("SELECT DB_NAME()")).scalar()).upper()
    if database_name != "GESTAO":
        raise VaultError("O cofre de credenciais só está disponível na base GESTAO.")
    db_session.execute(text("""
        IF OBJECT_ID('dbo.CREDENCIAL_VAULT', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.CREDENCIAL_VAULT (
                CREDENCIALSTAMP varchar(25) NOT NULL CONSTRAINT PK_CREDENCIAL_VAULT PRIMARY KEY,
                FEID int NOT NULL,
                CATEGORIA nvarchar(80) NOT NULL CONSTRAINT DF_CRED_VAULT_CATEGORIA DEFAULT (N''),
                DESCRICAO nvarchar(200) NOT NULL CONSTRAINT DF_CRED_VAULT_DESCRICAO DEFAULT (N''),
                URL nvarchar(1000) NOT NULL CONSTRAINT DF_CRED_VAULT_URL DEFAULT (N''),
                LOGIN nvarchar(255) NOT NULL CONSTRAINT DF_CRED_VAULT_LOGIN DEFAULT (N''),
                SEGREDO_CIPHERTEXT varbinary(max) NOT NULL,
                SEGREDO_NONCE binary(12) NOT NULL,
                SEGREDO_KEY_VERSION int NOT NULL,
                NOTAS nvarchar(max) NOT NULL CONSTRAINT DF_CRED_VAULT_NOTAS DEFAULT (N''),
                ATIVO bit NOT NULL CONSTRAINT DF_CRED_VAULT_ATIVO DEFAULT (1),
                DTCRI_UTC datetime2(3) NOT NULL CONSTRAINT DF_CRED_VAULT_DTCRI DEFAULT (SYSUTCDATETIME()),
                DTALT_UTC datetime2(3) NULL,
                USERCRIACAO varchar(100) NOT NULL CONSTRAINT DF_CRED_VAULT_USERCRI DEFAULT (''),
                USERALTERACAO varchar(100) NOT NULL CONSTRAINT DF_CRED_VAULT_USERALT DEFAULT (''),
                ROW_VERSION rowversion NOT NULL
            );
        END;

        IF OBJECT_ID('dbo.CREDENCIAL_VAULT_PERMISSAO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.CREDENCIAL_VAULT_PERMISSAO (
                PERMISSAOSTAMP varchar(25) NOT NULL CONSTRAINT PK_CRED_VAULT_PERM PRIMARY KEY,
                LOGIN varchar(100) NOT NULL,
                CONSULTAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_CONS DEFAULT (0),
                CRIAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_CRIAR DEFAULT (0),
                EDITAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_EDIT DEFAULT (0),
                DESATIVAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_DES DEFAULT (0),
                REVELAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_REV DEFAULT (0),
                COPIAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_COP DEFAULT (0),
                ADMINISTRAR bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_ADM DEFAULT (0),
                ATIVO bit NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_ATIVO DEFAULT (1),
                DTCRI_UTC datetime2(3) NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_DTCRI DEFAULT (SYSUTCDATETIME()),
                DTALT_UTC datetime2(3) NULL,
                USERALTERACAO varchar(100) NOT NULL CONSTRAINT DF_CRED_VAULT_PERM_USER DEFAULT ('')
            );
        END;

        IF OBJECT_ID('dbo.CREDENCIAL_VAULT_AUDIT', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.CREDENCIAL_VAULT_AUDIT (
                AUDITSTAMP varchar(25) NOT NULL CONSTRAINT PK_CRED_VAULT_AUDIT PRIMARY KEY,
                CREDENCIALSTAMP varchar(25) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_CRED DEFAULT (''),
                ACAO varchar(30) NOT NULL,
                SUCESSO bit NOT NULL,
                MOTIVO nvarchar(200) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_MOTIVO DEFAULT (N''),
                UTILIZADOR varchar(100) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_USER DEFAULT (''),
                USSTAMP varchar(25) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_US DEFAULT (''),
                FEID int NULL,
                IP varchar(64) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_IP DEFAULT (''),
                USER_AGENT nvarchar(500) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_UA DEFAULT (N''),
                REQUEST_PATH nvarchar(500) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_PATH DEFAULT (N''),
                DTCRI_UTC datetime2(3) NOT NULL CONSTRAINT DF_CRED_VAULT_AUDIT_DTCRI DEFAULT (SYSUTCDATETIME())
            );
        END;

        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.CREDENCIAL_VAULT') AND name='IX_CRED_VAULT_FEID_ATIVO')
            CREATE INDEX IX_CRED_VAULT_FEID_ATIVO ON dbo.CREDENCIAL_VAULT (FEID, ATIVO, CATEGORIA, DESCRICAO);
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.CREDENCIAL_VAULT_PERMISSAO') AND name='UX_CRED_VAULT_PERM_LOGIN')
            CREATE UNIQUE INDEX UX_CRED_VAULT_PERM_LOGIN ON dbo.CREDENCIAL_VAULT_PERMISSAO (LOGIN);
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.CREDENCIAL_VAULT_AUDIT') AND name='IX_CRED_VAULT_AUDIT_TARGET')
            CREATE INDEX IX_CRED_VAULT_AUDIT_TARGET ON dbo.CREDENCIAL_VAULT_AUDIT (CREDENCIALSTAMP, DTCRI_UTC DESC);

        IF NOT EXISTS (SELECT 1 FROM dbo.CREDENCIAL_VAULT_PERMISSAO WHERE LOWER(LTRIM(RTRIM(LOGIN)))='admin')
            INSERT INTO dbo.CREDENCIAL_VAULT_PERMISSAO
                (PERMISSAOSTAMP, LOGIN, CONSULTAR, CRIAR, EDITAR, DESATIVAR, REVELAR, COPIAR, ADMINISTRAR, ATIVO, USERALTERACAO)
            VALUES
                (:permission_stamp, 'admin', 1, 1, 1, 1, 1, 1, 1, 1, 'system');
    """), {"permission_stamp": new_stamp()})


def user_permissions(db_session, login: object) -> dict[str, bool]:
    clean_login = _clean(login, 100)
    defaults = {field: False for field in PERMISSION_FIELDS}
    if not clean_login:
        return defaults
    row = db_session.execute(text("""
        SELECT TOP 1 CONSULTAR, CRIAR, EDITAR, DESATIVAR, REVELAR, COPIAR, ADMINISTRAR
        FROM dbo.CREDENCIAL_VAULT_PERMISSAO
        WHERE LOWER(LTRIM(RTRIM(LOGIN)))=LOWER(:login) AND ISNULL(ATIVO,0)=1
    """), {"login": clean_login}).mappings().first()
    if not row:
        return defaults
    return {field: bool(row.get(field.upper()) or 0) for field in PERMISSION_FIELDS}


def clean_item_payload(payload: Mapping[str, object] | None) -> dict[str, Any]:
    source = payload or {}
    category = _clean(source.get("categoria"), 80)
    description = _clean(source.get("descricao"), 200)
    if not category:
        raise VaultValidationError("A categoria é obrigatória.")
    if not description:
        raise VaultValidationError("A descrição é obrigatória.")
    return {
        "categoria": category,
        "descricao": description,
        "url": _clean(source.get("url"), 1000),
        "login": _clean(source.get("login"), 255),
        "notas": _clean(source.get("notas")),
        "ativo": bool(source.get("ativo", True)),
    }


def public_item(row: Mapping[str, object]) -> dict[str, Any]:
    created = row.get("DTCRI_UTC")
    changed = row.get("DTALT_UTC")
    return {
        "stamp": _clean(row.get("CREDENCIALSTAMP"), 25),
        "categoria": _clean(row.get("CATEGORIA")),
        "descricao": _clean(row.get("DESCRICAO")),
        "url": _clean(row.get("URL")),
        "login": _clean(row.get("LOGIN")),
        "notas": _clean(row.get("NOTAS")),
        "ativo": bool(row.get("ATIVO") or 0),
        "criado_em": created.isoformat() if hasattr(created, "isoformat") else _clean(created),
        "alterado_em": changed.isoformat() if hasattr(changed, "isoformat") else _clean(changed),
        "criado_por": _clean(row.get("USERCRIACAO")),
        "alterado_por": _clean(row.get("USERALTERACAO")),
    }


def audit_event(
    db_session,
    *,
    action: str,
    success: bool,
    user_login: object,
    user_stamp: object = "",
    credential_stamp: object = "",
    feid: int | None = None,
    reason: object = "",
    ip: object = "",
    user_agent: object = "",
    request_path: object = "",
) -> None:
    db_session.execute(text("""
        INSERT INTO dbo.CREDENCIAL_VAULT_AUDIT
            (AUDITSTAMP, CREDENCIALSTAMP, ACAO, SUCESSO, MOTIVO, UTILIZADOR, USSTAMP, FEID, IP, USER_AGENT, REQUEST_PATH)
        VALUES
            (:stamp, :credential_stamp, :action, :success, :reason, :user_login, :user_stamp, :feid, :ip, :user_agent, :request_path)
    """), {
        "stamp": new_stamp(),
        "credential_stamp": _clean(credential_stamp, 25),
        "action": _clean(action, 30).upper(),
        "success": 1 if success else 0,
        "reason": _clean(reason, 200),
        "user_login": _clean(user_login, 100),
        "user_stamp": _clean(user_stamp, 25),
        "feid": int(feid) if feid not in (None, "") else None,
        "ip": _clean(ip, 64),
        "user_agent": _clean(user_agent, 500),
        "request_path": _clean(request_path, 500),
    })


def _write_key_file(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def rotate_key_file(db_session, key_file: str | os.PathLike[str]) -> dict[str, int]:
    """Add a key version and re-encrypt every credential before making it current."""
    path = Path(key_file)
    try:
        original_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VaultConfigurationError("Não foi possível ler o ficheiro de chaves do cofre.") from exc
    old_ring = load_keyring(key_file=path, environ={})
    raw_keys = dict(original_payload.get("keys") or {})
    new_version = max(old_ring.keys) + 1
    raw_keys[str(new_version)] = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")

    # Primeiro persiste a nova chave, mantendo a versão anterior como atual.
    # Assim, mesmo uma falha durante a rotação nunca deixa ciphertext sem chave.
    staged_payload = {"current_version": old_ring.current_version, "keys": raw_keys}
    _write_key_file(path, staged_payload)
    new_ring = load_keyring(key_file=path, environ={})
    rotation_ring = VaultKeyring(current_version=new_version, keys=new_ring.keys)

    rows = db_session.execute(text("""
        SELECT CREDENCIALSTAMP, FEID, SEGREDO_CIPHERTEXT, SEGREDO_NONCE, SEGREDO_KEY_VERSION
        FROM dbo.CREDENCIAL_VAULT WITH (UPDLOCK, HOLDLOCK)
        ORDER BY CREDENCIALSTAMP
    """)).mappings().all()
    try:
        for row in rows:
            stamp = _clean(row.get("CREDENCIALSTAMP"), 25)
            feid = int(row.get("FEID") or 0)
            plaintext = decrypt_secret(
                row.get("SEGREDO_CIPHERTEXT"),
                row.get("SEGREDO_NONCE"),
                stamp=stamp,
                feid=feid,
                key_version=int(row.get("SEGREDO_KEY_VERSION") or 0),
                keyring=new_ring,
            )
            encrypted = encrypt_secret(
                plaintext,
                stamp=stamp,
                feid=feid,
                keyring=rotation_ring,
            )
            db_session.execute(text("""
                UPDATE dbo.CREDENCIAL_VAULT
                SET SEGREDO_CIPHERTEXT=:ciphertext,
                    SEGREDO_NONCE=:nonce,
                    SEGREDO_KEY_VERSION=:key_version,
                    DTALT_UTC=SYSUTCDATETIME(),
                    USERALTERACAO='key-rotation'
                WHERE CREDENCIALSTAMP=:stamp
            """), {**encrypted, "stamp": stamp})
        audit_event(
            db_session,
            action="ROTACIONAR_CHAVE",
            success=True,
            user_login="system",
            reason=f"Versão {old_ring.current_version} para {new_version}; {len(rows)} registo(s)",
        )
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise

    _write_key_file(path, {"current_version": new_version, "keys": raw_keys})
    return {"previous_version": old_ring.current_version, "current_version": new_version, "records": len(rows)}
