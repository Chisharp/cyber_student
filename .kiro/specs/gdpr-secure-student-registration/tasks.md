# Implementation Plan: GDPR-Secure Student Registration

## Overview

Harden the existing Tornado student registration API to meet GDPR security standards.
Each task touches one file or one concern at a time, building incrementally toward a
fully secured system. All existing API contracts and HTTP status codes are preserved.

## Tasks

- [x] 1. Verify and update dependencies in `requirements.txt`
  - Add `bcrypt` and `hypothesis` to `requirements.txt` if not already present
  - Confirm `cryptography` and `keyring` are already listed (they are)
  - Run `pip install -r requirements.txt` to verify no install errors
  - _Requirements: 1.1, 8.1_

- [x] 2. Create `api/crypto.py` with key management
  - Create the new file `api/crypto.py`
  - Define constants `KEYRING_SERVICE = "gdpr-student-api"` and `KEYRING_USERNAME = "aes-key"`
  - Implement `get_encryption_key() -> bytes`:
    - Call `keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)`
    - If `None`, generate 32 random bytes with `os.urandom(32)`, base64-encode and store via `keyring.set_password`, then return the raw bytes
    - If found, base64-decode and return the stored bytes
  - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - _Design: Key Management Detail section_

- [x] 3. Add passphrase hashing functions to `api/crypto.py`
  - Add `hash_passphrase(passphrase: str) -> str`:
    - Use `bcrypt.hashpw(passphrase.encode(), bcrypt.gensalt(rounds=12))` and return as a decoded string
  - Add `verify_passphrase(passphrase: str, passphrase_hash: str) -> bool`:
    - Use `bcrypt.checkpw(passphrase.encode(), passphrase_hash.encode())` and return the result
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 2.3_
  - _Design: Passphrase hashing section_

- [x] 4. Add token hashing function to `api/crypto.py`
  - Add `hash_token(token: str) -> str`:
    - Use `hashlib.sha256(token.encode()).hexdigest()` and return the result
  - _Requirements: 3.2, 3.4, 4.1_
  - _Design: Token hashing section_

- [x] 5. Add field encryption and decryption functions to `api/crypto.py`
  - Add `encrypt_field(plaintext: str) -> tuple[str, str]`:
    - Call `get_encryption_key()` to get the AES key
    - Generate a random 16-byte IV with `os.urandom(16)`
    - Pad the plaintext with PKCS7 padding (block size 128)
    - Encrypt with `Cipher(algorithms.AES(key), modes.CBC(iv))`
    - Return `(base64_ciphertext, base64_iv)` both as decoded strings
  - Add `decrypt_field(ciphertext_b64: str, iv_b64: str) -> str`:
    - Call `get_encryption_key()`, base64-decode both inputs
    - Decrypt with AES-256-CBC, remove PKCS7 padding, return decoded plaintext string
  - _Requirements: 5.1, 5.2, 5.3, 5.6, 6.2, 8.4_
  - _Design: AES-256-CBC Detail section_

- [x] 6. Update `api/handlers/registration.py` to hash password and encrypt personal data
  - Import `hash_passphrase` and `encrypt_field` from `api.crypto`
  - Replace `'password': password` with `'password': hash_passphrase(password)` in the `insert_one` call
  - Define the list of personal data fields: `['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']`
  - For each personal data field present in the request body, call `encrypt_field(value)` and add both `field: ciphertext_b64` and `f"{field}_iv": iv_b64` to the document dict
  - Never write plaintext personal data or plaintext password to MongoDB
  - Response body stays unchanged: `{email, displayName}`
  - _Requirements: 1.2, 5.1, 5.4, 5.5, 7.1, 9.1, 9.3_

- [x] 7. Update `api/handlers/login.py` to verify password and hash token before storing
  - Import `verify_passphrase` and `hash_token` from `api.crypto`
  - Replace the `user['password'] != password` comparison with `not verify_passphrase(password, user['password'])`
  - In `generate_token`, replace `'token': token_uuid` (in the `$set` dict) with `'token': hash_token(token_uuid)`
  - The plaintext `token_uuid` is still returned to the client in the response body — only the hash goes to MongoDB
  - _Requirements: 2.1, 2.2, 2.3, 3.2, 3.3, 9.1, 9.4_

