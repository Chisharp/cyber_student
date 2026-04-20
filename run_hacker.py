"""
run_hacker.py — simulates a database breach.

Dumps everything stored in MongoDB exactly as it is stored.
After the GDPR-compliant changes:
  - passwords are bcrypt hashes (not plaintext)
  - tokens are SHA-256 hashes (not plaintext)
  - personal data fields are AES-256-CBC ciphertext (not plaintext)

Usage:
    python run_hacker.py list
"""

import asyncio
import click
from motor.motor_tornado import MotorClient

from api.conf import MONGODB_HOST, MONGODB_DBNAME

PERSONAL_FIELDS = [
    'fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities'
]


async def get_users(db):
    # Fetch every field stored in the collection
    projection = {
        'email': 1,
        'password': 1,
        'displayName': 1,
        'token': 1,
        'expiresIn': 1,
    }
    for field in PERSONAL_FIELDS:
        projection[field] = 1
        projection[f'{field}_iv'] = 1

    cur = db.users.find({}, projection)
    docs = await cur.to_list(length=None)

    click.echo(f'There are {len(docs)} registered users:')
    for doc in docs:
        click.echo('\n--- User record (raw from DB) ---')
        for key, value in doc.items():
            if key == '_id':
                continue
            click.echo(f'  {key}: {value}')


@click.group()
def cli():
    pass


@cli.command()
def list():
    db = MotorClient(**MONGODB_HOST)[MONGODB_DBNAME]
    asyncio.run(get_users(db))


if __name__ == '__main__':
    cli()
