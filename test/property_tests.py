import base64
import hashlib
import os
import unittest
from unittest import mock

from hypothesis import given, settings
from hypothesis import strategies as st

from api.crypto import (
    hash_passphrase, verify_passphrase,
    hash_token, encrypt_field, decrypt_field, get_encryption_key
)


class PropertyTests(unittest.TestCase):

    # Feature: gdpr-secure-student-registration, Property 1: Passphrase hash round-trip
    @given(st.text(alphabet=st.characters(max_codepoint=0x7F), min_size=1, max_size=72))
    @settings(max_examples=20, deadline=None)
    def test_passphrase_hash_roundtrip(self, passphrase):
        h = hash_passphrase(passphrase)
        self.assertTrue(verify_passphrase(passphrase, h))

    # Feature: gdpr-secure-student-registration, Property 3: Bcrypt non-determinism
    @given(st.text(alphabet=st.characters(max_codepoint=0x7F), min_size=1, max_size=72))
    @settings(max_examples=10, deadline=None)
    def test_passphrase_hash_nondeterministic(self, passphrase):
        self.assertNotEqual(hash_passphrase(passphrase), hash_passphrase(passphrase))

    # Feature: gdpr-secure-student-registration, Property 4: Token hash determinism
    @given(st.text(min_size=1))
    @settings(max_examples=100)
    def test_token_hash_deterministic(self, token):
        self.assertEqual(hash_token(token), hash_token(token))
        self.assertEqual(hash_token(token), hashlib.sha256(token.encode()).hexdigest())

    # Feature: gdpr-secure-student-registration, Property 7: Personal data encryption round-trip
    @given(st.text(min_size=1))
    @settings(max_examples=100)
    def test_encrypt_decrypt_roundtrip(self, value):
        fixed_key = os.urandom(32)
        with mock.patch('api.crypto.get_encryption_key', return_value=fixed_key):
            ct, iv = encrypt_field(value)
            result = decrypt_field(ct, iv)
        self.assertEqual(result, value)

    # Feature: gdpr-secure-student-registration, Property 8: IV is 16 bytes and unique per call
    @given(st.text(min_size=1))
    @settings(max_examples=100)
    def test_iv_16_bytes_and_unique(self, value):
        fixed_key = os.urandom(32)
        with mock.patch('api.crypto.get_encryption_key', return_value=fixed_key):
            _, iv1 = encrypt_field(value)
            _, iv2 = encrypt_field(value)
        self.assertEqual(len(base64.b64decode(iv1)), 16)
        self.assertEqual(len(base64.b64decode(iv2)), 16)
        self.assertNotEqual(iv1, iv2)

    # Feature: gdpr-secure-student-registration, Property 11: Encryption key is always 32 bytes
    def test_encryption_key_32_bytes(self):
        with mock.patch('keyring.get_password', return_value=None), \
             mock.patch('keyring.set_password'):
            key = get_encryption_key()
        self.assertEqual(len(key), 32)


if __name__ == '__main__':
    unittest.main()
