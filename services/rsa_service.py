import base64
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed


def _resolve_existing_path(path: str) -> str:
    raw = (path or "").strip()
    if not raw:
        raise ValueError("Caminho da chave RSA vazio.")
    expanded = os.path.expandvars(os.path.expanduser(raw))
    candidates = [expanded]
    if not os.path.isabs(expanded):
        candidates.append(os.path.abspath(expanded))
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(f"Ficheiro de chave RSA não encontrado: {raw}")


def load_private_key_from_pem(path: str) -> RSAPrivateKey:
    key_path = _resolve_existing_path(path)
    with open(key_path, "rb") as fh:
        data = fh.read()
    return serialization.load_pem_private_key(data, password=None)


def load_public_key_from_pem(path: str) -> RSAPublicKey:
    key_path = _resolve_existing_path(path)
    with open(key_path, "rb") as fh:
        data = fh.read()
    return serialization.load_pem_public_key(data)


def sign_sha1_prehashed(private_key: RSAPrivateKey, sha1_digest_bytes: bytes) -> bytes:
    return private_key.sign(
        sha1_digest_bytes,
        padding.PKCS1v15(),
        Prehashed(hashes.SHA1()),
    )


def verify_sha1_prehashed(public_key: RSAPublicKey, sha1_digest_bytes: bytes, signature_bytes: bytes) -> bool:
    try:
        public_key.verify(
            signature_bytes,
            sha1_digest_bytes,
            padding.PKCS1v15(),
            Prehashed(hashes.SHA1()),
        )
        return True
    except Exception:
        return False


def b64encode_signature(sig_bytes: bytes) -> str:
    return base64.b64encode(sig_bytes or b"").decode("ascii")


def b64decode_signature(sig_b64: str) -> bytes:
    return base64.b64decode((sig_b64 or "").encode("ascii"))

