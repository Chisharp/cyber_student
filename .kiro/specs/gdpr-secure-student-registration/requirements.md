# Requirements Document

## Introduction

This feature hardens the existing Python/Tornado student registration REST API to meet GDPR security
standards. Currently all credentials, tokens, and personal data are stored in plaintext in MongoDB.
The changes introduce bcrypt passphrase hashing, SHA-256 token hashing, and AES-256-CBC encryption
of personal data fields, with IVs/salts persisted in MongoDB and encryption keys managed through the
`keyring` package. All existing API behaviour and test contracts are preserved.

## Glossary

- **System**: The Tornado-based student registration REST API.
- **Registration_Handler**: The Tornado request handler at `POST /students/api/registration`.
- **Login_Handler**: The Tornado request handler at `POST /students/api/login`.
- **Auth_Handler**: The base Tornado request handler that validates the `X-Token` header for protected routes.
- **Logout_Handler**: The Tornado request handler at `POST /students/api/logout`.
- **User_Handler**: The Tornado request handler at `GET /students/api/user`.
- **Crypto_Service**: The module (`api/crypto.py`) that encapsulates all hashing and encryption logic.
- **Passphrase**: The user-supplied password string submitted during registration or login.
- **Passphrase_Hash**: The bcrypt hash of a Passphrase, stored in MongoDB in place of the plaintext Passphrase.
- **Token**: The UUID hex string generated at login and returned to the client in the response body.
- **Token_Hash**: The SHA-256 hex digest of a Token, stored in MongoDB in place of the plaintext Token.
- **Personal_Data_Field**: Any of the following user profile fields: `fullName`, `address`, `dateOfBirth`, `phoneNumber`, `disabilities`.
- **Ciphertext**: The AES-256-CBC encrypted bytes of a Personal_Data_Field, stored base64-encoded in MongoDB.
- **IV**: A 16-byte random initialisation vector generated per Personal_Data_Field per user, stored base64-encoded in MongoDB alongside the corresponding Ciphertext.
- **Encryption_Key**: A 32-byte AES key retrieved from the host keyring via the `keyring` package; never stored in MongoDB.
- **Key_Service**: The component responsible for retrieving and, on first use, generating the Encryption_Key via `keyring`.

---

## Requirements

### Requirement 1: Passphrase Hashing at Registration

**User Story:** As a security engineer, I want passphrases to be hashed with bcrypt before storage, so that plaintext passwords are never persisted in the database.

#### Acceptance Criteria

1. WHEN a registration request is received with a valid Passphrase, THE Crypto_Service SHALL produce a Passphrase_Hash using bcrypt with a work factor of at least 12.
2. WHEN a registration request is received with a valid Passphrase, THE Registration_Handler SHALL store the Passphrase_Hash in MongoDB and SHALL NOT store the plaintext Passphrase.
3. THE Crypto_Service SHALL produce a different Passphrase_Hash on each invocation for the same Passphrase input (due to random salt generation).
4. FOR ALL valid Passphrases, hashing then verifying the Passphrase against the resulting Passphrase_Hash SHALL return `True` (round-trip property).

---

### Requirement 2: Passphrase Verification at Login

**User Story:** As a registered student, I want to log in with my original passphrase, so that I can authenticate even though only a hash is stored.

#### Acceptance Criteria

1. WHEN a login request is received, THE Login_Handler SHALL retrieve the stored Passphrase_Hash for the given email address.
2. WHEN a login request is received with a Passphrase that matches the stored Passphrase_Hash, THE Login_Handler SHALL respond with HTTP 200 and a valid Token.
3. WHEN a login request is received with a Passphrase that does not match the stored Passphrase_Hash, THE Login_Handler SHALL respond with HTTP 403.
4. WHEN a login request is received for an email address that does not exist in the database, THE Login_Handler SHALL respond with HTTP 403.

---

### Requirement 3: Token Hashing After Generation

**User Story:** As a security engineer, I want session tokens to be hashed before storage, so that a database breach does not expose valid session tokens.

#### Acceptance Criteria

1. WHEN a login request succeeds, THE Login_Handler SHALL generate a UUID hex Token and return it to the client in the response body.
2. WHEN a login request succeeds, THE Crypto_Service SHALL compute a Token_Hash as the SHA-256 hex digest of the Token.
3. WHEN a login request succeeds, THE Login_Handler SHALL store the Token_Hash in MongoDB and SHALL NOT store the plaintext Token.
4. FOR ALL generated Tokens, computing the SHA-256 hex digest of the Token SHALL produce the same Token_Hash that was stored (deterministic round-trip property).

---

### Requirement 4: Token Verification for Authenticated Requests

**User Story:** As a registered student, I want my session token to be accepted for authenticated API calls, so that I can access protected resources after login.

#### Acceptance Criteria

1. WHEN an authenticated request is received with an `X-Token` header, THE Auth_Handler SHALL compute the SHA-256 hex digest of the supplied Token value.
2. WHEN an authenticated request is received, THE Auth_Handler SHALL query MongoDB for a user document whose stored `token` field equals the computed Token_Hash.
3. WHEN the Token_Hash matches a non-expired user document, THE Auth_Handler SHALL set `current_user` and allow the request to proceed.
4. WHEN the Token_Hash does not match any user document, THE Auth_Handler SHALL respond with HTTP 403.
5. WHEN the `X-Token` header is absent, THE Auth_Handler SHALL respond with HTTP 400.

---

### Requirement 5: Personal Data Encryption at Rest

**User Story:** As a GDPR compliance officer, I want personal data fields to be encrypted before storage, so that sensitive student information is protected in the database.

