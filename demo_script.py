<<<<<<< HEAD
"""



"""
import urllib.request
import urllib.error
import json
import asyncio
import time
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient

from api.conf import MONGODB_HOST, MONGODB_DBNAME
from api.crypto import encrypt_field

BASE     = "http://localhost:4000/students/api"
DIVIDER  = "=" * 65
DIVIDER2 = "-" * 65


def pause(msg=""):
    input(msg)


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get_with_token(path, token):
    req = urllib.request.Request(BASE + path, headers={"X-Token": token})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def post_with_token(path, data, token):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json", "X-Token": token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ── SLIDE 3 DEMO ──────────────────────────────────────────────────────────────

def demo_slide3():
    print()
    print(DIVIDER)
    print(" DEMO  -- Encryption at Rest: Protecting Personal Data")
    print(DIVIDER)
    print()
    print("  What I will show:")
    print("  1. I will register a student with personal data via the API")
    print("  2. I will show what the API returns (clean plaintext)")
    print("  3. I will show what is ACTUALLY stored in MongoDB (ciphertext)")
    print("  4. I will show encrypt_field() working live -- same input, different output")
    print()
    pause()

    # Step 1 -- Register
    print()
    print("  STEP 1: Register a student with personal data")
    print(DIVIDER2)
    personal_data = {
        "email":        "chioma.okoye@test.com",
        "password":     "SecurePass123",
        "displayName":  "Demo Student",
        "fullName":     "chioma okoye",
        "address":      "42 GDPR Street, Dublin",
        "dateOfBirth":  "1998-05-15",
        "phoneNumber":  "085-1234567",
        "disabilities": "Dyslexia"
    }
    print("  Sending POST /registration with:")
    for k, v in personal_data.items():
        if k != "password":
            print(f"    {k}: {v}")
    print()
    pause()

    status, resp = post("/registration", personal_data)
    print(f"\n  HTTP {status} response:")
    print(f"  {json.dumps(resp, indent=4)}")
    print()
    print("  [OK] API returns only email and displayName")
    print("  [OK] Personal data is never exposed in the API response")
    pause()

    # Step 2 -- Show raw DB
    print()
    print("  STEP 2: What is stored in MongoDB? (the hacker's view)")
    print(DIVIDER2)
    pause()

    async def fetch_doc():
        db = AsyncIOMotorClient(**MONGODB_HOST)[MONGODB_DBNAME]
        return await db.users.find_one({"email": "chioma.okoye@test.com"})

    doc = asyncio.run(fetch_doc())

    if doc:
        print()
        print("  Raw MongoDB document (what an attacker would see if DB was breached):")
        print()
        fields_order = [
            "email", "displayName", "password",
            "fullName", "fullName_iv",
            "address", "address_iv",
            "dateOfBirth", "dateOfBirth_iv",
            "phoneNumber", "phoneNumber_iv",
            "disabilities", "disabilities_iv"
        ]
        for field in fields_order:
            if field in doc:
                val = str(doc[field])
                display = val[:70] + "..." if len(val) > 70 else val
                if "_iv" in field:
                    print(f"    {field:<20} {display}   <-- IV (random bytes)")
                elif field in ("fullName", "address", "dateOfBirth",
                               "phoneNumber", "disabilities"):
                    print(f"    {field:<20} {display}   <-- CIPHERTEXT")
                elif field == "password":
                    print(f"    {field:<20} {display}   <-- bcrypt hash")
                else:
                    print(f"    {field:<20} {display}")
        print()
        print("  [OK] Personal data is unreadable ciphertext -- GDPR Article 32 satisfied")
        print("  [OK] Each field has its own unique IV stored alongside it")
        print("  [OK] Without the AES key (in OS keyring), ciphertext is useless")
    else:
        print("  ERROR: Could not find document -- is the server running?")
    pause()

    # Step 3 -- Live encrypt_field
    print()
    print("  STEP 3: Live demonstration of encrypt_field()")
    print(DIVIDER2)
    print("  Encrypting the string 'Dyslexia' twice with the same key...")
    print()
    pause()

    ct1, iv1 = encrypt_field("Dyslexia")
    time.sleep(0.3)
    ct2, iv2 = encrypt_field("Dyslexia")

    print(f"  Call 1 --> ciphertext : {ct1}")
    print(f"             IV         : {iv1}")
    print()
    print(f"  Call 2 --> ciphertext : {ct2}")
    print(f"             IV         : {iv2}")
    print()
    print(f"  Same ciphertext? {ct1 == ct2}  (should be False)")
    print(f"  Same IV?         {iv1 == iv2}  (should be False)")
    print()
    print("  [OK] Same input produces different ciphertext every time (unique random IV)")
    print("  [OK] Attacker cannot detect two users have the same disability")
    pause()














