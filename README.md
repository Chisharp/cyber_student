# `cyber-students`

This repository provides some sample code for the Shared Project for
Modern Cryptography and Security Management & Compliance.  The project
requires git, Python 3, and MongoDB.  The following sections briefly
explain how to setup the project on your local machine.

## Get the Sample Code

Create a [GitHub](https://github.com) account.  Downloaded and installed
[git](https://git-scm.com).   used `git` to manage our source
code.

Verify that `git` is installed correctly:

```sh
git --version
```

[Fork this
repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
and clone your forked repository to your local machine:

```sh
git clone https://github.com/YOUR_GITHUB_USERNAME/cyber-students.git
```

## Setup the Project

Create a Python 3 virtual environment:

```sh
python -m venv project-venv

```

Activate the virtual environment:

```bat
:: ... on Windows:
.\project-venv\Scripts\activate
```


```

Install the required packages:

```sh
cd cyber-students
pip install -r requirements.txt
```

Downloaded, installed and start [MongoDB Community
Edition](https://www.mongodb.com/docs/manual/installation).  i will
use MongoDB as our database.

Downloaded and installed [MongoDB
Shell](https://www.mongodb.com/try/download/shell).  Open a MongoDB
shell:

```sh
mongosh
```

Create a database with a collection named `users`:

```
use cyberStudents;
db.createCollection('users');
```

This database will store PII / PHI data.  The tests use an in-memory mock
database, so they do not require a running MongoDB server.


```

## Start the Project

The server contains functionality for:

* registering new users (`api/handlers/registration.py`)
* logging in (`api/handlers/login.py`)
* logging out (`api/handlers/logout.py`)
* displaying profile (`api/handlers/user.py`)

To start the server:

```sh
python run_server.py
```

The server is available on port 4000 at
http://localhost:4000/students/api.  However, it is not possible to
use all of the functionality offered by the server directly using a
browser.  Instead i will use `curl` to interact with the server.

### Registration

To register a new user:

```sh
curl -X POST http://localhost:4000/students/api/registration -d "{\"email\": \"chiom.okoye@test.com\", \"password\": \"pass\", \"displayName\": \"chioma okoye\"}"
```

If the registration is successful, it will confirm the email address
and the display name of the newly registered user:

```
{"email": "chioma.okoye@test.com", "displayName": "chioma okoye"}
```

If the registration is unsuccessful, for example, if you try to
register the same user twice, it will return an error message:

```
{"message": "A user with the given email address already exists!"}
```

### Logging In

To login:

```sh
curl -X POST http://localhost:4000/students/api/login -d "{\"email\": \"chioma.okoye@test.com\", \"password\": \"pass\"}"
```

If the login is successful, it will return a token and expiration
timestamp:

```
{"token": "d4a5d8b20fe143b7b92e4fba92d409be", "expiresIn": 1648559677.0}
```

A token expires and is intended to be short-lived.  A token expires
two hours after login, after a logout, or if there is another login
from the same user, generating a new token.

If the login is unsuccessful, for example, if you provide an incorrect
password, it will return an error message:

```
{"message": "The email address and password are invalid!"}
```

### Displaying a Profile

To display a user's profile you need a token that has not expired.
Then you can use:

```sh
curl -H "X-Token: d4a5d8b20fe143b7b92e4fba92d409be" http://localhost:4000/students/api/user
```

Note that this API call does not require the `-X POST` flag.

If successful, it will return the email address and the display name
for the user:

```
{"email": "chioma.okoye@test.com", "displayName": "chioma okoye"}
```

### Logging Out

To logout, you also need a token that has not expired.  Then you can
use:


```sh
curl -X POST -H "X-Token: d4a5d8b20fe143b7b92e4fba92d409be" http://localhost:4000/students/api/logout
```

## Test the Project

You can run the automated tests using:

```sh
python run_test.py
```

This command runs a number of automated tests in the `test` directory.
The tests use an in-memory mock database and perform tests such as registering new users
(`test/registration.py`), logging in (`test/login.py`), and logging
out (`test/logout.py`).

The project also includes a program called `run_hacker.py`.  You can
run it using:

```sh
python run_hacker.py list
```

It displays all information stored in the MongoDB database.  It
produces output similar to the following:

```
There are 1 registered users:
{'_id': ObjectId('6242d9c34536b3a16b49aa6b'), 'email': 'chioma okoye@test.com', 'password': 'pass', 'displayName': 'chioma okoye'}
```

As you can see, all of the information is stored in the clear; there
is no encryption or password hashing.  If a hacker was to compromise
the database, they could easily run a similar program to retrieve all
of the users personal information and passwords.
