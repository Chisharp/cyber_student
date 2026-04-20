"""
Quick API test script — run this instead of curl to avoid PowerShell quoting issues.
Usage: python test_api.py
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:4000/students/api"

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"X-Token": token})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# 1. Register
print("=== Register ===")
r = post("/registration", {
    "email": "alice@test.com",
    "password": "secret123",
    "displayName": "Alice",
    "fullName": "Alice Smith",
    "address": "123 Main St",
    "dateOfBirth": "1995-01-01",
    "phoneNumber": "555-1234",
    "disabilities": "none"
})
print(r)

# 2. Login
print("\n=== Login ===")
r = post("/login", {"email": "alice@test.com", "password": "secret123"})
print(r)
token = r.get("token")

if token:
    # 3. Get profile
    print("\n=== Profile ===")
    print(get("/user", token))

    # 4. Logout
    print("\n=== Logout ===")
    body = json.dumps({}).encode()
    req = urllib.request.Request(
        BASE + "/logout", data=body,
        headers={"Content-Type": "application/json", "X-Token": token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(json.loads(resp.read()))
    except urllib.error.HTTPError as e:
        print(json.loads(e.read()))
else:
    print("Login failed — cannot test profile/logout")