# ── SLIDE 4 DEMO ──────────────────────────────────────────────────────────────

def demo_slide4():
    print()
    print(DIVIDER)
    print("  DEMO -- Password Hashing & Token Security")
    print(DIVIDER)
    print()
    print("  What I will show:")
    print("  1. I will log in and capture the plaintext token returned to the client")
    print("  2. I will show the SHA-256 hash stored in MongoDB (not the real token)")
    print("  3. I will show the bcrypt hash stored for the password")
    print("  4. I will use the token to retrieve the decrypted profile")
    print()
    pause()

    # Step 1 -- Login
    print()
    print("  STEP 1: Login and capture the token")
    print(DIVIDER2)
    pause()

    status, resp = post("/login", {
        "email":    "chioma.okoye@test.com",
        "password": "SecurePass123"
    })

    if status != 200:
        print(f"  Login failed ({status}): {resp}")
        print("  Make sure you ran the Slide 3 demo first to register the user.")
        return

    token = resp["token"]
    print(f"\n  HTTP {status} -- Token returned to client:")
    print(f"  {token}")
    print()
    print("  [OK] Client receives the real UUID token to use in X-Token header")
    pause()

    # Step 2 -- Show stored hash
    print()
    print("  STEP 2: What token is stored in MongoDB?")
    print(DIVIDER2)
    pause()

    async def fetch_token_doc():
        db = AsyncIOMotorClient(**MONGODB_HOST)[MONGODB_DBNAME]
        return await db.users.find_one(
            {"email": "chioma.okoye@test.com"},
            {"token": 1, "password": 1}
        )

    doc = asyncio.run(fetch_token_doc())
    stored_token = doc.get("token", "")
    stored_pass  = doc.get("password", "")

    print(f"\n  Token returned to client : {token}")
    print(f"  Token stored in MongoDB  : {stored_token}")
    print()

    expected = hashlib.sha256(token.encode()).hexdigest()
    match = stored_token == expected
    print(f"  SHA-256(client token) == stored token: {match}  (should be True)")
    print()
    print("  [OK] Attacker stealing the DB token cannot use it -- it is a hash, not the real token")
    pause()

    # Step 3 -- bcrypt
    print()
    print("  STEP 3: Password stored as bcrypt hash")
    print(DIVIDER2)
    print(f"  Plaintext password : SecurePass123")
    print(f"  Stored in MongoDB  : {stored_pass}")
    print()
    print("  [OK] Starts with $2b$12$ -- bcrypt, work factor 12 (slow by design)")
    print("  [OK] Embedded salt means same password hashes differently every time")
    pause()

    # Step 4 -- Profile decryption
    print()
    print("  STEP 4: Token works -- decryption is transparent to the user")
    print(DIVIDER2)
    pause()

    status, profile = get_with_token("/user", token)
    print(f"\n  HTTP {status} -- Profile returned to client:")
    print(json.dumps(profile, indent=4))
    print()
    print("  [OK] Personal data decrypted transparently -- user sees plaintext")
    print("  [OK] Encryption and decryption are invisible to the API consumer")
    pause()

    # Cleanup
    post_with_token("/logout", {}, token)
    print("  User logged out. Demo complete.")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  GDPR Live Demo -- Slides 3 & 4")
    
    ()
    pause("  >> Slide 3 demo (Encryption at Rest)...")

    demo_slide3()

    print()
    pause("  >>  Slide 4 demo (Password Hashing & Token Security)...")

    demo_slide4()

    print()
    print("  All demos complete!")
    print()
