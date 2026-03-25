import hashlib
from json import dumps
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.web import Application

from .base import BaseTest

from api.handlers.login import LoginHandler
from api.crypto import hash_passphrase

class LoginHandlerTest(BaseTest):

    @classmethod
    def setUpClass(self):
        self.my_app = Application([(r'/login', LoginHandler)])
        super().setUpClass()

    async def register(self):
        await self.get_app().db.users.insert_one({
            'email': self.email,
            'password': hash_passphrase(self.password),
            'displayName': 'testDisplayName'
        })

    def setUp(self):
        super().setUp()

        self.email = 'test@test.com'
        self.password = 'testPassword'

        IOLoop.current().run_sync(self.register)

    def test_login(self):
        body = {
          'email': self.email,
          'password': self.password
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        body_2 = json_decode(response.body)
        self.assertIsNotNone(body_2['token'])
        self.assertIsNotNone(body_2['expiresIn'])

    def test_login_case_insensitive(self):
        body = {
          'email': self.email.swapcase(),
          'password': self.password
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        body_2 = json_decode(response.body)
        self.assertIsNotNone(body_2['token'])
        self.assertIsNotNone(body_2['expiresIn'])

    def test_login_wrong_email(self):
        body = {
          'email': 'wrongUsername',
          'password': self.password
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(403, response.code)

    def test_login_wrong_password(self):
        body = {
          'email': self.email,
          'password': 'wrongPassword'
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(403, response.code)

    def test_token_not_stored_as_plaintext(self):
        body = {
          'email': self.email,
          'password': self.password
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        response_token = json_decode(response.body)['token']
        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': self.email}))
        self.assertNotEqual(doc['token'], response_token)

    def test_token_stored_as_sha256(self):
        body = {
          'email': self.email,
          'password': self.password
        }

        response = self.fetch('/login', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        response_token = json_decode(response.body)['token']
        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': self.email}))
        self.assertEqual(doc['token'], hashlib.sha256(response_token.encode()).hexdigest())