#### Acceptance Criteria

1. WHEN a registration or profile-update request includes one or more Personal_Data_Fields, THE Crypto_Service SHALL encrypt each Personal_Data_Field independently using AES-256-CBC with a unique IV.
2. WHEN encrypting a Personal_Data_Field, THE Crypto_Service SHALL retrieve the Encryption_Key from the Key_Service using the `keyring` package.
3. WHEN encrypting a Personal_Data_Field, THE Crypto_Service SHALL generate a cryptographically random 16-byte IV for each field.
4. THE Registration_Handler SHALL store the Ciphertext (base64-encoded) and the corresponding IV (base64-encoded) in the user's MongoDB document for each Personal_Data_Field.
5. THE Registration_Handler SHALL NOT store the plaintext value of any Personal_Data_Field in MongoDB.
6. FOR ALL valid Personal_Data_Field values, encrypting then decrypting with the same Encryption_Key and IV SHALL return the original plaintext value (round-trip property).

---

### Requirement 6: Personal Data Decryption on Retrieval

**User Story:** As a registered student, I want my personal details returned in plaintext when I request my profile, so that the encryption is transparent to me.

#### Acceptance Criteria

1. WHEN an authenticated `GET /students/api/user` request is received, THE User_Handler SHALL retrieve the encrypted Personal_Data_Fields and their IVs from MongoDB.
2. WHEN returning Personal_Data_Fields to the client, THE Crypto_Service SHALL decrypt each Ciphertext using the corresponding IV and the Encryption_Key retrieved from the Key_Service.
3. WHEN a Personal_Data_Field is absent from the user document, THE User_Handler SHALL omit that field from the response without error.
4. WHEN decryption of a Personal_Data_Field fails, THE User_Handler SHALL respond with HTTP 500 and SHALL NOT return partial plaintext data.

---

### Requirement 7: IV and Salt Storage

**User Story:** As a security engineer, I want IVs and bcrypt salts to be stored in MongoDB alongside the encrypted data, so that decryption and verification remain possible without hardcoding values.

#### Acceptance Criteria

1. WHEN a Personal_Data_Field is encrypted, THE Registration_Handler SHALL store the IV for that field in the user's MongoDB document under a key named `<fieldName>_iv` (e.g., `fullName_iv`).
2. WHEN a Passphrase is hashed, THE Registration_Handler SHALL store the bcrypt salt embedded within the Passphrase_Hash in MongoDB (bcrypt stores the salt as part of the hash string; no separate field is required).
3. THE System SHALL store one distinct IV per Personal_Data_Field per user document.
4. WHEN a user document is retrieved from MongoDB, THE System SHALL be able to decrypt all present Personal_Data_Fields using only the stored IVs and the Encryption_Key from the Key_Service.

---

### Requirement 8: Encryption Key Management via Keyring

**User Story:** As a security engineer, I want encryption keys to be managed by the OS keyring, so that keys are never stored in the database or source code.

#### Acceptance Criteria

1. THE Key_Service SHALL retrieve the Encryption_Key by calling `keyring.get_password` with a fixed service name and username.
2. WHEN `keyring.get_password` returns `None`, THE Key_Service SHALL generate a new cryptographically random 32-byte Encryption_Key, store it via `keyring.set_password`, and return it.
3. THE Key_Service SHALL NOT store the Encryption_Key in MongoDB, in environment variables, or in source code.
4. WHEN the Encryption_Key is retrieved from the keyring, THE Key_Service SHALL return it as a 32-byte value suitable for AES-256 operations.

---

### Requirement 9: Backward Compatibility and Regression

**User Story:** As a developer, I want all existing API contracts and test cases to continue passing, so that the security changes do not break current functionality.

#### Acceptance Criteria

1. THE System SHALL preserve all existing HTTP status codes and response body schemas for the registration, login, logout, and user endpoints.
2. WHEN the test suite in `run_test.py` is executed after the changes, THE System SHALL pass all pre-existing test cases without modification to those test cases.
3. WHEN a registration request succeeds, THE Registration_Handler SHALL return the `email` and `displayName` fields in the response body, identical to the current behaviour.
4. WHEN a login request succeeds, THE Login_Handler SHALL return the `token` (plaintext UUID) and `expiresIn` fields in the response body, identical to the current behaviour.

---

### Requirement 10: Security Test Coverage

**User Story:** As a developer, I want new tests covering hashing, verification, and encryption, so that the security properties of the system are continuously validated.

#### Acceptance Criteria

1. THE Test_Suite SHALL include a test that verifies a stored password field is not equal to the plaintext Passphrase after registration.
2. THE Test_Suite SHALL include a test that verifies `bcrypt.checkpw(plaintext, stored_hash)` returns `True` for a registered user's Passphrase.
3. THE Test_Suite SHALL include a test that verifies a stored token field is not equal to the plaintext Token after login.
4. THE Test_Suite SHALL include a test that verifies the SHA-256 hex digest of the plaintext Token equals the stored Token_Hash.
5. THE Test_Suite SHALL include a test that verifies each Personal_Data_Field stored in MongoDB is not equal to its plaintext value after registration.
6. THE Test_Suite SHALL include a test that verifies decrypting a stored Ciphertext with its stored IV and the Encryption_Key returns the original plaintext Personal_Data_Field value (round-trip property).
7. FOR ALL valid Passphrases, hashing then verifying SHALL return `True` (property test covering multiple inputs).
8. FOR ALL valid Personal_Data_Field strings, encrypting then decrypting SHALL return the original string (property test covering multiple inputs).