=======
"""
Live demo for Slide 3 & Slide 4 of the GDPR screencast.


Usage:
    python demo_slide3_slide4.py
"""
import urllib.request
import urllib.error
import json
import asyncio
import time
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient

from api.conf import MONGODB_HOST, MONGODB_DBNAME
from api.crypto import encrypt_field

BASE     = "http://localhost:4000/students/api"
DIVIDER  = "=" * 65
DIVIDER2 = "-" * 65


def pause(msg=""):
    input(msg)


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get_with_token(path, token):
    req = urllib.request.Request(BASE + path, headers={"X-Token": token})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def post_with_token(path, data, token):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json", "X-Token": token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ── SLIDE 3 DEMO ──────────────────────────────────────────────────────────────

def demo_slide3():
    print()
    print(DIVIDER)
    print(" DEMO  -- Encryption at Rest: Protecting Personal Data")
    print(DIVIDER)
    print()
    print("  What I will show:")
    print("  1. I will register a student with personal data via the API")
    print("  2. I will show what the API returns (clean plaintext)")
    print("  3. I will show what is ACTUALLY stored in MongoDB (ciphertext)")
    print("  4. I will show encrypt_field() working live -- same input, different output")
    print()
    pause()

    # Step 1 -- Register
    print()
    print("  STEP 1: Register a student with personal data")
    print(DIVIDER2)
    personal_data = {
        "email":        "chioma.okoye@test.com",
        "password":     "SecurePass123",
        "displayName":  "Demo Student",
        "fullName":     "chioma okoye",
        "address":      "42 GDPR Street, Dublin",
        "dateOfBirth":  "1998-05-15",
        "phoneNumber":  "085-1234567",
        "disabilities": "Dyslexia"
    }
    print("  Sending POST /registration with:")
    for k, v in personal_data.items():
        if k != "password":
            print(f"    {k}: {v}")
    print()
    pause()

    status, resp = post("/registration", personal_data)
    print(f"\n  HTTP {status} response:")
    print(f"  {json.dumps(resp, indent=4)}")
    print()
    print("  [OK] API returns only email and displayName")
    print("  [OK] Personal data is never exposed in the API response")
    pause()

    # Step 2 -- Show raw DB
    print()
    print("  STEP 2: What is stored in MongoDB? (the hacker's view)")
    print(DIVIDER2)
    pause()

    async def fetch_doc():
        db = AsyncIOMotorClient(**MONGODB_HOST)[MONGODB_DBNAME]
        return await db.users.find_one({"email": "chioma.okoye@test.com"})

    doc = asyncio.run(fetch_doc())

    if doc:
        print()
        print("  Raw MongoDB document (what an attacker would see if DB was breached):")
        print()
        fields_order = [
            "email", "displayName", "password",
            "fullName", "fullName_iv",
            "address", "address_iv",
            "dateOfBirth", "dateOfBirth_iv",
            "phoneNumber", "phoneNumber_iv",
            "disabilities", "disabilities_iv"
        ]
        for field in fields_order:
            if field in doc:
                val = str(doc[field])
                display = val[:70] + "..." if len(val) > 70 else val
                if "_iv" in field:
                    print(f"    {field:<20} {display}   <-- IV (random bytes)")
                elif field in ("fullName", "address", "dateOfBirth",
                               "phoneNumber", "disabilities"):
                    print(f"    {field:<20} {display}   <-- CIPHERTEXT")
                elif field == "password":
                    print(f"    {field:<20} {display}   <-- bcrypt hash")
                else:
                    print(f"    {field:<20} {display}")
        print()
        print("  [OK] Personal data is unreadable ciphertext -- GDPR Article 32 satisfied")
        print("  [OK] Each field has its own unique IV stored alongside it")
        print("  [OK] Without the AES key (in OS keyring), ciphertext is useless")
    else:
        print("  ERROR: Could not find document -- is the server running?")
    pause()

    # Step 3 -- Live encrypt_field
    print()
    print("  STEP 3: Live demonstration of encrypt_field()")
    print(DIVIDER2)
    print("  Encrypting the string 'Dyslexia' twice with the same key...")
    print()
    pause()

    ct1, iv1 = encrypt_field("Dyslexia")
    time.sleep(0.3)
    ct2, iv2 = encrypt_field("Dyslexia")

    print(f"  Call 1 --> ciphertext : {ct1}")
    print(f"             IV         : {iv1}")
    print()
    print(f"  Call 2 --> ciphertext : {ct2}")
    print(f"             IV         : {iv2}")
    print()
    print(f"  Same ciphertext? {ct1 == ct2}  (should be False)")
    print(f"  Same IV?         {iv1 == iv2}  (should be False)")
    print()
    print("  [OK] Same input produces different ciphertext every time (unique random IV)")
    print("  [OK] Attacker cannot detect two users have the same disability")
    pause()














