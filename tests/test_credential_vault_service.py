import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

from services.credential_vault_service import (
    VaultError,
    VaultValidationError,
    clean_item_payload,
    decrypt_secret,
    encrypt_secret,
    load_keyring,
    public_item,
)


class CredentialVaultServiceTests(unittest.TestCase):
    def setUp(self):
        self.raw_key = os.urandom(32)
        self.encoded_key = base64.urlsafe_b64encode(self.raw_key).decode("ascii")
        self.keyring = load_keyring(environ={
            "CREDENTIAL_VAULT_MASTER_KEY": self.encoded_key,
            "CREDENTIAL_VAULT_KEY_VERSION": "7",
        })

    def test_encrypts_and_decrypts_with_versioned_aad(self):
        encrypted = encrypt_secret(
            "segredo muito sensível",
            stamp="ABC123",
            feid=2,
            keyring=self.keyring,
        )
        self.assertEqual(encrypted["key_version"], 7)
        self.assertNotIn(b"segredo", encrypted["ciphertext"])
        result = decrypt_secret(
            encrypted["ciphertext"],
            encrypted["nonce"],
            stamp="ABC123",
            feid=2,
            key_version=7,
            keyring=self.keyring,
        )
        self.assertEqual(result, "segredo muito sensível")

    def test_ciphertext_cannot_be_moved_to_another_record(self):
        encrypted = encrypt_secret("secret", stamp="ONE", feid=2, keyring=self.keyring)
        with self.assertRaises(VaultError):
            decrypt_secret(
                encrypted["ciphertext"],
                encrypted["nonce"],
                stamp="TWO",
                feid=2,
                key_version=7,
                keyring=self.keyring,
            )

    def test_public_payload_never_exposes_encrypted_columns(self):
        result = public_item({
            "CREDENCIALSTAMP": "ABC",
            "CATEGORIA": "Portal",
            "DESCRICAO": "Conta",
            "LOGIN": "user",
            "SEGREDO_CIPHERTEXT": b"cipher",
            "SEGREDO_NONCE": b"123456789012",
            "SEGREDO_KEY_VERSION": 7,
            "ATIVO": 1,
        })
        self.assertEqual(result["login"], "user")
        self.assertNotIn("password", result)
        self.assertNotIn("ciphertext", result)
        self.assertNotIn("nonce", result)

    def test_validates_required_metadata(self):
        with self.assertRaises(VaultValidationError):
            clean_item_payload({"categoria": "", "descricao": "Conta"})
        with self.assertRaises(VaultValidationError):
            clean_item_payload({"categoria": "Portal", "descricao": ""})

    def test_loads_versioned_key_file_without_environment_fallback(self):
        second_key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "vault.json"
            path.write_text(json.dumps({
                "current_version": 8,
                "keys": {"7": self.encoded_key, "8": second_key},
            }), encoding="utf-8")
            ring = load_keyring(environ={}, key_file=path)
        self.assertEqual(ring.current_version, 8)
        self.assertEqual(set(ring.keys), {7, 8})


if __name__ == "__main__":
    unittest.main()