- [x] 8. Update `api/handlers/auth.py` to hash the incoming token before querying MongoDB
  - Import `hash_token` from `api.crypto`
  - Before the `find_one` call, compute `token_hash = hash_token(token)`
  - Change the query from `{'token': token}` to `{'token': token_hash}`
  - All other logic (expiry check, `current_user` population) stays unchanged
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 9. Update `api/handlers/user.py` to decrypt personal data fields before returning
  - Import `decrypt_field` from `api.crypto`
  - Change the handler to `async def get` and fetch the full user document from MongoDB using `self.current_user['email']`
  - Define the list of personal data fields: `['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']`
  - For each field present in the document, call `decrypt_field(doc[field], doc[f"{field}_iv"])` and add the plaintext to `self.response`
  - Wrap decryption in a try/except; on any exception respond with HTTP 500 and return immediately
  - If a field is absent from the document, omit it from the response silently
  - `email` and `displayName` are not encrypted — include them as before
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.4_

- [x] 10. Update `test/registration.py` setUp to work with hashed passwords
  - The existing tests in `test/registration.py` POST through the HTTP handler, so no setUp change is needed for those tests
  - Verify the existing `test_registration`, `test_registration_without_display_name`, and `test_registration_twice` tests still pass after the handler change (they use the HTTP endpoint, not direct DB inserts)
  - _Requirements: 9.1, 9.2_

- [x] 11. Update `test/login.py` setUp to seed the database with a bcrypt-hashed password
  - Import `hash_passphrase` from `api.crypto`
  - In the `register` async method, replace `'password': self.password` with `'password': hash_passphrase(self.password)`
  - Keep `self.password = 'testPassword'` as the plaintext value used in test request bodies
  - This ensures the existing `test_login`, `test_login_case_insensitive`, `test_login_wrong_email`, and `test_login_wrong_password` tests continue to pass
  - _Requirements: 9.1, 9.2_

- [x] 12. Update `test/user.py` setUp to seed the database with hashed password and hashed token
  - Import `hash_passphrase` and `hash_token` from `api.crypto`
  - In the `register` async method, replace `'password': self.password` with `'password': hash_passphrase(self.password)`
  - In the `login` async method, replace `'token': self.token` with `'token': hash_token(self.token)`
  - Keep `self.token = 'testToken'` as the plaintext value used in the `X-Token` request header
  - This ensures the existing `test_user`, `test_user_without_token`, and `test_user_wrong_token` tests continue to pass
  - _Requirements: 9.1, 9.2_

- [x] 13. Checkpoint — run the full test suite
  - Run `python run_test.py` and confirm all pre-existing tests pass
  - Fix any issues before continuing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Create `test/crypto.py` with unit tests for all crypto functions
  - [x] 14.1 Write unit tests for `get_encryption_key`
    - `test_get_encryption_key_generates_on_first_use`: mock `keyring.get_password` to return `None`; assert returned key is 32 bytes and `keyring.set_password` was called
    - `test_get_encryption_key_returns_stored`: mock `keyring.get_password` to return a base64-encoded 32-byte key; assert the same key bytes are returned
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 14.2 Write unit tests for `hash_passphrase` and `verify_passphrase`
    - `test_hash_passphrase_work_factor`: assert the hash string starts with `$2b$12$`
    - `test_verify_passphrase_correct`: hash a passphrase then verify it returns `True`
    - `test_verify_passphrase_wrong`: verify with a different password returns `False`
    - _Requirements: 1.1, 1.4, 10.2_

  - [x] 14.3 Write unit tests for `hash_token`
    - `test_hash_token_sha256`: assert `hash_token(t) == hashlib.sha256(t.encode()).hexdigest()` for a known value
    - _Requirements: 3.2, 3.4, 10.4_

  - [x] 14.4 Write unit tests for `encrypt_field` and `decrypt_field`
    - `test_encrypt_decrypt_roundtrip`: encrypt a string then decrypt it; assert result equals original
    - `test_iv_length`: assert `len(base64.b64decode(iv))` equals 16
    - _Requirements: 5.6, 10.6_