# ── SLIDE 4 DEMO ──────────────────────────────────────────────────────────────

def demo_slide4():
    print()
    print(DIVIDER)
    print("  DEMO -- Password Hashing & Token Security")
    print(DIVIDER)
    print()
    print("  What I will show:")
    print("  1. I will log in and capture the plaintext token returned to the client")
    print("  2. I will show the SHA-256 hash stored in MongoDB (not the real token)")
    print("  3. I will show the bcrypt hash stored for the password")
    print("  4. I will use the token to retrieve the decrypted profile")
    print()
    pause()

    # Step 1 -- Login
    print()
    print("  STEP 1: Login and capture the token")
    print(DIVIDER2)
    pause()

    status, resp = post("/login", {
        "email":    "chioma.okoye@test.com",
        "password": "SecurePass123"
    })

    if status != 200:
        print(f"  Login failed ({status}): {resp}")
        print("  Make sure you ran the Slide 3 demo first to register the user.")
        return

    token = resp["token"]
    print(f"\n  HTTP {status} -- Token returned to client:")
    print(f"  {token}")
    print()
    print("  [OK] Client receives the real UUID token to use in X-Token header")
    pause()

    # Step 2 -- Show stored hash
    print()
    print("  STEP 2: What token is stored in MongoDB?")
    print(DIVIDER2)
    pause()

    async def fetch_token_doc():
        db = AsyncIOMotorClient(**MONGODB_HOST)[MONGODB_DBNAME]
        return await db.users.find_one(
            {"email": "chioma.okoye@test.com"},
            {"token": 1, "password": 1}
        )

    doc = asyncio.run(fetch_token_doc())
    stored_token = doc.get("token", "")
    stored_pass  = doc.get("password", "")

    print(f"\n  Token returned to client : {token}")
    print(f"  Token stored in MongoDB  : {stored_token}")
    print()

    expected = hashlib.sha256(token.encode()).hexdigest()
    match = stored_token == expected
    print(f"  SHA-256(client token) == stored token: {match}  (should be True)")
    print()
    print("  [OK] Attacker stealing the DB token cannot use it -- it is a hash, not the real token")
    pause()

    # Step 3 -- bcrypt
    print()
    print("  STEP 3: Password stored as bcrypt hash")
    print(DIVIDER2)
    print(f"  Plaintext password : SecurePass123")
    print(f"  Stored in MongoDB  : {stored_pass}")
    print()
    print("  [OK] Starts with $2b$12$ -- bcrypt, work factor 12 (slow by design)")
    print("  [OK] Embedded salt means same password hashes differently every time")
    pause()

    # Step 4 -- Profile decryption
    print()
    print("  STEP 4: Token works -- decryption is transparent to the user")
    print(DIVIDER2)
    pause()

    status, profile = get_with_token("/user", token)
    print(f"\n  HTTP {status} -- Profile returned to client:")
    print(json.dumps(profile, indent=4))
    print()
    print("  [OK] Personal data decrypted transparently -- user sees plaintext")
    print("  [OK] Encryption and decryption are invisible to the API consumer")
    pause()

    # Cleanup
    post_with_token("/logout", {}, token)
    print("  User logged out. Demo complete.")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  GDPR Live Demo -- Slides 3 & 4")
    
    ()
    pause("  >> Slide 3 demo (Encryption at Rest)...")

    demo_slide3()

    print()
    pause("  >>  Slide 4 demo (Password Hashing & Token Security)...")

    demo_slide4()

    print()
    print("  All demos complete!")
    print()
>>>>>>> a120bb56d4ac687d4688d6bc22078a07e7f9ee40
