import base64
import hashlib
import os
import unittest
from unittest import mock

from api.crypto import (
    get_encryption_key, hash_passphrase, verify_passphrase,
    hash_token, encrypt_field, decrypt_field
)


class TestGetEncryptionKey(unittest.TestCase):

    def test_get_encryption_key_generates_on_first_use(self):
        with mock.patch('keyring.get_password', return_value=None), \
             mock.patch('keyring.set_password') as mock_set:
            key = get_encryption_key()
            self.assertEqual(len(key), 32)
            mock_set.assert_called_once()

    def test_get_encryption_key_returns_stored(self):
        raw_key = os.urandom(32)
        encoded = base64.b64encode(raw_key).decode()
        with mock.patch('keyring.get_password', return_value=encoded):
            key = get_encryption_key()
            self.assertEqual(key, raw_key)


class TestHashPassphrase(unittest.TestCase):

    def test_hash_passphrase_work_factor(self):
        result = hash_passphrase('testPassword')
        self.assertTrue(result.startswith('$2b$12$'))

    def test_verify_passphrase_correct(self):
        passphrase = 'mySecretPass'
        hashed = hash_passphrase(passphrase)
        self.assertTrue(verify_passphrase(passphrase, hashed))

    def test_verify_passphrase_wrong(self):
        hashed = hash_passphrase('correctPassword')
        self.assertFalse(verify_passphrase('wrongPassword', hashed))


class TestHashToken(unittest.TestCase):

    def test_hash_token_sha256(self):
        token = 'testtoken123'
        expected = hashlib.sha256(token.encode()).hexdigest()
        self.assertEqual(hash_token(token), expected)


class TestEncryptDecryptField(unittest.TestCase):

    def _mock_key(self):
        return mock.patch('api.crypto.get_encryption_key', return_value=os.urandom(32))

    def test_encrypt_decrypt_roundtrip(self):
        fixed_key = os.urandom(32)
        with mock.patch('api.crypto.get_encryption_key', return_value=fixed_key):
            ciphertext_b64, iv_b64 = encrypt_field('Hello, World!')
            plaintext = decrypt_field(ciphertext_b64, iv_b64)
        self.assertEqual(plaintext, 'Hello, World!')

    def test_iv_length(self):
        with mock.patch('api.crypto.get_encryption_key', return_value=os.urandom(32)):
            _, iv_b64 = encrypt_field('some data')
        iv = base64.b64decode(iv_b64)
        self.assertEqual(len(iv), 16)


if __name__ == '__main__':
    unittest.main()
