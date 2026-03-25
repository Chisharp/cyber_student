import os
import base64
import hashlib
import keyring
import bcrypt

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

KEYRING_SERVICE = "gdpr-student-api"
KEYRING_USERNAME = "aes-key"


def get_encryption_key() -> bytes:
    """Return the 32-byte AES key from the OS keyring, generating it on first use."""
    stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if stored is None:
        raw = os.urandom(32)
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, base64.b64encode(raw).decode())
        return raw
    return base64.b64decode(stored)


def hash_passphrase(passphrase: str) -> str:
    """Hash a passphrase using bcrypt with 12 rounds."""
    return bcrypt.hashpw(passphrase.encode(), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_passphrase(passphrase: str, passphrase_hash: str) -> bool:
    """Verify a passphrase against its bcrypt hash."""
    return bcrypt.checkpw(passphrase.encode(), passphrase_hash.encode())

def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of the given token."""
    return hashlib.sha256(token.encode()).hexdigest()

def encrypt_field(plaintext: str) -> tuple[str, str]:
    """Encrypt a string field using AES-256-CBC. Returns (ciphertext_b64, iv_b64)."""
    key = get_encryption_key()
    iv = os.urandom(16)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    return (base64.b64encode(ciphertext).decode(), base64.b64encode(iv).decode())


def decrypt_field(ciphertext_b64: str, iv_b64: str) -> str:
    """Decrypt an AES-256-CBC encrypted field. Returns the original plaintext."""
    key = get_encryption_key()
    iv = base64.b64decode(iv_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded_plaintext = dec.update(ciphertext) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
    return plaintext_bytes.decode()