- [x] 15. Add security-specific tests to `test/registration.py`
  - `test_password_not_stored_as_plaintext`: register a user, fetch the document from `self.get_app().db.users`, assert `doc['password'] != plaintext_password`
  - `test_password_stored_as_bcrypt_hash`: assert `bcrypt.checkpw(plaintext.encode(), doc['password'].encode())` is `True`
  - `test_personal_data_not_stored_as_plaintext`: register with all five personal data fields; assert each stored value differs from the plaintext supplied
  - `test_personal_data_iv_keys_present`: assert `<fieldName>_iv` keys exist in the document for each supplied personal data field
  - _Requirements: 1.2, 5.4, 5.5, 7.1, 10.1, 10.2, 10.5_

- [x] 16. Add security-specific tests to `test/login.py`
  - `test_token_not_stored_as_plaintext`: call the login endpoint, capture the `token` from the response body, fetch the user document, assert `doc['token'] != response_token`
  - `test_token_stored_as_sha256`: assert `doc['token'] == hashlib.sha256(response_token.encode()).hexdigest()`
  - _Requirements: 3.3, 10.3, 10.4_

- [x] 17. Add security-specific tests to `test/user.py`
  - `test_user_personal_data_decrypted`: register a user with personal data fields via the HTTP endpoint, log in, call `GET /user` with the token, assert each personal data field in the response equals the original plaintext value supplied at registration
  - `test_user_missing_field_omitted`: register a user without optional personal data fields; call `GET /user` and assert those keys are absent from the response body
  - _Requirements: 6.2, 6.3, 7.4, 10.6_

- [x] 18. Create `test/property_tests.py` with Hypothesis property-based tests
  - [x] 18.1 Write property test for Property 1: Passphrase hash round-trip
    - `@given(st.text(min_size=1))` on `test_passphrase_hash_roundtrip`
    - Assert `verify_passphrase(passphrase, hash_passphrase(passphrase))` is `True`
    - `# Feature: gdpr-secure-student-registration, Property 1: Passphrase hash round-trip`
    - _Requirements: 1.4, 10.7_

  - [x] 18.2 Write property test for Property 3: Bcrypt non-determinism
    - `@given(st.text(min_size=1))` on `test_passphrase_hash_nondeterministic`
    - Assert `hash_passphrase(passphrase) != hash_passphrase(passphrase)`
    - `# Feature: gdpr-secure-student-registration, Property 3: Bcrypt non-determinism`
    - _Requirements: 1.3_

  - [x] 18.3 Write property test for Property 4: Token hash determinism
    - `@given(st.text(min_size=1))` on `test_token_hash_deterministic`
    - Assert `hash_token(token) == hash_token(token)` and equals `hashlib.sha256(token.encode()).hexdigest()`
    - `# Feature: gdpr-secure-student-registration, Property 4: Token hash determinism`
    - _Requirements: 3.2, 3.4, 10.3, 10.4_

  - [x] 18.4 Write property test for Property 7: Personal data encryption round-trip
    - `@given(st.text(min_size=1))` on `test_encrypt_decrypt_roundtrip`
    - Assert `decrypt_field(*encrypt_field(value)) == value`
    - `# Feature: gdpr-secure-student-registration, Property 7: Personal data encryption round-trip`
    - _Requirements: 5.6, 10.6, 10.8_

  - [x] 18.5 Write property test for Property 8: IV is 16 bytes and unique per call
    - `@given(st.text(min_size=1))` on `test_iv_16_bytes_and_unique`
    - Call `encrypt_field(value)` twice; assert each decoded IV is 16 bytes and the two IVs differ
    - `# Feature: gdpr-secure-student-registration, Property 8: IV is 16 bytes and unique`
    - _Requirements: 5.1, 5.3_

  - [x] 18.6 Write property test for Property 11: Encryption key is always 32 bytes
    - `test_encryption_key_32_bytes` (no `@given` needed — call `get_encryption_key()` and assert `len(key) == 32`)
    - `# Feature: gdpr-secure-student-registration, Property 11: Encryption key is always 32 bytes`
    - _Requirements: 8.4_

  - Add `test/property_tests.py` to the imports in `run_test.py` so it is discovered by the test runner

- [x] 19. Final checkpoint — run all tests and verify security
  - Run `python run_test.py` and confirm every test passes, including the new property-based tests
  - Run `python run_hacker.py` and confirm no readable plaintext passwords, tokens, or personal data appear in the output
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints (tasks 13 and 19) ensure incremental validation before moving on
- Property tests validate universal correctness properties across many random inputs
- Unit tests validate specific examples, edge cases, and error conditions
- `email` and `displayName` are never encrypted — they are used as lookup keys and display values
