from json import dumps
from tornado.escape import json_decode
from tornado.httputil import HTTPHeaders
from tornado.ioloop import IOLoop
from tornado.web import Application

from api.handlers.user import UserHandler
from api.crypto import encrypt_field, hash_passphrase, hash_token

from .base import BaseTest

class UserHandlerTest(BaseTest):

    @classmethod
    def setUpClass(self):
        self.my_app = Application([(r'/user', UserHandler)])
        super().setUpClass()

    async def register(self):
        await self.get_app().db.users.insert_one({
            'email': self.email,
            'password': hash_passphrase(self.password),
            'displayName': self.display_name
        })

    async def login(self):
        await self.get_app().db.users.update_one({
            'email': self.email
        }, {
            '$set': { 'token': hash_token(self.token), 'expiresIn': 2147483647 }
        })

    def setUp(self):
        super().setUp()

        self.email = 'test@test.com'
        self.password = 'testPassword'
        self.display_name = 'testDisplayName'
        self.token = 'testToken'

        IOLoop.current().run_sync(self.register)
        IOLoop.current().run_sync(self.login)

    def test_user(self):
        headers = HTTPHeaders({'X-Token': self.token})

        response = self.fetch('/user', headers=headers)
        self.assertEqual(200, response.code)

        body_2 = json_decode(response.body)
        self.assertEqual(self.email, body_2['email'])
        self.assertEqual(self.display_name, body_2['displayName'])

    def test_user_without_token(self):
        response = self.fetch('/user')
        self.assertEqual(400, response.code)

    def test_user_wrong_token(self):
        headers = HTTPHeaders({'X-Token': 'wrongToken'})

        response = self.fetch('/user')
        self.assertEqual(400, response.code)

    def test_user_personal_data_decrypted(self):
        personal_email = 'personal@test.com'
        personal_token = 'personalToken'

        personal_data = {
            'fullName': 'Jane Smith',
            'address': '456 Oak Ave',
            'dateOfBirth': '1995-06-15',
            'phoneNumber': '555-9876',
            'disabilities': 'none',
        }

        async def setup_personal_user():
            doc = {
                'email': personal_email,
                'password': hash_passphrase('personalPassword'),
                'displayName': 'Jane Smith',
            }
            for field, value in personal_data.items():
                ciphertext_b64, iv_b64 = encrypt_field(value)
                doc[field] = ciphertext_b64
                doc[f'{field}_iv'] = iv_b64
            await self.get_app().db.users.insert_one(doc)
            await self.get_app().db.users.update_one(
                {'email': personal_email},
                {'$set': {'token': hash_token(personal_token), 'expiresIn': 2147483647}}
            )

        IOLoop.current().run_sync(setup_personal_user)

        headers = HTTPHeaders({'X-Token': personal_token})
        response = self.fetch('/user', headers=headers)
        self.assertEqual(200, response.code)

        body = json_decode(response.body)
        self.assertEqual('Jane Smith', body['fullName'])
        self.assertEqual('456 Oak Ave', body['address'])
        self.assertEqual('1995-06-15', body['dateOfBirth'])
        self.assertEqual('555-9876', body['phoneNumber'])
        self.assertEqual('none', body['disabilities'])

    def test_user_missing_field_omitted(self):
        headers = HTTPHeaders({'X-Token': self.token})
        response = self.fetch('/user', headers=headers)
        self.assertEqual(200, response.code)

        body = json_decode(response.body)
        for field in ['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']:
            self.assertNotIn(field, body)
